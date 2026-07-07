from config import MIN_CIRCUIT_DISTANCE, MAX_NOISE_THRESHOLD, Porcentaje_util
import networkx as nx
from networkx.algorithms import isomorphism
from collections import deque
import time

def calculate_dynamic_noise_threshold(G, percentile=Porcentaje_util):
    """
    Calcula un umbral dinámico de ruido basado en los percentiles de la máquina.
    Por defecto usa el percentil 95, permitiendo usar el 95% de los qubits.
    """
    noise_values = [G.nodes[n]['noise'] for n in G.nodes()]
    noise_values.sort()
    index = int(len(noise_values) * percentile / 100)
    dynamic_threshold = noise_values[min(index, len(noise_values) - 1)]
    print(f" Umbral dinámico calculado: {dynamic_threshold:.4f} (percentil {percentile})")
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

def bfs_connected_groups(G, start, size, used_nodes, noise_threshold=None, max_solutions=3, max_iterations=1000):
    """
    Búsqueda BFS optimizada con límites AGRESIVOS para evitar explosión exponencial.
    """
    if noise_threshold is None:
        noise_threshold = MAX_NOISE_THRESHOLD
    
    if start in used_nodes or G.nodes[start]['noise'] > noise_threshold:
        return []
        
    queue = deque([[start]])
    groups = []
    iterations = 0

    while queue and len(groups) < max_solutions and iterations < max_iterations:
        iterations += 1
        path = queue.popleft()
        
        if len(path) == size:
            if all(G.nodes[n]['noise'] <= noise_threshold for n in path):
                if is_far_enough(G, path, used_nodes):
                    groups.append(list(path))
                    if len(groups) >= max_solutions:
                        break
            continue

        if len(path) < size:
            for neighbor in G.neighbors(path[-1]):
                if neighbor not in path and neighbor not in used_nodes:
                    if G.nodes[neighbor]['noise'] <= noise_threshold:
                        queue.append(path + [neighbor])
    
    if iterations >= max_iterations and not groups:
        print(f"⚠️ BFS timeout para size={size} (sin soluciones en {max_iterations} iteraciones)")
    
    return groups

def find_best_placement_with_sentinel(G, size, used_nodes, noise_threshold):
    """
    Busca un grupo de 'size' qubits (isla) + 1 qubit extra (centinela) adyacente,
    garantizando que la isla y el centinela mantengan la distancia requerida de otras islas.
    """
    best_group = None
    best_centinela = None
    best_noise = float('inf')

    sorted_nodes = sorted(
        [n for n in G.nodes if n not in used_nodes and G.nodes[n]['noise'] <= noise_threshold],
        key=lambda n: G.nodes[n]['noise']
    )
    
    max_nodes_to_explore = min(10, len(sorted_nodes))
    
    for node in sorted_nodes[:max_nodes_to_explore]:
        candidate_groups = bfs_connected_groups(G, node, size, used_nodes, noise_threshold, max_solutions=2)
        
        for group in candidate_groups:
            candidatos_centinela = []
            
            # Buscar vecinos disponibles para hacer de centinela
            for isla_node in group:
                for vecino in G.neighbors(isla_node):
                    if vecino not in used_nodes and vecino not in group:
                        if G.nodes[vecino]['noise'] <= noise_threshold:
                            candidatos_centinela.append(vecino)
            
            if candidatos_centinela:
                # Escoger el centinela con el menor ruido térmico
                centinela = min(candidatos_centinela, key=lambda n: G.nodes[n]['noise'])
                all_nodes = group + [centinela]
                
                # Verificar que la estructura COMPLETA (Isla + Centinela) está lejos de islas previas
                if is_far_enough(G, all_nodes, used_nodes):
                    total_noise = sum(G.nodes[n]['noise'] for n in group) + G.nodes[centinela]['noise']
                    
                    if total_noise < best_noise:
                        best_noise = total_noise
                        best_group = group
                        best_centinela = centinela
                        
    return best_group, best_centinela

