
from topology_graph import build_graph
from dijkstra import dijkstra, get_path
from p_space import calculate_p_space
from q_space import calculate_q_space

# Topology mo rong de nghien cuu TI-LFA
LINKS_TILFA = [
    ("r1", "r2", 10),
    ("r2", "r4", 10),
    ("r1", "r3", 10),
    ("r3", "r5", 10),
    ("r5", "r4", 30),
]

source = "r1"
destination = "r4"
failed_neighbor = "r2"

# Tao do thi truoc su co
graph = build_graph(LINKS_TILFA)

# Tinh duong chinh
old_dist, old_prev = dijkstra(graph, source)
old_path = get_path(old_prev, source, destination)

# Tinh P-space va Q-space
p = set(calculate_p_space(graph, source, failed_neighbor))

q = set(calculate_q_space(
    graph, destination, source, failed_neighbor
))

pq = p & q

# Gia lap hong lien ket R1 - R2
remaining_links = [
    (a, b, cost)
    for a, b, cost in LINKS_TILFA
    if {a, b} != {source, failed_neighbor}
]

new_graph = build_graph(remaining_links)

new_dist, new_prev = dijkstra(new_graph, source)
new_path = get_path(new_prev, source, destination)

# Tim PQ-node o xa tren duong sau su co
remote_pq = [
    node for node in new_path
    if node in pq and node not in graph[source]
    and node != source
]

print("=== TI-LFA ADVANCED TOPOLOGY ===")
print("Primary path:", " -> ".join(old_path))
print("Primary cost:", old_dist[destination])
print("P-space:", sorted(p))
print("Q-space:", sorted(q))
print("PQ-nodes:", sorted(pq))
print("Backup path:", " -> ".join(new_path))
print("Backup cost:", new_dist[destination])
print("Remote PQ-nodes:", remote_pq)


# Buoc 4.11: Tao Repair List tu Remote PQ-node

SID_MAP = {
    "r5": "2001:db8:200:5::1"
}

def uses_failed_link(path, a, b):
    return any(
        {path[i], path[i + 1]} == {a, b}
        for i in range(len(path) - 1)
    )


if remote_pq:
    pq_node = remote_pq[0]

    # Kiem tra duong di toi PQ-node truoc su co
    _, prev_to_pq = dijkstra(graph, source)
    path_to_pq = get_path(prev_to_pq, source, pq_node)

    # Kiem tra duong tu PQ-node den dich truoc su co
    _, prev_to_dest = dijkstra(graph, pq_node)
    path_to_dest = get_path(
        prev_to_dest, pq_node, destination
    )

    if (uses_failed_link(path_to_pq, source, failed_neighbor)
            or uses_failed_link(path_to_dest, source, failed_neighbor)):
        raise ValueError("Repair path khong an toan")

    repair_list = [SID_MAP[pq_node]]

    print("\n=== TI-LFA REPAIR LIST ===")
    print("PQ-node:", pq_node)
    print("Path to PQ:", " -> ".join(path_to_pq))
    print("Path to destination:", " -> ".join(path_to_dest))
    print("Repair List:", repair_list)
else:
    print("Khong tim thay Remote PQ-node")
