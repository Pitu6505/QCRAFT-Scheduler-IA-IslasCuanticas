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
    - La cola formateada (solo los circuitos que realmente han sido asignados)
    - El layout global de qubits físicos asignados (lista plana de enteros)
    """

    # Paso 1: Obtener grafo y propiedades del backend
    coupling_map, qubit_props, gate_props = get_backend_graph()
    G = build_graph(coupling_map, qubit_props)

    # Debug inicial
    print("\n🔎 [DEBUG] Cola original recibida:")
    for c in queue.get_queue():
        print(f"  - id={c['id']}, size={c['size']}")

    # Paso 2: Ejecutar el algoritmo de asignación
    placements, errores = place_circuits(G, queue.get_queue())

    print("\n🔎 [DEBUG] Resultado de placements:")
    for p in placements:
        if p is not None:
            print(f"  - id={p[0]}, qubits físicos={p[1]}")
        else:
            print("  - None (circuito no asignado)")

    # Paso 3: Construir diccionario de la cola
    queue_dict = {c['id']: c for c in queue.get_queue()}

    # Paso 4: Filtrar cola y construir layout global
    cola_formateada = []
    layout_global = []

    for placement in placements:
        if placement is None:
            continue

        circ_id, assigned = placement
        if circ_id in queue_dict:
            circuito = queue_dict[circ_id]
            cola_formateada.append(circuito)

            # Normalizar "assigned" a lista
            if isinstance(assigned, (list, tuple)):
                layout_global.extend(list(assigned))
            else:
                layout_global.append(assigned)

            print(f"✅ [DEBUG] Circuito {circ_id} (size={circuito['size']}) "
                  f"asignado a qubits físicos {assigned}")
        else:
            print(f"⚠️ [WARNING] Placement con id {circ_id} no estaba en la cola original")

    # Paso 5: Validar correlación entre layout y tamaños de circuitos
    total_qubits_needed = sum(int(c['size']) for c in cola_formateada)
    total_qubits_assigned = len(layout_global)

    print("\n🔎 [DEBUG] Cola formateada final:")
    for c in cola_formateada:
        print(f"  - id={c['id']}, size={c['size']}")

    print(f"\n🔎 [DEBUG] Layout global construido: {layout_global}")

    if total_qubits_assigned == total_qubits_needed:
        print(f"✅ [VALIDACIÓN] Layout válido: {total_qubits_assigned} qubits asignados "
              f"para {total_qubits_needed} qubits lógicos.")
    else:
        print(f"❌ [ERROR] Layout inconsistente: {total_qubits_assigned} qubits físicos asignados "
              f"vs {total_qubits_needed} qubits lógicos requeridos.")
        print("   → Revisa el algoritmo de asignación o la filtración de la cola.")

    return cola_formateada, layout_global
