import struct
from flask import Flask, request, render_template_string

app = Flask(__name__)

DICT_STRUCT = struct.Struct("<32sIQ")
DOC_STRUCT = struct.Struct("<I128s124s")

class Searcher:
    def _get_postings(self, word):
        word = word.lower().strip()
        if not os.path.exists("dictionary.bin"): return []
        
        with open("dictionary.bin", "rb") as f:
            f.seek(0, 2)
            num_terms = f.tell() // DICT_STRUCT.size
            
            low, high = 0, num_terms - 1
            while low <= high:
                mid = (low + high) // 2
                f.seek(mid * DICT_STRUCT.size)
                data = f.read(DICT_STRUCT.size)
                term_b, freq, offset = DICT_STRUCT.unpack(data)
                
                current_term = term_b.decode('utf-8', errors='ignore').strip('\x00')
                
                if current_term == word:
                    with open("postings.bin", "rb") as pf:
                        pf.seek(offset)
                        ids_data = pf.read(freq * 4)
                        return list(struct.unpack(f"<{freq}I", ids_data))
                elif current_term < word:
                    low = mid + 1
                else:
                    high = mid - 1
        return []

    def get_doc_info(self, doc_id):
        return {"url": f"https://news.drom.ru/{doc_id}.html", "title": f"Новость {doc_id}"}

searcher = Searcher()

@app.route("/")
def index():
    query = request.args.get("q", "")
    results = []
    if query:
        ids = searcher._get_postings(query)
        results = [searcher.get_doc_info(idx) for idx in ids[:50]]
    
    return render_template_string("""
        <form>
            <input name="q" value="{{q}}">
            <button>Поиск</button>
        </form>
        <ul>
        {% for res in results %}
            <li><a href="{{res.url}}">{{res.title}}</a></li>
        {% endfor %}
        </ul>
    """, q=query, results=results)

if __name__ == "__main__":
    import os
    app.run(port=5000)