import networkx as nx
from braket.aws import AwsDevice

class SimulatedGate:
    def __init__(self, gate_name, qubits, error_value):
        self.gate = gate_name
        self.qubits = qubits
        self.parameters = [
             {'name': 'gate_error', 'value': error_value}
        ]

def buscar_clave_recursiva(diccionario, clave_objetivo):
    """Busca una clave en cualquier nivel de profundidad del diccionario de AWS."""
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

def get_backend_graph_aws(device_arn: str = "arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1-108Q"):
    """
    Obtiene los datos de calibración de AWS Braket y los formatea
    de forma segura para que sean compatibles con el grafo del middleware.
    """
    print(f"🛰️ Conectando a AWS Braket para obtener datos de {device_arn}...")
    
    try:
        device = AwsDevice(device_arn)
        properties_aws = device.properties
        props_dict = properties_aws.dict()
    except Exception as e:
        print(f"Error al conectar con AWS Braket: {e}")
        return None, None, None

    # Búsqueda dinámica para evitar fallos si AWS cambia el esquema
    aws_qubit_props = buscar_clave_recursiva(props_dict, 'oneQubitProperties') or {}
    aws_gate_props = buscar_clave_recursiva(props_dict, 'twoQubitProperties') or {}
    
    g_temp = nx.Graph(properties_aws.paradigm.connectivity.connectivityGraph)
    
    coupling_map = [[int(q1), int(q2)] for q1, q2 in g_temp.edges()]
    
    qubit_ids_from_graph = set(q for edge in coupling_map for q in edge) if coupling_map else set()
    qubit_ids_from_props = set(int(q_id) for q_id in aws_qubit_props.keys()) if aws_qubit_props else set()
    
    all_qubit_ids = qubit_ids_from_graph | qubit_ids_from_props
    max_qubit_id = max(all_qubit_ids) if all_qubit_ids else 0
    list_size = max_qubit_id + 1
    
    print(f" Qubits detectados: {len(all_qubit_ids)} (IDs del 0 al {max_qubit_id})")
    
    dummy_q_props = [
        {'value': 0.0},
        {'value': 0.0},
        None, None, None,
        {'value': 1.0}
    ]
    
    formatted_qubit_list = [dummy_q_props.copy() for _ in range(list_size)]
    
    for q_id_str, props in aws_qubit_props.items():
        try:
            q_id = int(q_id_str)
        except ValueError:
            continue
            
        ibm_style_list = [None] * 6 

        t1_s = props.get('T1', {}).get('value', 1e-9)
        ibm_style_list[0] = {'value': t1_s * 1e6}

        t2_s = props.get('T2', {}).get('value', 1e-9)
        ibm_style_list[1] = {'value': t2_s * 1e6}
        
        readout_fidelity = None
        for item in props.get('oneQubitFidelity', []):
            if item.get('fidelityType', {}).get('name') == 'READOUT':
                readout_fidelity = item.get('fidelity', 1.0)
                break
        
        readout_error = 1.0 - readout_fidelity if readout_fidelity is not None else 1.0
        ibm_style_list[5] = {'value': readout_error}
        
        formatted_qubit_list[q_id] = ibm_style_list

    properties = {'qubits': formatted_qubit_list}
    gate_props_list = [] 
    
    for pair_str, props in aws_gate_props.items():
        try:
            q_pair = tuple(map(int, pair_str.strip("()").split("-")))
        except ValueError:
            try:
                # Soporte por si AWS Braket devuelve el formato antiguo (q1, q2)
                q_pair = tuple(map(int, pair_str.strip("()").split(",")))
            except ValueError:
                continue

        cx_fidelity = None
        gate_name_from_aws = None
        for item in props.get('twoQubitGateFidelity', []) or props.get('twoQubitFidelity', []):
            if item.get('fidelityType', {}).get('name') in ['INTERLEAVED_RANDOMIZED_BENCHMARKING', 'CZ', 'CX']:
                cx_fidelity = item.get('fidelity', 1.0)
                gate_name_from_aws = 'cx'
                break
        
        if gate_name_from_aws:
            cx_error = 1.0 - cx_fidelity if cx_fidelity is not None else 1.0
            sim_gate = SimulatedGate(
                gate_name=gate_name_from_aws,
                qubits=list(q_pair),
                error_value=cx_error
            )
            gate_props_list.append(sim_gate)

    print("✅ Datos de AWS Braket obtenidos y formateados.")
    return coupling_map, properties, gate_props_list