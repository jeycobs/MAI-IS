import sys
import os
from pathlib import Path

POSSIBLE_PATHS = [
    Path("drom_corpus/text"),
    Path("../lab1/drom_corpus/text"),
    Path("../drom_corpus/text")
]

def extract_text():
    corpus_dir = None
    for p in POSSIBLE_PATHS:
        if p.exists() and p.is_dir():
            corpus_dir = p
            break
            
    if not corpus_dir:
        hard_path = Path("/Users/grinya/Documents/study/s4e1/is/lab1/drom_corpus/text")
        if hard_path.exists():
            corpus_dir = hard_path
        else:
            print(f"ОШИБКА: Папка с текстами не найдена!", file=sys.stderr)
            sys.exit(1)

    files = list(corpus_dir.glob("*.txt"))
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sys.stdout.write(f.read() + "\n")
        except: pass

if __name__ == "__main__":
    extract_text()
