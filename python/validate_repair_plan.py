
import json
from pathlib import Path

from topology_graph import build_graph
from dijkstra import dijkstra, get_path

# Doc Repair Plan da tinh truoc
file_path = Path(__file__).with_name("repair_plan.json")

with open(file_path, "r") as f:
    plan = json.load(f)

# Topology 5 router
links = [
    ("r1", "r2", 10),
    ("r2", "r4", 10),
    ("r1", "r3", 10),
    ("r3", "r5", 10),
    ("r5", "r4", 30),
]

graph = build_graph(links)

source, failed_neighbor = plan["protected_link"]
destination = plan["destination"]
pq_node = plan["pq_node"]

# Kiem tra duong den PQ va duong den dich
full_path = (
    plan["path_to_pq"]
    + plan["path_to_destination"][1:]
)

assert full_path[0] == source
assert full_path[-1] == destination
assert plan["path_to_pq"][-1] == pq_node
assert plan["path_to_destination"][0] == pq_node
assert full_path[1] == plan["backup_next_hop"]

# Kiem tra moi lien ket tren duong du phong
for a, b in zip(full_path, full_path[1:]):
    assert b in graph[a], f"Lien ket {a}-{b} khong ton tai"
    assert {a, b} != {source, failed_neighbor}, \
        "Duong du phong su dung lien ket loi!"

# Kiem tra duong sau khi loai lien ket loi
new_graph = build_graph([
    (a, b, cost)
    for a, b, cost in links
    if {a, b} != {source, failed_neighbor}
])

distances, previous = dijkstra(new_graph, source)
backup_path = get_path(previous, source, destination)

assert full_path == backup_path

print("=== REPAIR PLAN VALIDATION ===")
print("Protected link:", source, "-", failed_neighbor)
print("Backup path:", " -> ".join(full_path))
print("Backup cost:", distances[destination])
print("PQ-node:", pq_node)
print("Repair List:", plan["repair_list"])
print("RESULT: VALID REPAIR PLAN")
