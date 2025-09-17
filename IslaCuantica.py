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
    - El layout global de qubits físicos asignados (lista plana de enteros)
    """
    # Paso 1: Obtener grafo y propiedades del backend
    coupling_map, qubit_props, gate_props = get_backend_graph()
    G = build_graph(coupling_map, qubit_props)

    # Paso 2: Ejecutar el algoritmo de asignación
    placements, errores = place_circuits(G, queue.get_queue())

    # Paso 3: Filtrar la cola formateada (solo los circuitos asignados)
    cola_formateada = []
    layout_global = []

    for idx, placement in enumerate(placements):
        if placement is not None:
            # queue.get_queue()[idx] es el dict del circuito (p.e. {'id':..., 'size':...})
            cola_formateada.append(queue.get_queue()[idx])

            # placement[1] se supone que es la lista/tupla de qubits físicos asignados a este circuito
            assigned = placement[1]

            # Normalizar assigned a lista y concatenar (manteniendo orden)
            if isinstance(assigned, (list, tuple)):
                layout_global.extend(list(assigned))
            else:
                layout_global.append(assigned)

    # NO eliminar duplicados — queremos el layout plano y en orden lógico
    # (Si hay duplicados en layout_global eso significa que el algoritmo asignó mal
    # o que hubo solapamiento, y debe detectarse más arriba.)

    return cola_formateada, layout_global






