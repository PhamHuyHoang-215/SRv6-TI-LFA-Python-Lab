
import heapq
from topology_graph import LINKS, build_graph

# Ham tinh duong di ngan nhat
def dijkstra(graph, start):
    distance = {node: float("inf") for node in graph}
    previous = {node: None for node in graph}

    distance[start] = 0
    queue = [(0, start)]

    while queue:
        current_cost, current = heapq.heappop(queue)

        if current_cost > distance[current]:
            continue

        for neighbor, weight in graph[current].items():
            new_cost = current_cost + weight

            if new_cost < distance[neighbor]:
                distance[neighbor] = new_cost
                previous[neighbor] = current
                heapq.heappush(queue, (new_cost, neighbor))

    return distance, previous


# Ham truy vet duong di
def get_path(previous, start, end):
    path = []
    current = end

    while current is not None:
        path.append(current)

        if current == start:
            return path[::-1]

        current = previous[current]

    return []


# Chuong trinh chinh
if __name__ == "__main__":
    graph = build_graph(LINKS)

    start = "r1"
    end = "r4"

    distance, previous = dijkstra(graph, start)
    path = get_path(previous, start, end)

    print("=== DIJKSTRA SHORTEST PATH ===")
    print("Duong di:", " -> ".join(path))
    print("Tong chi phi:", distance[end])
