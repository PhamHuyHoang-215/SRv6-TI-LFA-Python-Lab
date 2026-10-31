# Mo hinh mang dung cho thuat toan TI-LFA

# (Router A, Router B, Chi phi lien ket)
LINKS = [
    ("r1", "r2", 10),
    ("r1", "r3", 20),
    ("r2", "r4", 10),
    ("r3", "r4", 10),
]

def build_graph(links):
    graph = {}

    for a, b, cost in links:
        graph.setdefault(a, {})[b] = cost
        graph.setdefault(b, {})[a] = cost

    return graph


if __name__ == "__main__":
    graph = build_graph(LINKS)

    print("=== SRv6 NETWORK GRAPH ===")

    for router in sorted(graph):
        print(f"{router}: {graph[router]}")
