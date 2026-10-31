
from topology_graph import LINKS, build_graph
from dijkstra import dijkstra, get_path

# Router nguon va dich
source = "r1"
destination = "r4"

# Mang hoat dong binh thuong
graph = build_graph(LINKS)

distance, previous = dijkstra(graph, source)
path = get_path(previous, source, destination)

print("=== TRUOC KHI XAY RA SU CO ===")
print("Duong di:", " -> ".join(path))
print("Chi phi:", distance[destination])

# Mo phong dut lien ket R1 - R2
remaining_links = [
    (a, b, cost)
    for a, b, cost in LINKS
    if {a, b} != {"r1", "r2"}
]

# Tao lai do thi sau su co
new_graph = build_graph(remaining_links)

distance, previous = dijkstra(new_graph, source)
path = get_path(previous, source, destination)

print("\n=== SAU KHI R1 - R2 BI DUT ===")
print("Duong di:", " -> ".join(path))
print("Chi phi:", distance[destination])
