import networkx as nx

# Pesos configurables
ALPHA = 0.3  # peso del error de lectura
BETA = 0.35    # peso de 1/T1
GAMMA = 0.35   # peso de 1/T2

def build_graph(coupling_map, properties):
    G = nx.Graph()

    for i, qubit_props in enumerate(properties['qubits']):
        try:
            t1 = qubit_props[0]['value']  # Tiempo de relajación
            t2 = qubit_props[1]['value']  # Tiempo de decoherencia
            readout_error = qubit_props[5]['value']  # Error de lectura

            # Calcular ruido efectivo
            noise = (
                ALPHA * readout_error +
                BETA * (1 / t1 if t1 > 0 else float('inf')) +
                GAMMA * (1 / t2 if t2 > 0 else float('inf'))
            )

            G.add_node(i, noise=noise)

        except (IndexError, KeyError, ZeroDivisionError):
            # En caso de datos corruptos o incompletos
            G.add_node(i, noise=float('inf'))

    # Añadir aristas del coupling map
    for qubit1, qubit2 in coupling_map:
        G.add_edge(qubit1, qubit2)

    # Mostrar información del grafo
    # print(f"\n🔗 Grafo construido con {G.number_of_nodes()} nodos y {G.number_of_edges()} aristas."
    #       f" Ruido promedio: {sum(nx.get_node_attributes(G, 'noise').values()) / G.number_of_nodes():.4f}")
    
    # mostrar el grafo
    # import matplotlib.pyplot as plt
    # pos = nx.spring_layout(G)
    # # Etiqueta: "QubitID\nRuido"
    # node_labels = {node: f"{node}\n{data['noise']:.5f}" for node, data in G.nodes(data=True)}
    # nx.draw(G, pos, labels=node_labels, with_labels=True, node_color='lightblue', edge_color='gray', node_size=500, font_size=10)
    # plt.title("Grafo de Qubits y Conexiones (ID y Ruido como etiqueta)")
    # plt.show()
    # # Mostrar el peso de cada nodo
    # print("\n📊 Ruido de cada qubit:")
    # for node, data in G.nodes(data=True):
    #     print(f"Qubit {node}: Ruido={data['noise']:.4f}")
    

    return G
