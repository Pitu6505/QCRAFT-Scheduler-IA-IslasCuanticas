import networkx as nx
import math

# Pesos configurables
ALPHA = 0.3  # peso del error de lectura
BETA = 0.35    # peso de 1/T1
GAMMA = 0.35   # peso de 1/T2

def build_graph(coupling_map, properties, partition_mode=False, partition_index=1, partitions=4, partition_ranges=None):
    """
    Construye el grafo de qubits.
    - partition_mode: activar particionado (bool).
    - partition_index: índice 1-based de la partición a usar.
    - partitions: número de particiones si se usa particionado uniforme.
    - partition_ranges: lista opcional de tuplas (start, end) inclusive, longitud == partitions.
      Si se proporciona, se usa esta lista en vez de dividir uniformemente.
    """
    G = nx.Graph()

    total_qubits = len(properties.get('qubits', []))

    # Determinar el conjunto de nodos a incluir
    if partition_mode:
        if partition_ranges is not None:
            if not isinstance(partition_ranges, (list, tuple)):
                raise ValueError("partition_ranges debe ser lista/tuple de tuplas (start, end)")
            if partition_index < 1 or partition_index > len(partition_ranges):
                raise ValueError("partition_index fuera de rango para partition_ranges")
            start, end_inclusive = partition_ranges[partition_index - 1]
            if start < 0 or end_inclusive >= total_qubits or start > end_inclusive:
                raise ValueError("Rango de partición inválido")
            node_set = set(range(start, end_inclusive + 1))
        else:
            if partitions <= 0:
                raise ValueError("partitions debe ser > 0")
            if partition_index < 1 or partition_index > partitions:
                raise ValueError(f"partition_index debe estar en 1..{partitions}")
            part_size = math.ceil(total_qubits / partitions)
            start = (partition_index - 1) * part_size
            end = min(start + part_size, total_qubits)  # end no inclusivo
            node_set = set(range(start, end))
    else:
        node_set = set(range(total_qubits))

    # Añadir nodos con ruido (solo los de node_set)
    for i, qubit_props in enumerate(properties.get('qubits', [])):
        if i not in node_set:
            continue
        try:
            t1 = qubit_props[0]['value']
            t2 = qubit_props[1]['value']
            readout_error = qubit_props[5]['value']
            noise = (
                ALPHA * readout_error +
                BETA * (1 / t1 if t1 > 0 else float('inf')) +
                GAMMA * (1 / t2 if t2 > 0 else float('inf'))
            )
            G.add_node(i, noise=noise)
        except (IndexError, KeyError, TypeError, ZeroDivisionError):
            G.add_node(i, noise=float('inf'))

    # Añadir aristas solo si ambos extremos están en la partición
    for q1, q2 in coupling_map:
        if q1 in node_set and q2 in node_set:
            G.add_edge(q1, q2)
    
    return G
