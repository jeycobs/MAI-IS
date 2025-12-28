import matplotlib.pyplot as plt

def graph(filename="frequencies.txt"):
    ranks = []
    frequencies = []
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for rank, line in enumerate(f, 1):
                parts = line.strip().split()
                if len(parts) >= 2:
                    frequencies.append(int(parts[0]))
                    ranks.append(rank)
                if rank >= 20000: break 
    except FileNotFoundError:
        print("файл frequencies.txt не найден.")
        return

    if not frequencies:
        print("Нет данных.")
        return

    C = frequencies[0]
    zipf_ideal = [C / r for r in ranks]

    plt.figure(figsize=(10, 6))
    plt.loglog(ranks, frequencies, '.', label='эмпирические данные (Drom)', markersize=2)
    plt.loglog(ranks, zipf_ideal, 'r--', label='идеальный Закон Ципфа', linewidth=2)
    
    plt.title('Закон Ципфа')
    plt.xlabel('ранг(log)')
    plt.ylabel('частота (log)')
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend()
    
    plt.savefig('graph.png')
    plt.show()

if __name__ == "__main__":
    graph()