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

# ✅ Paso 1: Obtener grafo desde IBM
coupling_map, qubit_props, gate_props = get_backend_graph()
#mostrar_grafo(coupling_map)
#mostrar_propiedades(qubit_props)

G = build_graph(coupling_map, qubit_props)

# Paso 2: Crear y llenar la cola de circuitos
queue = CircuitQueue()
queue.add_circuit("circuito_estrella", 3, edges=[(0, 1), (0, 2)])
queue.add_circuit("circuito_triangulo", 3, edges=[(0, 1), (0, 2), (1, 2)])
queue.add_circuit("circuito_lineal", 3, edges=[(0, 1), (1, 2)])
queue.add_circuit("circuito_cuadrado", 4, edges=[(0, 1), (0, 2), (0, 3)])
queue.add_circuit("circuito_simple", 2)

queue.add_circuit("circuito_estrella_3", 3, edges=[(0, 1), (0, 2)])
queue.add_circuit("circuito_triangulo_3", 3, edges=[(0, 1), (0, 2), (1, 2)])
queue.add_circuit("circuito_lineal_3", 3, edges=[(0, 1), (1, 2)])
queue.add_circuit("circuito_cuadrado_4", 4, edges=[(0, 1), (0, 2), (0, 3)])
queue.add_circuit("circuito_simple_2", 2)

queue.add_circuit("circuito_lineal_5", 5, edges=[(0, 1), (1, 2), (2, 3), (3, 4)])
queue.add_circuit("circuito_estrella_5", 5, edges=[(0, 1), (0, 2), (0, 3), (0, 4)])
queue.add_circuit("circuito_anillo_6", 6, edges=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)])
queue.add_circuit("circuito_arbol_7", 7, edges=[(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)])
queue.add_circuit("circuito_completo_4", 4, edges=[(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])

queue.add_circuit("circuito_ladder_6", 6, edges=[(0, 1), (2, 3), (4, 5), (0, 2), (2, 4), (1, 3), (3, 5)])
queue.add_circuit("circuito_malha_9", 9, edges=[
    (0, 1), (1, 2), (0, 3), (1, 4), (2, 5),
    (3, 4), (4, 5), (3, 6), (4, 7), (5, 8),
    (6, 7), (7, 8)
])
queue.add_circuit("circuito_estrella_6", 6, edges=[(0, 1), (0, 2), (0, 3), (0, 4), (0, 5)])
queue.add_circuit("circuito_binario_7", 7, edges=[(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)])
queue.add_circuit("circuito_doble_triangulo_6", 6, edges=[(0, 1), (0, 2), (1, 2), (3, 4), (3, 5), (4, 5)])

queue.add_circuit("circuito_lineal_12", 12, edges=[(i, i + 1) for i in range(11)])
queue.add_circuit("circuito_anillo_10", 10, edges=[(i, (i + 1) % 10) for i in range(10)])
queue.add_circuit("circuito_estrella_8", 8, edges=[(0, i) for i in range(1, 8)])
queue.add_circuit("circuito_completo_5", 5, edges=[(i, j) for i in range(5) for j in range(i + 1, 5)])
queue.add_circuit("circuito_random_9", 9, edges=[(0, 1), (0, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8), (1, 5)])

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
