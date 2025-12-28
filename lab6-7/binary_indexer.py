import os
import json
import struct
import re
from pathlib import Path

TERM_SIZE = 32      
DOC_REC_SIZE = 512  

class BinaryIndexer:
    def __init__(self, corpus_path):
        self.corpus_path = Path(corpus_path)
        self.text_dir = self.corpus_path / "text"
        self.metadata_path = self.corpus_path / "meta" / "metadata.jsonl"
        self.inverted_index = {} 
        self.docs_meta = []

    def tokenize(self, text):
        return re.findall(r'[a-zа-я0-9]+', text.lower())

    def build(self):
        print("Начало индексации...")
        
        if not self.metadata_path.exists():
            print(f"Файл {self.metadata_path} не найден!")
            return

        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    doc_id_str = str(data.get('id', ''))
                    if doc_id_str.isdigit():
                        data['id'] = int(doc_id_str)
                        self.docs_meta.append(data)
                    else:
                        continue
                except:
                    continue

        print(f"Загружено {len(self.docs_meta)} документов. Сбор слов...")

        indexed_count = 0
        for doc in self.docs_meta:
            doc_id = doc['id']
            txt_path = self.text_dir / f"{doc_id}.txt"
            if not txt_path.exists(): 
                continue
            
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                words = set(self.tokenize(content))
                for word in words:
                    term = word[:TERM_SIZE-1] 
                    if term not in self.inverted_index:
                        self.inverted_index[term] = []
                    self.inverted_index[term].append(doc_id)
            
            indexed_count += 1
            if indexed_count % 2000 == 0:
                print(f"Обработано {indexed_count} текстов...")

        self._write_docs_bin()
        self._write_postings_and_dict()

    def _write_docs_bin(self):
        print("Запись forward.bin...")
        with open("forward.bin", "wb") as f:
            for doc in self.docs_meta:
                url = doc['url'].encode('utf-8')[:127]
                title = f"Drom News {doc['id']}".encode('utf-8')[:379]
                data = struct.pack("<I128s380s", doc['id'], url, title)
                f.write(data)

    def _write_postings_and_dict(self):
        print("Запись dictionary.bin и postings.bin...")
        
        with open("dictionary.bin", "wb") as f_dict, open("postings.bin", "wb") as f_post:
            offset = 0
            sorted_terms = sorted(self.inverted_index.keys())
            
            for term in sorted_terms:
                postings = sorted(list(set(self.inverted_index[term])))
                freq = len(postings)
                
                post_data = struct.pack(f"<{freq}I", *postings)
                f_post.write(post_data)
                
                term_bytes = term.encode('utf-8')[:TERM_SIZE-1]
                dict_entry = struct.pack(f"<{TERM_SIZE}sIQ", term_bytes, freq, offset)
                f_dict.write(dict_entry)
                
                offset += freq * 4 

if __name__ == "__main__":
    indexer = BinaryIndexer("drom_corpus")
    indexer.build()
    print("Индексация завершена успешно!")