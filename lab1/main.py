import os
import time
import random
import json
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup, Comment
from tqdm import tqdm

BASE_URL = "https://news.drom.ru"
PAGINATION_URL = "https://news.drom.ru/page{}/"
OUTPUT_DIR = Path("drom_corpus")
TARGET_COUNT = 80123 
REQUEST_TIMEOUT = 10
DELAY = (0.5, 1.2)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

def ensure_dirs():
    (OUTPUT_DIR / "raw").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "text").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "meta").mkdir(parents=True, exist_ok=True)

def extract_content(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    
    article_body = soup.find('div', {'class': 'b-article__content'}) or \
                   soup.find('div', {'class': 'b-news-item__content'}) or \
                   soup.find('div', {'id': 'tx'})
    
    if article_body:
        text = article_body.get_text(separator=" ", strip=True)
    else:
        text = soup.get_text(separator=" ", strip=True)

    text = re.sub(r'\s+', ' ', text)
    return text

def get_article_links(page_num, session):
    url = PAGINATION_URL.format(page_num)
    try:
        r = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'news.drom.ru/' in href and href.endswith('.html') and re.search(r'\d+', href):
                if href not in links:
                    links.append(href)
        return list(set(links))
    except Exception as e:
        print(f"Error on page {page_num}: {e}")
        return []

def main():
    ensure_dirs()
    meta_file = OUTPUT_DIR / "meta" / "metadata.jsonl"
    
    collected_count = 0
    seen_urls = set()

    if meta_file.exists():
        with open(meta_file, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                seen_urls.add(data['url'])
                collected_count += 1

    session = requests.Session()
    pbar = tqdm(total=TARGET_COUNT, desc="Collecting Drom News")
    pbar.update(collected_count)

    page = 1
    while collected_count < TARGET_COUNT:
        links = get_article_links(page, session)
        if not links:
            print(f"No more links on page {page}")
            break

        for url in links:
            if url in seen_urls:
                continue
            if collected_count >= TARGET_COUNT:
                break

            try:
                time.sleep(random.uniform(*DELAY))
                res = session.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
                if res.status_code == 200:
                    doc_id = url.split('/')[-1].replace('.html', '')
                    raw_path = OUTPUT_DIR / "raw" / f"{doc_id}.html"
                    text_path = OUTPUT_DIR / "text" / f"{doc_id}.txt"
                    
                    with open(raw_path, "w", encoding="utf-8") as f:
                        f.write(res.text)
                    
                    text = extract_content(res.text)
                    if len(text) < 200: 
                        continue

                    with open(text_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    
                    meta = {
                        "id": doc_id,
                        "url": url,
                        "raw_size": raw_path.stat().st_size,
                        "text_size": text_path.stat().st_size,
                        "word_count": len(text.split())
                    }
                    
                    with open(meta_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(meta, ensure_ascii=False) + "\n")
                    
                    seen_urls.add(url)
                    collected_count += 1
                    pbar.update(1)
            except Exception as e:
                print(f"Failed to download {url}: {e}")

        page += 1

    pbar.close()
    print(f"Сбор завершен! Итого документов: {collected_count}")

if __name__ == "__main__":
    main()

