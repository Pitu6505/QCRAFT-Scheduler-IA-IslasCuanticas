from ibm_api import get_backend_graph
from graph_utils import build_graph
from circuit_queue import CircuitQueue
from placement_algorithm import place_circuits
from utiles.debug import (
    mostrar_grafo,
    mostrar_propiedades,
    mostrar_asignaciones,
    mostrar_correspondencia_logico_fisico,
    calcular_ruido_total
)
from utiles.metrics import estimar_swap_noise, calcular_ruido_swaps_con_logica


def Cola_Formateada(queue: CircuitQueue):
    """
    Recibe una cola de circuitos y devuelve:
    - La cola formateada (circuitos seleccionados para ejecutar)
    - El layout de qubits físicos asignados (lista de números)
    """
    # Paso 1: Obtener grafo y propiedades del backend
    coupling_map, qubit_props, gate_props = get_backend_graph()
    G = build_graph(coupling_map, qubit_props)

    # Paso 2: Ejecutar el algoritmo de asignación
    placements, errores = place_circuits(G, queue.get_queue())

    # Paso 3: Filtrar la cola formateada (solo los circuitos asignados)
    cola_formateada = []
    layout_fisico = []

    for idx, placement in enumerate(placements):
        if placement is not None:
            cola_formateada.append(queue.get_queue()[idx])
            layout_fisico.append(placement[1])  # Solo el qubit físico

    # Opcional: Eliminar duplicados en layout
    layout_fisico = list(set(tuple(q) if isinstance(q, list) else q for q in layout_fisico))

    return cola_formateada, layout_fisico