def place_circuits_logical(G, circuits, max_time_seconds=30, sentinel_mode=None):
    """
    Asigna circuitos a qubits físicos.
    Si 'sentinel_mode' tiene un valor (ej: 'standard', 'robust'), fuerza la reserva de un centinela.
    """
    placed = []
    errors = []
    used_nodes = set()
    start_time = time.time()
    
    dynamic_threshold = calculate_dynamic_noise_threshold(G, percentile=Porcentaje_util)
    noise_threshold = dynamic_threshold
    print(f" Usando umbral de ruido: {noise_threshold:.4f}")
    
    if sentinel_mode:
        print(f"🛡️ MODO FTQC ACTIVADO: Reservando centinelas tipo '{sentinel_mode}'")

    for idx, circuit in enumerate(circuits):
        elapsed = time.time() - start_time
        if elapsed > max_time_seconds:
            print(f" TIMEOUT GLOBAL: {elapsed:.2f}s > {max_time_seconds}s. Procesados {len(placed)}/{len(circuits)} circuitos.")
            remaining = [c['id'] for c in circuits if c['id'] not in [p[0] for p in placed]]
            for cid in remaining:
                errors.append(f"Circuito {cid} no procesado por timeout global")
            break
        
        if idx % 5 == 0:
            print(f" Progreso: {idx}/{len(circuits)} circuitos procesados ({elapsed:.1f}s transcurridos)")

        size = circuit['size']

        # =====================================================================
        # RAMA 1: ASIGNACIÓN CON PROTECCIÓN (ISLA + CENTINELA)
        # =====================================================================
        if sentinel_mode:
            isla_data, centinela = find_best_placement_with_sentinel(G, size, used_nodes, noise_threshold)
            
            if isla_data and centinela:
                all_nodes = isla_data + [centinela]
                used_nodes.update(all_nodes)
                
                # Devolvemos un DICCIONARIO para que el ensamblador sepa inyectar el código QASM
                mapeo_estructurado = {
                    'data': isla_data,
                    'sentinel': centinela,
                    'mode': sentinel_mode
                }
                placed.append((circuit['id'], mapeo_estructurado))
                print(f"  [+] Isla {circuit['id']} mapeada: Datos={isla_data}, Centinela={centinela}")
            else:
                reason = f"Circuito {circuit['id']} no pudo asignar Isla+Centinela: espacio/ruido insuficiente."
                errors.append(reason)
            
            continue # Saltamos la rama clásica y vamos al siguiente circuito

        # =====================================================================
        # RAMA 2: ASIGNACIÓN CLÁSICA (SIN CENTINELAS)
        # =====================================================================
        if 'edges' in circuit and circuit['edges'] and size <= 4:
            logical_graph = nx.Graph()
            logical_graph.add_nodes_from(range(size))
            logical_graph.add_edges_from(circuit['edges'])
            mapping = find_isomorphic_subgraph(G, logical_graph, used_nodes, noise_threshold)

            if mapping:
                used_nodes.update(mapping)
                placed.append((circuit['id'], mapping))
                continue
            else:
                print(f"⚠️ No se encontró isomorfismo para circuito {circuit['id']}, usando BFS optimizado")

        if 'edges' in circuit and circuit['edges']:
            logical_graph = nx.Graph()
            logical_graph.add_nodes_from(range(size))
            logical_graph.add_edges_from(circuit['edges'])
            components = list(nx.connected_components(logical_graph))
            
            if len(components) > 1:
                all_assigned = []
                success = True
                
                for component in components:
                    comp_size = len(component)
                    if comp_size == 1:
                        best_node = None
                        best_noise = float('inf')
                        
                        for node in G.nodes:
                            if node in used_nodes:
                                continue
                            node_noise = G.nodes[node]['noise']
                            if node_noise <= noise_threshold and node_noise < best_noise:
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
                        best_group = None
                        best_noise = float('inf')
                        sorted_nodes = sorted(
                            [n for n in G.nodes if n not in used_nodes and G.nodes[n]['noise'] <= noise_threshold],
                            key=lambda n: G.nodes[n]['noise']
                        )
                        max_nodes_to_explore = min(5, len(sorted_nodes))
                        
                        for node in sorted_nodes[:max_nodes_to_explore]:
                            candidate_groups = bfs_connected_groups(G, node, comp_size, used_nodes, noise_threshold, max_solutions=2)
                            if candidate_groups:
                                for group in candidate_groups:
                                    total_noise = sum(G.nodes[n]['noise'] for n in group)
                                    if total_noise < best_noise:
                                        best_noise = total_noise
                                        best_group = group
                                break
                        
                        if best_group:
                            used_nodes.update(best_group)
                            all_assigned.extend(best_group)
                        else:
                            success = False
                            break
                
                if success:
                    placed.append((circuit['id'], all_assigned))
                    continue
                else:
                    for node in all_assigned:
                        used_nodes.discard(node)
        
        # Mapeo estándar (sin isomorfismo ni desconexiones)
        best_group = None
        best_noise = float('inf')
        sorted_nodes = sorted(
            [n for n in G.nodes if n not in used_nodes and G.nodes[n]['noise'] <= noise_threshold],
            key=lambda n: G.nodes[n]['noise']
        )
        max_nodes_to_explore = min(10, len(sorted_nodes))
        
        for node in sorted_nodes[:max_nodes_to_explore]:
            candidate_groups = bfs_connected_groups(G, node, size, used_nodes, noise_threshold, max_solutions=2)
            if candidate_groups:
                for group in candidate_groups:
                    total_noise = sum(G.nodes[n]['noise'] for n in group)
                    if total_noise < best_noise:
                        best_noise = total_noise
                        best_group = group
                break

        if best_group:
            used_nodes.update(best_group)
            placed.append((circuit['id'], best_group))
        else:
            reason = f"Circuito {circuit['id']} no se pudo asignar clásicamente."
            errors.append(reason)

    return placed, errors