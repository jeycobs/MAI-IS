import os
import json
import struct
import re
from pathlib import Path

DICT_STRUCT = struct.Struct("<32sIQ") 
DOC_STRUCT = struct.Struct("<I128s124s")

def build_index(corpus_dir):
    corpus_path = Path(corpus_dir)
    meta_file = corpus_path / "meta" / "metadata.jsonl"
    text_dir = corpus_path / "text"
    
    inverted_index = {} 
    docs_for_forward = []

    print("Шаг 1: Чтение метаданных...")
    if not meta_file.exists():
        print(f"Ошибка: Файл {meta_file} не найден!")
        return

    with open(meta_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                if str(data['id']).isdigit():
                    docs_for_forward.append(data)
                else:
                    print(f"Пропуск некорректного ID: {data['id']}")
            except (json.JSONDecodeError, KeyError):
                continue

    print(f"Загружено метаданных для {len(docs_for_forward)} документов.")

    print("Шаг 2: Токенизация и сбор слов...")
    indexed_count = 0
    for doc in docs_for_forward:
        doc_id = int(doc['id'])
        txt_path = text_dir / f"{doc_id}.txt"
        
        if txt_path.exists():
            with open(txt_path, 'r', encoding='utf-8') as f:
                text = f.read().lower()
                words = set(re.findall(r'[a-zа-я0-9]+', text))
                for word in words:
                    if len(word) > 31: word = word[:31]
                    if word not in inverted_index:
                        inverted_index[word] = []
                    inverted_index[word].append(doc_id)
            indexed_count += 1
            if indexed_count % 1000 == 0:
                print(f"Обработано {indexed_count} файлов...")

    print(f"Шаг 3: Запись forward.bin (всего {len(docs_for_forward)} записей)...")
    with open("forward.bin", "wb") as f:
        for doc in docs_for_forward:
            try:
                doc_id = int(doc['id'])
                url = doc['url'].encode('utf-8')[:127]
                title = f"Drom Article {doc_id}".encode('utf-8')[:123]
                f.write(DOC_STRUCT.pack(doc_id, url, title))
            except Exception as e:
                print(f"Ошибка записи документа {doc.get('id')}: {e}")

    print("Шаг 4: Запись dictionary.bin и postings.bin...")
    with open("dictionary.bin", "wb") as f_dict, open("postings.bin", "wb") as f_post:
        current_offset = 0
        sorted_terms = sorted(inverted_index.keys())
        print(f"Всего уникальных термов: {len(sorted_terms)}")

        for term in sorted_terms:
            postings = sorted(list(set(inverted_index[term]))) 
            freq = len(postings)
            
            post_data = struct.pack(f"<{freq}I", *postings)
            f_post.write(post_data)
            
            term_bytes = term.encode('utf-8').ljust(32, b'\x00')
            f_dict.write(DICT_STRUCT.pack(term_bytes, freq, current_offset))
            
            current_offset += freq * 4

    print("=== Успех! Индексация завершена ===")

if __name__ == "__main__":
    build_index("drom_corpus")