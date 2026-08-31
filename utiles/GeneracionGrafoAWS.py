import networkx as nx
import matplotlib.pyplot as plt
from braket.aws import AwsDevice
import json

def buscar_clave_recursiva(diccionario, clave_objetivo):
    """Busca una clave en cualquier nivel de profundidad de un diccionario."""
    if isinstance(diccionario, dict):
        if clave_objetivo in diccionario:
            return diccionario[clave_objetivo]
        for valor in diccionario.values():
            resultado = buscar_clave_recursiva(valor, clave_objetivo)
            if resultado is not None:
                return resultado
    elif isinstance(diccionario, list):
        for elemento in diccionario:
            resultado = buscar_clave_recursiva(elemento, clave_objetivo)
            if resultado is not None:
                return resultado
    return None

def generar_grafo_ruido_aws(device_arn="arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1-108Q"):
    print(f"🛰️ Conectando a AWS Braket: {device_arn}")
    device = AwsDevice(device_arn)
    props_dict = device.properties.dict()

    # Búsqueda dinámica independiente de la versión del esquema
    one_q_props = buscar_clave_recursiva(props_dict, 'oneQubitProperties')
    two_q_props = buscar_clave_recursiva(props_dict, 'twoQubitProperties')

    if not one_q_props or not two_q_props:
        print("⚠️ No se encontraron las métricas en la respuesta de AWS.")
        with open("debug_aws_props.json", "w") as f:
            json.dump(props_dict, f, indent=2)
        print("Archivo 'debug_aws_props.json' generado en el directorio para inspección manual.")
        return

    G = nx.Graph()

    # 1. Extraer Conectividad (Edges)
    edges = []
    for edge_key in two_q_props.keys():
        try:
            q1, q2 = map(int, edge_key.split('-'))
            edges.append((q1, q2))
        except ValueError:
            continue
            
    G.add_edges_from(edges)

    # 2. Extraer Métricas de Ruido
    for q_str, data in one_q_props.items():
        q_id = int(q_str)
        if not G.has_node(q_id):
            G.add_node(q_id, error_ro=0.0, error_1q=0.0)
            
        fidelities = data.get('oneQubitFidelity', [])
        f_ro = 1.0
        f_1q = 1.0
        
        for fid_entry in fidelities:
            fid_type = fid_entry.get('fidelityType', {}).get('name', '')
            if fid_type == 'READOUT':
                f_ro = fid_entry.get('fidelity', 1.0)
            elif fid_type == 'RANDOMIZED_BENCHMARKING':
                f_1q = fid_entry.get('fidelity', 1.0)
                
        G.nodes[q_id]['error_ro'] = round((1.0 - f_ro) * 100, 2)
        G.nodes[q_id]['error_1q'] = round((1.0 - f_1q) * 100, 2)

    # 3. Visualización
    plt.figure(figsize=(16, 12))
    pos = nx.spring_layout(G, k=0.15, iterations=50) 
    
    colores = [G.nodes[n].get('error_ro', 0.0) for n in G.nodes()]
    
    nodos = nx.draw_networkx_nodes(G, pos, node_color=colores, cmap=plt.cm.Reds, node_size=600)
    nx.draw_networkx_edges(G, pos, edge_color='gray', alpha=0.6)
    
    etiquetas = {n: f"Q{n}\n{G.nodes[n].get('error_ro', 0.0)}%" for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels=etiquetas, font_size=8, font_color='black', font_weight='bold')
    
    plt.colorbar(nodos, label="Tasa de Error de Lectura (%)")
    plt.title("Topología Rigetti Cepheus-1-108Q: Mapa de Calor de Ruido", fontsize=16)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

    # 4. Volcado de datos críticos
    print("\n📊 Top 10 Qubits con mayor Error de Lectura (Readout Error):")
    nodos_ordenados = sorted(G.nodes(data=True), key=lambda x: x[1].get('error_ro', 0.0), reverse=True)
    for n, data in nodos_ordenados[:10]:
        print(f" -> Qubit {n:^3}: Error Lectura = {data.get('error_ro'):>5}%, Error Puerta 1Q = {data.get('error_1q')}%")

if __name__ == "__main__":
    generar_grafo_ruido_aws()