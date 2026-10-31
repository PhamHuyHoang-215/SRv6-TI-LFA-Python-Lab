
from topology_graph import LINKS, build_graph
from dijkstra import dijkstra


def calculate_p_space(graph, source, failed_neighbor):
    # Khoang cach ngan nhat truoc su co
    dist_source, _ = dijkstra(graph, source)
    dist_neighbor, _ = dijkstra(graph, failed_neighbor)

    # Chi phi lien ket can bao ve
    link_cost = graph[source][failed_neighbor]

    p_space = []

    for node in sorted(graph):
        shortest = dist_source[node]

        # Chi phi di qua lien ket can bao ve
        via_failed_link = link_cost + dist_neighbor[node]

        # Chi giu node neu khong co duong ngan nhat
        # nao su dung lien ket can bao ve
        if shortest < via_failed_link:
            p_space.append(node)

    return p_space


if __name__ == "__main__":
    graph = build_graph(LINKS)

    source = "r1"
    failed_neighbor = "r2"

    result = calculate_p_space(
        graph, source, failed_neighbor
    )

    print("=== P-SPACE CALCULATION ===")
    print("Router bao ve:", source)
    print("Lien ket can bao ve: r1 - r2")
    print("P-space:", result)
