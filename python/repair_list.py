
from topology_graph import LINKS, build_graph
from dijkstra import dijkstra, get_path
from p_space import calculate_p_space
from q_space import calculate_q_space


def calculate_repair(graph, source, destination, failed_neighbor):

    # Buoc 1: Tinh P-space va Q-space
    p = set(calculate_p_space(graph, source, failed_neighbor))

    q = set(calculate_q_space(
        graph, destination, source, failed_neighbor
    ))

    pq = p & q

    # Buoc 2: Tao ban sao do thi, loai lien ket loi
    new_graph = {
        node: neighbors.copy()
        for node, neighbors in graph.items()
    }

    del new_graph[source][failed_neighbor]
    del new_graph[failed_neighbor][source]

    # Buoc 3: Tinh duong sau su co
    distances, previous = dijkstra(new_graph, source)
    path = get_path(previous, source, destination)

    if len(path) < 2:
        raise ValueError("Khong tim thay duong du phong")

    # Buoc 4: Kiem tra hang xom tren duong thay the
    next_hop = path[1]

    if next_hop in pq:
        repair_list = []
        repair_type = "DIRECT_LFA"
    else:
        repair_list = None
        repair_type = "CAN_TINH_REPAIR_LIST_BANG_SID"

    return repair_type, next_hop, repair_list, path


if __name__ == "__main__":
    graph = build_graph(LINKS)

    result = calculate_repair(
        graph,
        source="r1",
        destination="r4",
        failed_neighbor="r2"
    )

    repair_type, next_hop, repair_list, path = result

    print("=== REPAIR PATH CALCULATION ===")
    print("Loai bao ve:", repair_type)
    print("Next-hop du phong:", next_hop)
    print("Repair List:", repair_list)
    print("Duong thay the:", " -> ".join(path))
