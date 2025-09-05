def estimar_swap_noise(G, placements, gate_props):
    # Diccionario de errores para puertas CX entre pares de qubits
    swap_errors = {
        tuple(sorted(gate.qubits)): gate.parameters[0].value
        for gate in gate_props
        if gate.gate == 'cx'
    }

    total_noise = 0
    for _, qubits in placements:
        # Comprobamos cada par distinto en el circuito
        for i in range(len(qubits)):
            for j in range(i + 1, len(qubits)):
                pair = tuple(sorted((qubits[i], qubits[j])))
                # Solo sumamos ruido si no hay conexión directa
                if not G.has_edge(*pair):
                    # Obtenemos el error de swap si existe, sino ponemos un valor por defecto
                    error_swap = swap_errors.get(pair, 0.02)
                    total_noise += error_swap

    return total_noise

def calcular_ruido_swaps_con_logica(G, placements, queue, gate_props):
    """
    G: grafo físico
    placements: lista (circuit_id, [qubits_físicos])
    queue: lista de circuitos con info lógica (id, edges)
    gate_props: propiedades de las puertas (para obtener error cx)
    """
    # Diccionario de errores de CX
    swap_errors = {
        tuple(sorted(gate.qubits)): gate.parameters[0].value
        for gate in gate_props
        if gate.gate == 'cx'
    }

    # Mapear circuitos para fácil acceso por id
    queue_dict = {c['id']: c for c in queue}

    total_noise = 0
    total_swaps = 0

    for circuit_id, qubits_fisicos in placements:
        circuit_logico = queue_dict[circuit_id]
        edges_logicos = circuit_logico.get('edges', [])

        # Mapeo lógico → físico
        mapping_logico_a_fisico = {i: q for i, q in enumerate(qubits_fisicos)}

        # Verificar cada conexión lógica si está físicamente conectada
        for (u, v) in edges_logicos:
            q_u = mapping_logico_a_fisico[u]
            q_v = mapping_logico_a_fisico[v]
            pair = tuple(sorted((q_u, q_v)))

            if not G.has_edge(*pair):
                error_swap = swap_errors.get(pair, 0.02)
                total_noise += error_swap
                total_swaps += 1
                print(f"Swap necesario en circuito {circuit_id} entre qubits físicos {pair} con error {error_swap:.5f}")

    print(f"\nTotal swaps contados (basado en estructura lógica): {total_swaps}")
    return total_noise

