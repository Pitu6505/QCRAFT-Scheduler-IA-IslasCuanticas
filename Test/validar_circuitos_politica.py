"""Valida circuitos de prueba sin enviarlos a IBM/AWS ni ejecutarlos.

Ejemplo:
    python Test/validar_circuitos_politica.py --policy Islas_Cuanticas_Edges \
        --sentinel-mode dynamic_local_initial_ramsey --limit 1
"""

import argparse
import ast
import csv
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from qiskit import QuantumCircuit


POLICIES = {

    "Islas_Cuanticas_Edges",
}
GRAPH_POLICIES = {"Islas_Cuanticas", "Islas_Cuanticas_Edges"}
DEFAULT_SOURCE = Path(__file__).with_name("PruebasCentinelas4.py")
MAX_QUBITS = 156


def load_urls(source: Path):
    """Lee únicamente el literal `urls` sin importar el script de pruebas."""
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "urls"
            for target in node.targets
        ):
            values = ast.literal_eval(node.value)
            if not isinstance(values, dict):
                raise ValueError("La variable urls no contiene un diccionario")
            return values
    raise ValueError(f"No se encontró la variable urls en {source}")


def download(url: str) -> str:
    request = Request(url, headers={"User-Agent": "QCRAFT-dry-run-validator"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def build_circuit(code: str) -> QuantumCircuit:
    """Construye el QuantumCircuit local; nunca transpila ni lo envía a un backend."""
    if "OPENQASM 3.0" in code:
        from qiskit import qasm3

        return qasm3.loads(code)

    compile(code.replace("return circuit", ""), "<remote-circuit>", "exec")
    local_vars = {}
    exec(code.replace("return circuit", ""), {}, local_vars)
    circuit = local_vars.get("circuit")
    if not isinstance(circuit, QuantumCircuit):
        raise ValueError("El código no produjo una variable QuantumCircuit llamada 'circuit'")
    return circuit


def logical_edges(circuit: QuantumCircuit):
    edges = set()
    qubit_indexes = {qubit: index for index, qubit in enumerate(circuit.qubits)}
    for instruction in circuit.data:
        indexes = [qubit_indexes[qubit] for qubit in instruction.qubits]
        for left_index, left in enumerate(indexes):
            for right in indexes[left_index + 1:]:
                edges.add(tuple(sorted((left, right))))
    return sorted(edges)


def validate(name, url, policy, sentinel_mode, provider, shots):
    result = {
        "circuit": name,
        "url": url,
        "policy": policy,
        "sentinel_mode": sentinel_mode or "none",
        "provider": provider,
        "status": "ERROR",
        "error": "",
        "qubits": "",
        "depth": "",
        "gates": "",
        "edges": "",
    }
    try:
        code = download(url)
        circuit = build_circuit(code)
        edges = logical_edges(circuit)

        if circuit.num_qubits > MAX_QUBITS:
            raise ValueError(f"requiere {circuit.num_qubits} qubits; máximo {MAX_QUBITS}")
        if not isinstance(shots, int) or not 0 < shots <= 20000:
            raise ValueError("shots debe estar entre 1 y 20000")
        if policy not in POLICIES:
            raise ValueError(f"política desconocida: {policy}")
        if provider not in {"ibm", "aws"}:
            raise ValueError(f"proveedor desconocido: {provider}")
        if sentinel_mode and policy not in GRAPH_POLICIES:
            raise ValueError("sentinel-mode solo se aplica a las políticas de islas cuánticas")

        result.update(
            status="OK",
            qubits=circuit.num_qubits,
            depth=circuit.depth(),
            gates=sum(circuit.count_ops().values()),
            edges=len(edges),
        )
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="Islas_Cuanticas_Edges")
    parser.add_argument("--sentinel-mode", default=None)
    parser.add_argument("--provider", choices=("ibm", "aws"), default="ibm")
    parser.add_argument("--shots", type=int, default=10000)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--limit", type=int, default=0, help="0 procesa todos los circuitos")
    parser.add_argument("--output", type=Path, default=Path("validacion_circuitos.csv"))
    args = parser.parse_args()

    urls = list(load_urls(args.source).items())
    if args.limit > 0:
        urls = urls[:args.limit]

    results = [
        validate(name, url, args.policy, args.sentinel_mode, args.provider, args.shots)
        for name, url in urls
    ]
    fieldnames = list(results[0]) if results else ["circuit", "status", "error"]
    with args.output.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    for result in results:
        details = result["error"] or (
            f"qubits={result['qubits']} depth={result['depth']} "
            f"gates={result['gates']} edges={result['edges']}"
        )
        print(f"[{result['status']}] {result['circuit']}: {details}")
    valid = sum(result["status"] == "OK" for result in results)
    print(f"\nResumen: {valid}/{len(results)} OK; CSV: {args.output}")
    return 0 if valid == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())