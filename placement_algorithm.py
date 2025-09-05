from config import MIN_CIRCUIT_DISTANCE, MAX_NOISE_THRESHOLD
import networkx as nx
from collections import deque

def is_far_enough(G, candidate_nodes, used_nodes):
    for u in candidate_nodes:
        for v in used_nodes:
            try:
                if nx.shortest_path_length(G, u, v) <= MIN_CIRCUIT_DISTANCE:
                    return False
            except nx.NetworkXNoPath:
                continue
    return True

def bfs_connected_groups(G, start, size, used_nodes):
    visited = set()
    queue = deque([[start]])
    groups = []

    while queue:
        path = queue.popleft()
        if len(path) == size:
            if all(G.nodes[n]['noise'] <= MAX_NOISE_THRESHOLD for n in path):
                if is_far_enough(G, path, used_nodes):
                    groups.append(list(path))
            continue

        for neighbor in G.neighbors(path[-1]):
            if neighbor not in path and neighbor not in used_nodes:
                queue.append(path + [neighbor])
    return groups

def place_circuits(G, circuits):
    placed = []
    errors = []
    used_nodes = set()

    for circuit in circuits:
        size = circuit['size']
        best_group = None
        best_noise = float('inf')

        for node in G.nodes:
            if node in used_nodes or G.nodes[node]['noise'] > MAX_NOISE_THRESHOLD:
                continue

            candidate_groups = bfs_connected_groups(G, node, size, used_nodes)

            for group in candidate_groups:
                total_noise = sum(G.nodes[n]['noise'] for n in group)
                if total_noise < best_noise:
                    best_noise = total_noise
                    best_group = group

        if best_group:
            used_nodes.update(best_group)
            placed.append((circuit['id'], best_group))
        else:
            reason = f"Circuito {circuit['id']} no se pudo asignar: "
            reason += f"no hay {size} qubits adyacentes y conectados con ruido ≤ {MAX_NOISE_THRESHOLD} "
            reason += f"y separados al menos {MIN_CIRCUIT_DISTANCE} de otros."
            errors.append(reason)

    return placed, errors
