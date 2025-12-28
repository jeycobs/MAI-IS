import matplotlib.pyplot as plt
def graph(filename="frequencies.txt"):
    ranks, freqs = [], []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for r, l in enumerate(f, 1):
                p = l.strip().split()
                if len(p) >= 2: freqs.append(int(p[0])); ranks.append(r)
                if r >= 20000: break
    except: return
    if not freqs: return
    
    plt.loglog(ranks, freqs, '.', label='Данные')
    plt.loglog(ranks, [freqs[0]/r for r in ranks], 'r--', label='Ципф')
    plt.legend(); plt.grid(True); plt.savefig('graph.png'); print("График готов!")

if __name__ == "__main__": graph()
