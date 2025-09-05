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
            # Suponiendo que placement es un dict {logical_qubit: physical_qubit}
            layout_fisico.extend(list(placement.values()))

    # Opcional: Eliminar duplicados en layout
    layout_fisico = list(set(layout_fisico))

    return cola_formateada, layout_fisico
    



# ✅ Paso 1: Obtener grafo desde IBM
coupling_map, qubit_props, gate_props = get_backend_graph()
#mostrar_grafo(coupling_map)
#mostrar_propiedades(qubit_props)

G = build_graph(coupling_map, qubit_props)

# Paso 2: Crear y llenar la cola de circuitos
queue = CircuitQueue()


# Paso 3: Ejecutar el algoritmo de asignación
placements, errores = place_circuits(G, queue.get_queue())

# Paso 4: Mostrar resultados
mostrar_asignaciones(placements, len(queue.get_queue()))
mostrar_correspondencia_logico_fisico(placements)


ruido_total = calcular_ruido_total(G, placements)
print(f"\n🔊 Ruido total acumulado de qubits usados: {ruido_total:.5f}")


ruido_puertas = calcular_ruido_swaps_con_logica(G, placements, queue.get_queue(), gate_props)
print(f"\n🔊 Ruido estimado por SWAPs: {ruido_puertas:.5f}")

ruido_total += ruido_puertas
print(f"\n🔊 Ruido total acumulado (qubits + SWAPs): {ruido_total:.5f}")

if errores:
    print("\n🚫 Circuitos no asignados y motivos:")
    for err in errores:
        print(err)




