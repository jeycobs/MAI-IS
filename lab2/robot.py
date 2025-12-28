import argparse
import hashlib
import json
import logging
import random
import re
import signal
import sys
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
import yaml
from bs4 import BeautifulSoup
from pymongo import MongoClient, ASCENDING, DESCENDING

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] ROBOT: %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        self.kill_now = True
        log.warning("Получен сигнал остановки. Завершаем текущую задачу...")

def compute_hash(content: str) -> str:
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def clean_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        scheme = parts.scheme.lower() if parts.scheme else 'http'
        netloc = parts.netloc.lower()
        path = parts.path if parts.path else '/'
        
        while '//' in path:
            path = path.replace('//', '/')
            
        return urlunsplit((scheme, netloc, path, parts.query, ''))
    except Exception:
        return url

def get_links(html: str, parent_url: str):
    soup = BeautifulSoup(html, 'lxml')
    for tag in soup.find_all('a', href=True):
        href = tag['href'].strip()
        if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
            continue
        yield urljoin(parent_url, href)


class MongoCrawler:
    def __init__(self, config_path: str):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.cfg = yaml.safe_load(f)

        db_conf = self.cfg.get('db', {})
        self.client = MongoClient(db_conf.get('uri', 'mongodb://localhost:27017'))
        self.db = self.client[db_conf.get('database', 'search_engine')]
        
        self.col_urls = self.db['urls']
        self.col_docs = self.db['docs']
        
        self._ensure_indexes()
        
        logic = self.cfg.get('logic', {})
        self.http_timeout = logic.get('timeout', 10)
        self.retry_delay = logic.get('retry_delay', 3600)
        self.recrawl_period = logic.get('recrawl_period', 86400)
        self.batch_size = logic.get('batch_size', 20)
        self.user_agent = logic.get('user_agent', 'Bot/2.0')
        
        d_range = logic.get('delay', [1.0, 2.0])
        self.delay_range = (d_range[0], d_range[1]) if isinstance(d_range, list) else (d_range, d_range)
        
        self.rules = []
        self.global_ignore = [re.compile(p) for p in self.cfg.get('crawl', {}).get('ignore_patterns', [])]
        
        for rule in self.cfg.get('crawl', {}).get('sources', []):
            self.rules.append({
                'name': rule['name'],
                'domains': set(rule['domains']),
                'regex': [re.compile(r) for r in rule.get('patterns', [])]
            })

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})

    def _ensure_indexes(self):
        self.col_urls.create_index('url', unique=True)
        self.col_urls.create_index('next_check')
        self.col_docs.create_index('url')

    def _match_rule(self, url: str):
        for pat in self.global_ignore:
            if pat.search(url):
                return None
        
        u_parsed = urlsplit(url)
        domain = u_parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]

        for r in self.rules:
            if domain in r['domains']:
                if not r['regex']:
                    return r['name']
                for pat in r['regex']:
                    if pat.search(url):
                        return r['name']
        return None

    def schedule_url(self, url: str, source: str, priority_ts: int = 0):
        try:
            self.col_urls.update_one(
                {'url': url},
                {
                    '$setOnInsert': {
                        'url': url,
                        'source': source,
                        'added_at': int(time.time()),
                        'status': 'new',
                        'content_hash': None,
                        'etag': None,
                        'last_mod': None
                    },
                    '$min': {'next_check': priority_ts}
                },
                upsert=True
            )
        except Exception as e:
            log.error(f"Ошибка Mongo при вставке {url}: {e}")

    def load_seeds(self):
        seeds = self.cfg.get('seeds', {})
        now = int(time.time())
        
        for s in seeds.get('manual_urls', []):
            u = clean_url(s['url'])
            src = self._match_rule(u)
            if src:
                self.schedule_url(u, src, now)
        
        for path in seeds.get('files', []):
            count = 0
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            rec = json.loads(line)
                            u = clean_url(rec['url'])
                            src = self._match_rule(u)
                            if src:
                                self.schedule_url(u, src, now)
                                count += 1
                        except: pass
                log.info(f"Загружено {count} URL из файла {path}")
            except FileNotFoundError:
                log.warning(f"Файл сидов не найден: {path}")

    def fetch_page(self, task):
        url = task['url']
        headers = {}
        
        if task.get('etag'):
            headers['If-None-Match'] = task['etag']
        if task.get('last_mod'):
            headers['If-Modified-Since'] = task['last_mod']

        try:
            resp = self.session.get(url, headers=headers, timeout=self.http_timeout)
            return resp
        except requests.RequestException as e:
            log.warning(f"Сбой сети для {url}: {e}")
            return None

    def worker_step(self, task):
        url = task['url']
        source = task['source']
        old_hash = task.get('content_hash')
        
        resp = self.fetch_page(task)
        now = int(time.time())

        if resp is None:
            self.col_urls.update_one(
                {'_id': task['_id']},
                {'$set': {'next_check': now + self.retry_delay}}
            )
            return

        if resp.status_code == 304:
            log.info(f"Не изменился (304): {url}")
            self.col_urls.update_one(
                {'_id': task['_id']},
                {'$set': {
                    'next_check': now + self.recrawl_period,
                    'last_check': now,
                    'status': '304'
                }}
            )
            return

        if resp.status_code == 200:
            content = resp.text
            new_hash = compute_hash(content)
            
            is_changed = (new_hash != old_hash)
            
            if is_changed:
                doc_record = {
                    'url': url,
                    'source': source,
                    'raw_html': content,
                    'crawl_ts': now,
                    'title': ''
                }
                try:
                    soup = BeautifulSoup(content, 'lxml')
                    if soup.title:
                        doc_record['title'] = soup.title.string.strip()
                except: pass

                self.col_docs.insert_one(doc_record)
                log.info(f"Сохранен документ ({len(content)} байт): {url}")
            else:
                log.info(f"Хеш совпал, пропускаем сохранение: {url}")

            if self.cfg.get('crawl', {}).get('collect_links', True):
                count = 0
                for link in get_links(content, url):
                    normalized = clean_url(link)
                    rule_name = self._match_rule(normalized)
                    if rule_name:
                        self.schedule_url(normalized, rule_name, now)
                        count += 1
                if count: log.info(f"Найдено {count} ссылок")

            self.col_urls.update_one(
                {'_id': task['_id']},
                {'$set': {
                    'next_check': now + self.recrawl_period,
                    'last_check': now,
                    'status': '200',
                    'content_hash': new_hash,
                    'etag': resp.headers.get('ETag'),
                    'last_mod': resp.headers.get('Last-Modified')
                }}
            )
            return

        log.warning(f"Код ответа {resp.status_code}: {url}")
        self.col_urls.update_one(
            {'_id': task['_id']},
            {'$set': {
                'next_check': now + self.recrawl_period, 
                'last_check': now,
                'status': str(resp.status_code)
            }}
        )

    def start(self):
        log.info("Запуск Crawler...")
        killer = GracefulKiller()
        
        self.load_seeds()
        
        while not killer.kill_now:
            now = int(time.time())
            cursor = self.col_urls.find(
                {'next_check': {'$lte': now}}
            ).sort('next_check', ASCENDING).limit(self.batch_size)
            
            tasks = list(cursor)
            
            if not tasks:
                log.info("Очередь пуста или задачи отложены. Сплю...")
                time.sleep(5)
                continue
            
            for task in tasks:
                if killer.kill_now: break
                self.worker_step(task)
                
                sleep_time = random.uniform(*self.delay_range)
                time.sleep(sleep_time)
        
        log.info("Работа завершена.")

def main():
    parser = argparse.ArgumentParser(description="Lab 2 Crawler")
    parser.add_argument('config', help='Путь к YAML конфигу')
    args = parser.parse_args()
    
    bot = MongoCrawler(args.config)
    bot.start()

if __name__ == '__main__':
    main()
