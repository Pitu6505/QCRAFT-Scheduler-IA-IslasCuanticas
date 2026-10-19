"""Compara niveles de colocación y estima SWAPs para un circuito Qiskit de GitHub."""

import argparse
import ast
import csv
import json
import sys
from itertools import combinations
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import networkx as nx

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from graph_utils import build_graph
from placement_algorithm_logical import place_circuits_logical
import config


LEVEL_SCENARIOS = (
    ("Nivel 3", {3}),
    ("Niveles 2 + 3", {2, 3}),
    ("Niveles 1 + 2 + 3", {1, 2, 3}),
)
DEFAULT_URLS_FILE = Path(__file__).with_name("scheduler-async_IslasEdges_Short.py")
CSV_FIELDS = (
    "circuit",
    "url",
    "qubits",
    "logical_pairs",
    "scenario",
    "iteration",
    "level_used",
    "strategy_used",
    "physical_qubits",
    "estimated_swaps",
    "status",
)


def load_url_entries(path):
    """Carga URLs de un JSON o del diccionario urls de un script Python, sin ejecutarlo."""
    source_path = Path(path)
    source = source_path.read_text(encoding="utf-8")
    if source_path.suffix.lower() == ".json":
        entries = json.loads(source)
    else:
        tree = ast.parse(source, filename=str(source_path))
        entries = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "urls"
                for target in node.targets
            ):
                entries = ast.literal_eval(node.value)
                break
        if entries is None:
            raise ValueError(f"No se encontró el diccionario 'urls' en {source_path}.")

    if not isinstance(entries, dict) or not entries:
        raise ValueError("El fichero debe contener un diccionario no vacío de nombre: URL.")
    if any(not isinstance(name, str) or not isinstance(url, str) for name, url in entries.items()):
        raise ValueError("Todas las entradas deben tener un nombre y una URL de texto.")
    return list(entries.items())


def load_github_source(url):
    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or parsed_url.netloc != "raw.githubusercontent.com":
        raise ValueError("La URL debe ser un archivo HTTPS de raw.githubusercontent.com.")

    request = Request(url, headers={"User-Agent": "QCRAFT-placement-analysis"})
    with urlopen(request, timeout=20) as response:
        source = response.read(5_000_001)
    if len(source) > 5_000_000:
        raise ValueError("El archivo remoto supera el límite de 5 MB.")
    return source.decode("utf-8")


def _register_sizes(tree):
    sizes = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        call = node.value
        if (
            isinstance(target, ast.Name)
            and isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "QuantumRegister"
            and call.args
            and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, int)
        ):
            sizes[target.id] = call.args[0].value
    if not sizes:
        raise ValueError("No se encontró una declaración estática QuantumRegister(n, ...).")
    if len(sizes) != 1:
        raise ValueError("El análisis requiere un único QuantumRegister, como el parser del scheduler.")
    return sizes


def _circuit_variables(tree):
    circuit_variables = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        call = node.value
        if (
            isinstance(node.targets[0], ast.Name)
            and isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "QuantumCircuit"
        ):
            circuit_variables.add(node.targets[0].id)
    if not circuit_variables:
        raise ValueError("No se encontró una asignación a QuantumCircuit.")
    return circuit_variables


def _qubit_index(node, register_names):
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id in register_names
    ):
        index = node.slice
        if isinstance(index, ast.Constant) and isinstance(index.value, int):
            return index.value
    return None


def extract_circuit(source):
    """Extrae registros, número de qubits y pares lógicos sin ejecutar código remoto."""
    tree = ast.parse(source)
    register_sizes = _register_sizes(tree)
    circuit_variables = _circuit_variables(tree)
    edges = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if (
            not isinstance(node.func.value, ast.Name)
            or node.func.value.id not in circuit_variables
        ):
            continue
        qubits = []
        for argument in node.args:
            for candidate in ast.walk(argument):
                index = _qubit_index(candidate, register_sizes)
                if index is not None:
                    qubits.append(index)
        if len(qubits) >= 2:
            edges.update(tuple(sorted(pair)) for pair in combinations(qubits, 2))

    return sum(register_sizes.values()), sorted(edges)


def estimate_swaps(graph, placement, logical_edges):
    """Suma distancia-1 por pareja lógica única; no sustituye al routing del transpiler."""
    logical_to_physical = {logical: physical for logical, physical in enumerate(placement)}
    estimated_swaps = 0
    unreachable_edges = []

    for logical_a, logical_b in logical_edges:
        physical_a = logical_to_physical[logical_a]
        physical_b = logical_to_physical[logical_b]
        try:
            distance = nx.shortest_path_length(graph, physical_a, physical_b)
        except nx.NetworkXNoPath:
            unreachable_edges.append((logical_a, logical_b))
            continue
        estimated_swaps += max(0, distance - 1)

    return estimated_swaps, unreachable_edges


