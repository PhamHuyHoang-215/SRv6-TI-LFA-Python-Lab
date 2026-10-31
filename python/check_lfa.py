
from topology_graph import build_graph
from dijkstra import dijkstra

# Topology TI-LFA 5 router
LINKS = [
    ("r1", "r2", 10),
    ("r2", "r4", 10),
    ("r1", "r3", 10),
    ("r3", "r5", 10),
    ("r5", "r4", 30),
]

graph = build_graph(LINKS)

source = "r1"
neighbor = "r3"
destination = "r4"

# Tinh khoang cach ngan nhat
dist_source, _ = dijkstra(graph, source)
dist_neighbor, _ = dijkstra(graph, neighbor)

d_nd = dist_neighbor[destination]
d_ns = dist_neighbor[source]
d_sd = dist_source[destination]

# Dieu kien Loop-Free Alternate
is_lfa = d_nd < d_ns + d_sd

print("=== CHECK LFA CONDITION ===")
print("D(R3,R4):", d_nd)
print("D(R3,R1):", d_ns)
print("D(R1,R4):", d_sd)

print("\nLFA condition:")
print(f"{d_nd} < {d_ns} + {d_sd}")

if is_lfa:
    print("RESULT: LFA AVAILABLE")
else:
    print("RESULT: NO DIRECT LFA")
    print("Need remote repair using Segment Routing")
