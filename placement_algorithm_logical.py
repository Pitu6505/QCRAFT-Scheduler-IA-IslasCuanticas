# Nuevo archivo: placement_algorithm_logical.py

from config import MIN_CIRCUIT_DISTANCE, MAX_NOISE_THRESHOLD
import networkx as nx
from networkx.algorithms import isomorphism
from collections import deque

def calculate_dynamic_noise_threshold(G, percentile=95):
    """
    Calcula un umbral dinámico de ruido basado en los percentiles de la máquina.
    Por defecto usa el percentil 95, permitiendo usar el 95% de los qubits.
    """
    noise_values = [G.nodes[n]['noise'] for n in G.nodes()]
    noise_values.sort()
    index = int(len(noise_values) * percentile / 100)
    dynamic_threshold = noise_values[min(index, len(noise_values) - 1)]
    print(f"🎯 Umbral dinámico calculado: {dynamic_threshold:.4f} (percentil {percentile})")
    return dynamic_threshold

def is_far_enough(G, candidate_nodes, used_nodes):
    for u in candidate_nodes:
        for v in used_nodes:
            try:
                if nx.shortest_path_length(G, u, v) <= MIN_CIRCUIT_DISTANCE:
                    return False
            except nx.NetworkXNoPath:
                continue
    return True

def find_isomorphic_subgraph(G, logical_graph, used_nodes, noise_threshold=None):
    if noise_threshold is None:
        noise_threshold = MAX_NOISE_THRESHOLD
    
    for nodes_subset in nx.algorithms.components.connected_components(G):
        if len(nodes_subset) < logical_graph.number_of_nodes():
            continue
        subgraph = G.subgraph(nodes_subset)

        matcher = isomorphism.GraphMatcher(
            subgraph,
            logical_graph,
            node_match=lambda n1, n2: n1.get("noise", 0) <= noise_threshold
        )
        for match in matcher.subgraph_isomorphisms_iter():
            candidate = list(match.keys())
            if all(G.nodes[n]['noise'] <= noise_threshold for n in candidate):
                if is_far_enough(G, candidate, used_nodes):
                    return candidate
    return None

def bfs_connected_groups(G, start, size, used_nodes, noise_threshold=None):
    if noise_threshold is None:
        noise_threshold = MAX_NOISE_THRESHOLD
        
    visited = set()
    queue = deque([[start]])
    groups = []

    while queue:
        path = queue.popleft()
        if len(path) == size:
            if all(G.nodes[n]['noise'] <= noise_threshold for n in path):
                if is_far_enough(G, path, used_nodes):
                    groups.append(list(path))
            continue

        for neighbor in G.neighbors(path[-1]):
            if neighbor not in path and neighbor not in used_nodes:
                queue.append(path + [neighbor])
    return groups

def place_circuits_logical(G, circuits):
    placed = []
    errors = []
    used_nodes = set()
    
    # Calcular umbral dinámico basado en la máquina actual
    dynamic_threshold = calculate_dynamic_noise_threshold(G, percentile=95)
    noise_threshold = max(MAX_NOISE_THRESHOLD, dynamic_threshold)  # Usar el mayor
    print(f"🔧 Usando umbral de ruido: {noise_threshold:.4f}")

    for circuit in circuits:
        if 'edges' in circuit and circuit['edges']:
            logical_graph = nx.Graph()
            logical_graph.add_nodes_from(range(circuit['size']))  # Añadir TODOS los nodos primero
            logical_graph.add_edges_from(circuit['edges'])
            mapping = find_isomorphic_subgraph(G, logical_graph, used_nodes, noise_threshold)

            if mapping:
                used_nodes.update(mapping)
                placed.append((circuit['id'], mapping))
                continue
            else:
                print(f"⚠️ No se encontró estructura lógica para circuito {circuit['id']}, se intentará mapeo estándar")

        # Modo estándar si no se pudo mapear lógica
        size = circuit['size']
        
        # Si el circuito tiene edges definidos, obtener componentes conectados
        if 'edges' in circuit and circuit['edges']:
            logical_graph = nx.Graph()
            logical_graph.add_nodes_from(range(size))  # Asegurar que todos los nodos existen
            logical_graph.add_edges_from(circuit['edges'])
            components = list(nx.connected_components(logical_graph))
            
            print(f"🔍 [DEBUG] Circuito {circuit['id']}: size={size}, edges={circuit['edges']}, componentes={components}")
            
            # Si hay componentes desconectados, asignar cada uno por separado
            if len(components) > 1:
                print(f"  → Detectados {len(components)} componentes desconectados, asignando por separado...")
                all_assigned = []
                success = True
                
                for component in components:
                    comp_size = len(component)
                    
                    # Para nodos aislados (sin conexiones), asignar un solo qubit
                    if comp_size == 1:
                        best_node = None
                        best_noise = float('inf')
                        
                        for node in G.nodes:
                            if node in used_nodes:
                                continue
                            node_noise = G.nodes[node]['noise']
                            if node_noise <= noise_threshold and node_noise < best_noise:
                                # Verificar distancia mínima
                                if is_far_enough(G, [node], used_nodes):
                                    best_noise = node_noise
                                    best_node = node
                        
                        if best_node is not None:
                            used_nodes.add(best_node)
                            all_assigned.append(best_node)
                        else:
                            success = False
                            break
                    else:
                        # Para componentes conectados, usar BFS
                        best_group = None
                        best_noise = float('inf')
                        
                        for node in G.nodes:
                            if node in used_nodes or G.nodes[node]['noise'] > noise_threshold:
                                continue
                            
                            candidate_groups = bfs_connected_groups(G, node, comp_size, used_nodes, noise_threshold)
                            
                            for group in candidate_groups:
                                total_noise = sum(G.nodes[n]['noise'] for n in group)
                                if total_noise < best_noise:
                                    best_noise = total_noise
                                    best_group = group
                        
                        if best_group:
                            used_nodes.update(best_group)
                            all_assigned.extend(best_group)
                        else:
                            success = False
                            break
                
                if success:
                    print(f"  ✅ Asignación exitosa de componentes: {all_assigned}")
                    placed.append((circuit['id'], all_assigned))
                    continue
                else:
                    # Revertir nodos usados si falló
                    for node in all_assigned:
                        used_nodes.discard(node)
        
        # Mapeo estándar para circuitos sin estructura o componentes completamente conectados
        best_group = None
        best_noise = float('inf')

        for node in G.nodes:
            if node in used_nodes or G.nodes[node]['noise'] > noise_threshold:
                continue

            candidate_groups = bfs_connected_groups(G, node, size, used_nodes, noise_threshold)

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
            reason += f"no hay {circuit['size']} qubits adyacentes y conectados con ruido ≤ {noise_threshold:.4f} "
            reason += f"y separados al menos {MIN_CIRCUIT_DISTANCE} de otros."
            errors.append(reason)

    return placed, errors