def placement_strategy_name(level):
    return {
        1: "VF2: isomorfismo exacto",
        2: "Componentes conexas",
        3: "Búsqueda normal",
    }[level]


def get_backend_graph_for_provider(provider, backend_name):
    if provider == "aws":
        from aws_api import get_backend_graph_aws

        coupling_map, qubit_props, _ = get_backend_graph_aws()
    else:
        from ibm_api import get_backend_graph

        coupling_map, qubit_props, _ = get_backend_graph(backend_name)
    if coupling_map is None or qubit_props is None:
        raise RuntimeError(f"No se pudieron obtener los datos de topología para {provider}.")

    return build_graph(
        coupling_map,
        qubit_props,
        partition_mode=config.USE_PARTITION,
        partition_index=config.PARTITION_INDEX,
        partitions=config.PARTITIONS,
        partition_ranges=config.PARTITION_RANGES,
    )


def analyze_circuits(circuits, graph, scenarios):
    rows = []
    for label, enabled_levels in scenarios:
        pending = list(circuits)
        iteration = 1
        while pending:
            selected_levels = {}
            placements, errors = place_circuits_logical(
                graph,
                [
                    {"id": circuit["id"], "size": circuit["qubits"], "edges": circuit["edges"]}
                    for circuit in pending
                ],
                enabled_levels=enabled_levels,
                placement_levels=selected_levels,
                verbose=False,
                min_circuit_distance=0,
            )
            placement_by_id = dict(placements)
            error_by_id = {}
            for error in errors:
                for circuit in pending:
                    if error.startswith(f"Circuito {circuit['id']} "):
                        error_by_id[circuit["id"]] = error
                        break

            placed_ids = set(placement_by_id)
            for circuit in pending:
                physical_qubits = placement_by_id.get(circuit["id"])
                if physical_qubits is None:
                    continue

                swaps, unreachable_edges = estimate_swaps(graph, physical_qubits, circuit["edges"])
                if unreachable_edges:
                    status = f"Interacciones sin ruta: {unreachable_edges}"
                    estimated_swaps = ""
                else:
                    status = "OK"
                    estimated_swaps = swaps
                level_used = selected_levels[circuit["id"]]
                rows.append({
                    "circuit": circuit["name"],
                    "url": circuit["url"],
                    "qubits": circuit["qubits"],
                    "logical_pairs": len(circuit["edges"]),
                    "scenario": label,
                    "iteration": iteration,
                    "level_used": level_used,
                    "strategy_used": placement_strategy_name(level_used),
                    "physical_qubits": " ".join(map(str, physical_qubits)),
                    "estimated_swaps": estimated_swaps,
                    "status": status,
                })

            pending = [circuit for circuit in pending if circuit["id"] not in placed_ids]
            if not pending:
                break

            if not placed_ids:
                for circuit in pending:
                    rows.append({
                        "circuit": circuit["name"],
                        "url": circuit["url"],
                        "qubits": circuit["qubits"],
                        "logical_pairs": len(circuit["edges"]),
                        "scenario": label,
                        "iteration": iteration,
                        "level_used": "",
                        "strategy_used": "",
                        "physical_qubits": "",
                        "estimated_swaps": "",
                        "status": error_by_id.get(
                            circuit["id"],
                            "No se pudo colocar ni siquiera en una iteración vacía.",
                        ),
                    })
                break

            iteration += 1

    return rows


def selected_level_scenarios(levels):
    if levels is None:
        return LEVEL_SCENARIOS
    enabled_levels = set(levels)
    if not enabled_levels:
        raise ValueError("Selecciona al menos un nivel.")
    label = "Solo nivel " + str(next(iter(enabled_levels))) if len(enabled_levels) == 1 else (
        "Niveles " + "+".join(map(str, sorted(enabled_levels)))
    )
    return ((label, enabled_levels),)


def summarize_swaps(rows, scenarios):
    summaries = []
    for label in (scenario[0] for scenario in scenarios):
        scenario_rows = [row for row in rows if row["scenario"] == label]
        estimates = [
            row["estimated_swaps"]
            for row in scenario_rows
            if isinstance(row["estimated_swaps"], int)
        ]
        summaries.append({
            "scenario": label,
            "total_estimated_swaps": sum(estimates),
            "estimated_circuits": len(estimates),
            "total_circuits": len(scenario_rows),
        })
    return summaries


