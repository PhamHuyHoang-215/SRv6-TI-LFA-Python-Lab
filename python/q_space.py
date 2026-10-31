
from topology_graph import LINKS, build_graph
from dijkstra import dijkstra


def calculate_q_space(graph, destination, failed_a, failed_b):
    # Chi phi cua lien ket can bao ve
    link_cost = graph[failed_a][failed_b]

    # Tinh khoang cach ngan nhat tu cac node
    dist_dest, _ = dijkstra(graph, destination)
    dist_a, _ = dijkstra(graph, failed_a)
    dist_b, _ = dijkstra(graph, failed_b)

    q_space = []

    for node in sorted(graph):
        # Khoang cach ngan nhat den dich
        shortest = dist_dest[node]

        # Duong di qua lien ket loi theo hai chieu
        via_ab = (
            dist_a[node] + link_cost
            + dist_b[destination]
        )

        via_ba = (
            dist_b[node] + link_cost
            + dist_a[destination]
        )

        # Loai bo node neu co duong ngan nhat
        # di qua lien ket can bao ve
        if shortest < via_ab and shortest < via_ba:
            q_space.append(node)

    return q_space


if __name__ == "__main__":
    graph = build_graph(LINKS)

    result = calculate_q_space(
        graph,
        destination="r4",
        failed_a="r1",
        failed_b="r2"
    )

    print("=== Q-SPACE CALCULATION ===")
    print("Destination: r4")
    print("Protected link: r1 - r2")
    print("Q-space:", result)
