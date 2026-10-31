
from topology_graph import LINKS, build_graph
from dijkstra import dijkstra, get_path
from p_space import calculate_p_space
from q_space import calculate_q_space

# Thong tin bai toan
source = "r1"
destination = "r4"
failed_a = "r1"
failed_b = "r2"

# 1. Tao do thi ban dau
graph = build_graph(LINKS)

# 2. Tinh P-space va Q-space truoc su co
p_space = set(calculate_p_space(graph, source, failed_b))
q_space = set(calculate_q_space(
    graph, destination, failed_a, failed_b
))

# 3. Tim giao cua P-space va Q-space
pq_nodes = p_space.intersection(q_space)

# 4. Tao do thi khi lien ket R1-R2 bi hong
remaining_links = [
    (a, b, cost)
    for a, b, cost in LINKS
    if {a, b} != {failed_a, failed_b}
]

new_graph = build_graph(remaining_links)

# 5. Tinh duong di sau su co
distance, previous = dijkstra(new_graph, source)
post_path = get_path(previous, source, destination)

# 6. Chon PQ-node nam tren duong sau su co
valid_pq = [node for node in post_path if node in pq_nodes]

print("=== PQ-NODE CALCULATION ===")
print("P-space:", sorted(p_space))
print("Q-space:", sorted(q_space))
print("PQ-nodes:", sorted(pq_nodes))
print("Post-failure path:", " -> ".join(post_path))
print("PQ-node on repair path:", valid_pq)
