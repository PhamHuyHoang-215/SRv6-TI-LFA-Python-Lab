
import json
from pathlib import Path

from topology_graph import build_graph
from dijkstra import dijkstra, get_path
from p_space import calculate_p_space
from q_space import calculate_q_space

# Topology 5 router
links = [
    ("r1", "r2", 10),
    ("r2", "r4", 10),
    ("r1", "r3", 10),
    ("r3", "r5", 10),
    ("r5", "r4", 30),
]

graph = build_graph(links)

source = "r1"
destination = "r4"
failed_neighbor = "r2"
pq_node = "r5"

# Tinh P-space va Q-space tren mang chua bi loi
p = set(calculate_p_space(graph, source, failed_neighbor))
q = set(calculate_q_space(
    graph, destination, source, failed_neighbor
))

if pq_node not in (p & q):
    raise ValueError("R5 khong phai PQ-node hop le")

# Kiem tra duong di den PQ-node
_, prev = dijkstra(graph, source)
path_to_pq = get_path(prev, source, pq_node)

# Kiem tra duong tu PQ-node den dich
_, prev = dijkstra(graph, pq_node)
path_to_dest = get_path(prev, pq_node, destination)

# Tao ke hoach sua chua truoc su co
repair_plan = {
    "protected_link": ["r1", "r2"],
    "destination": destination,
    "backup_next_hop": "r3",
    "pq_node": pq_node,
    "repair_list": ["2001:db8:200:5::1"],
    "path_to_pq": path_to_pq,
    "path_to_destination": path_to_dest,
    "status": "PRECOMPUTED"
}

# Luu ke hoach vao file JSON
output = Path(__file__).with_name("repair_plan.json")

with open(output, "w") as file:
    json.dump(repair_plan, file, indent=4)

print("=== PRECOMPUTED REPAIR PLAN ===")
print(json.dumps(repair_plan, indent=4))
print("\nSaved:", output)