def main():
    parser = argparse.ArgumentParser(
        description="Analiza circuitos GitHub sobre la topología de una QPU y escenarios de colocación."
    )
    parser.add_argument(
        "--urls-file",
        default=str(DEFAULT_URLS_FILE),
        help=(
            "Script Python con un diccionario urls o fichero JSON nombre: URL "
            f"(por defecto: {DEFAULT_URLS_FILE.name})"
        ),
    )
    parser.add_argument(
        "--provider",
        choices=("ibm", "aws"),
        default="ibm",
        help="Backend cuya topología se usará (por defecto: ibm)",
    )
    parser.add_argument(
        "--backend",
        default="ibm_fez",
        help="Nombre de QPU IBM (por defecto: ibm_fez; no aplica a AWS)",
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        type=int,
        choices=(1, 2, 3),
        help="Niveles que se activan, por ejemplo --levels 3; por defecto compara 3, 2+3 y 1+2+3",
    )
    parser.add_argument(
        "--output",
        default="resultados_niveles_colocacion.csv",
        help="CSV de salida (por defecto: resultados_niveles_colocacion.csv)",
    )
    args = parser.parse_args()

    try:
        scenarios = selected_level_scenarios(args.levels)
        url_entries = load_url_entries(args.urls_file)
        graph = get_backend_graph_for_provider(args.provider, args.backend)
    except (OSError, SyntaxError, ValueError, RuntimeError) as error:
        parser.error(str(error))

    print(f"Circuitos a analizar: {len(url_entries)}")
    qpu_name = args.backend if args.provider == "ibm" else "Rigetti Ankaa-3"
    print(f"QPU: {qpu_name}; proveedor: {args.provider}")
    print(f"Grafo de conectividad cargado: {graph.number_of_nodes()} qubits físicos")
    print("Estrategias: nivel 1 = VF2, nivel 2 = componentes conexas, nivel 3 = búsqueda normal")
    print("Escenarios comparados: " + "; ".join(label for label, _ in scenarios))
    print("Separación extra entre circuitos: ninguna; se crean iteraciones al llenar la QPU.")
    print("SWAP = estimación por distancia mínima, no recuento exacto del transpiler.\n")

    circuits = []
    for index, (name, url) in enumerate(url_entries, start=1):
        print(f"Descargando [{index}/{len(url_entries)}] {name}")
        try:
            num_qubits, edges = extract_circuit(load_github_source(url))
            circuits.append({
                "id": f"circuit_{index}",
                "name": name,
                "url": url,
                "qubits": num_qubits,
                "edges": edges,
            })
        except (HTTPError, URLError, UnicodeDecodeError, SyntaxError, ValueError) as error:
            circuits.append({
                "id": f"circuit_{index}",
                "circuit": name,
                "name": name,
                "url": url,
                "load_error": f"Error al leer circuito: {error}",
            })
            print(f"  Error: {error}")

    valid_circuits = [circuit for circuit in circuits if "load_error" not in circuit]
    results = []
    for circuit in circuits:
        if "load_error" in circuit:
            for label, _ in scenarios:
                results.append({
                    "circuit": circuit["name"],
                    "url": circuit["url"],
                    "qubits": "",
                    "logical_pairs": "",
                    "scenario": label,
                    "iteration": "",
                    "level_used": "",
                    "strategy_used": "",
                    "physical_qubits": "",
                    "estimated_swaps": "",
                    "status": circuit["load_error"],
                })

    if valid_circuits:
        results.extend(analyze_circuits(valid_circuits, graph, scenarios))

    result_by_circuit_scenario = {
        (row["circuit"], row["scenario"]): row for row in results
    }
    for name in (name for name, _ in url_entries):
        print(f"\n{name}")
        for label in (label for label, _ in scenarios):
            row = result_by_circuit_scenario[(name, label)]
            print(
                f"  {label}, iteración {row['iteration'] or '-'}: "
                f"{row['strategy_used'] or 'sin colocación'}; "
                f"SWAP estimados {row['estimated_swaps'] or '-'}; {row['status']}"
            )

    summaries = summarize_swaps(results, scenarios)
    print("\n========== TOTAL SWAP ESTIMADOS ==========")
    for summary in summaries:
        omitted = summary["total_circuits"] - summary["estimated_circuits"]
        coverage = (
            f"estimación disponible para {summary['estimated_circuits']}/"
            f"{summary['total_circuits']} circuitos"
        )
        if omitted:
            coverage += f"; {omitted} sin estimación"
        print(
            f"{summary['scenario']}: "
            f"{summary['total_estimated_swaps']} SWAP estimados ({coverage})"
        )
        results.append({
            "circuit": "TOTAL ESCENARIO",
            "url": "",
            "qubits": "",
            "logical_pairs": "",
            "scenario": summary["scenario"],
            "iteration": "",
            "level_used": "",
            "strategy_used": "",
            "physical_qubits": "",
            "estimated_swaps": summary["total_estimated_swaps"],
            "status": coverage,
        })

    output_path = Path(args.output)
    with output_path.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(results)
    print(f"\nResultados guardados en: {output_path.resolve()}")


if __name__ == "__main__":
    main()
