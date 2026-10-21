"""Analiza los circuitos activos de un diccionario ``urls`` sin ejecutar sus scripts."""

from __future__ import annotations

import argparse
import ast
import csv
import math
import operator
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import MCMT, XGate, YGate, ZGate


REFERENCE_SCRIPT = Path(__file__).with_name("scheduler-async_IslasEdges_Short.py")
CSV_OUTPUT = Path("analisis_circuitos.csv")
ALLOWED_HOST = "raw.githubusercontent.com"
ALLOWED_PATH_PREFIX = "/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code/"
GATE_METHODS = {
    "barrier",
    "ccx",
    "ch",
    "cp",
    "crx",
    "cry",
    "crz",
    "cswap",
    "cu",
    "cu1",
    "cu3",
    "cx",
    "cy",
    "cz",
    "h",
    "id",
    "initialize",
    "measure",
    "measure_all",
    "measure_active",
    "mcx",
    "mcp",
    "mcrx",
    "mcry",
    "mcrz",
    "mcswap",
    "mct",
    "mcu",
    "mcy",
    "mcz",
    "p",
    "reset",
    "rx",
    "rxx",
    "ry",
    "ryy",
    "rz",
    "rzx",
    "rzz",
    "s",
    "sdg",
    "swap",
    "t",
    "tdg",
    "toffoli",
    "u",
    "u1",
    "u2",
    "u3",
    "unitary",
    "x",
    "y",
    "z",
    "append",
}
CONSTRUCTORS = {
    "ClassicalRegister": ClassicalRegister,
    "MCMT": MCMT,
    "QuantumCircuit": QuantumCircuit,
    "QuantumRegister": QuantumRegister,
    "XGate": XGate,
    "YGate": YGate,
    "ZGate": ZGate,
    "abs": abs,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "range": range,
    "tuple": tuple,
    "zip": zip,
}
BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
COMPARISON_OPERATORS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda left, right: left in right,
    ast.NotIn: lambda left, right: left not in right,
}


class UnsupportedCircuitError(ValueError):
    """El código del circuito usa una construcción fuera del subconjunto seguro."""


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _safe_eval(node: ast.expr, environment: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in environment:
            raise UnsupportedCircuitError(f"variable no soportada: {node.id}")
        return environment[node.id]
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = [_safe_eval(element, environment) for element in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(values)
        if isinstance(node, ast.Set):
            return set(values)
        return values
    if isinstance(node, ast.Dict):
        return {
            _safe_eval(key, environment): _safe_eval(value, environment)
            for key, value in zip(node.keys, node.values)
            if key is not None
        }
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPERATORS:
        return BINARY_OPERATORS[type(node.op)](
            _safe_eval(node.left, environment), _safe_eval(node.right, environment)
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPERATORS:
        return UNARY_OPERATORS[type(node.op)](_safe_eval(node.operand, environment))
    if isinstance(node, ast.Subscript):
        value = _safe_eval(node.value, environment)
        index = _safe_eval(node.slice, environment)
        return value[index]
    if isinstance(node, ast.Slice):
        return slice(
            _safe_eval(node.lower, environment) if node.lower else None,
            _safe_eval(node.upper, environment) if node.upper else None,
            _safe_eval(node.step, environment) if node.step else None,
        )
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id in {"math", "np", "numpy"}:
            if node.attr == "pi":
                return math.pi
        raise UnsupportedCircuitError("atributo no soportado")
    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, environment)
        for comparison, comparator in zip(node.ops, node.comparators):
            if type(comparison) not in COMPARISON_OPERATORS:
                raise UnsupportedCircuitError("comparación no soportada")
            right = _safe_eval(comparator, environment)
            if not COMPARISON_OPERATORS[type(comparison)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        values = [_safe_eval(value, environment) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
    if isinstance(node, ast.ListComp):
        return _evaluate_list_comprehension(node, environment)
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in CONSTRUCTORS:
            function = CONSTRUCTORS[node.func.id]
        elif (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in environment
            and isinstance(environment[node.func.value.id], QuantumCircuit)
            and node.func.attr in GATE_METHODS
        ):
            function = getattr(environment[node.func.value.id], node.func.attr)
        else:
            raise UnsupportedCircuitError("llamada no soportada en el circuito")
        args = [_safe_eval(argument, environment) for argument in node.args]
        kwargs = {
            keyword.arg: _safe_eval(keyword.value, environment)
            for keyword in node.keywords
            if keyword.arg is not None
        }
        return function(*args, **kwargs)
    raise UnsupportedCircuitError(f"expresión no soportada: {type(node).__name__}")


def _evaluate_list_comprehension(
    node: ast.ListComp, environment: dict[str, Any]
) -> list[Any]:
    results: list[Any] = []

    def visit(generator_index: int, local_environment: dict[str, Any]) -> None:
        if generator_index == len(node.generators):
            results.append(_safe_eval(node.elt, local_environment))
            return
        generator = node.generators[generator_index]
        if not isinstance(generator.target, ast.Name):
            raise UnsupportedCircuitError("objetivo de comprensión no soportado")
        for value in _safe_eval(generator.iter, local_environment):
            nested_environment = local_environment.copy()
            nested_environment[generator.target.id] = value
            if all(_safe_eval(condition, nested_environment) for condition in generator.ifs):
                visit(generator_index + 1, nested_environment)

    visit(0, environment.copy())
    return results


def _contains_circuit_call(node: ast.AST, circuit_names: set[str]) -> bool:
    return any(
        isinstance(child, ast.Call)
        and isinstance(child.func, ast.Attribute)
        and isinstance(child.func.value, ast.Name)
        and child.func.value.id in circuit_names
        for child in ast.walk(node)
    )


def _assign_target(target: ast.expr, value: Any, environment: dict[str, Any]) -> None:
    if isinstance(target, ast.Name):
        environment[target.id] = value
        return
    if isinstance(target, (ast.Tuple, ast.List)):
        if len(target.elts) != len(value):
            raise UnsupportedCircuitError("asignación múltiple no válida")
        for item, assigned_value in zip(target.elts, value):
            _assign_target(item, assigned_value, environment)
        return
    raise UnsupportedCircuitError("destino de asignación no soportado")


def _run_circuit_statements(
    statements: list[ast.stmt],
    environment: dict[str, Any],
    circuit_names: set[str],
) -> None:
    for statement in statements:
        if isinstance(statement, ast.Assign):
            try:
                value = _safe_eval(statement.value, environment)
            except UnsupportedCircuitError:
                if any(
                    isinstance(target, ast.Name) and target.id in circuit_names
                    for target in statement.targets
                ) or _contains_circuit_call(statement.value, circuit_names):
                    raise
                continue
            for target in statement.targets:
                _assign_target(target, value, environment)
        elif isinstance(statement, ast.AnnAssign) and statement.value is not None:
            try:
                value = _safe_eval(statement.value, environment)
            except UnsupportedCircuitError:
                if isinstance(statement.target, ast.Name) and statement.target.id in circuit_names:
                    raise
                continue
            _assign_target(statement.target, value, environment)
        elif isinstance(statement, ast.AugAssign):
            if not isinstance(statement.target, ast.Name):
                raise UnsupportedCircuitError("asignación incremental no soportada")
            current = environment[statement.target.id]
            right = _safe_eval(statement.value, environment)
            operator_function = BINARY_OPERATORS.get(type(statement.op))
            if operator_function is None:
                raise UnsupportedCircuitError("operador de asignación no soportado")
            environment[statement.target.id] = operator_function(current, right)
        elif isinstance(statement, ast.Expr) and _contains_circuit_call(statement, circuit_names):
            _safe_eval(statement.value, environment)
        elif isinstance(statement, ast.For) and _contains_circuit_call(statement, circuit_names):
            if not isinstance(statement.target, ast.Name):
                raise UnsupportedCircuitError("bucle for no soportado")
            for value in _safe_eval(statement.iter, environment):
                environment[statement.target.id] = value
                _run_circuit_statements(statement.body, environment, circuit_names)
            _run_circuit_statements(statement.orelse, environment, circuit_names)
        elif isinstance(statement, ast.If) and _contains_circuit_call(statement, circuit_names):
            branch = statement.body if _safe_eval(statement.test, environment) else statement.orelse
            _run_circuit_statements(branch, environment, circuit_names)


def _circuit_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.Assign, ast.AnnAssign))
            and isinstance(node.value, ast.Call)
            and _call_name(node.value.func) == "QuantumCircuit"
        ):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names.update(target.id for target in targets if isinstance(target, ast.Name))
    return names


def analyze_source(source: str) -> dict[str, int]:
    tree = ast.parse(source)
    circuits = _circuit_names(tree)
    if not circuits:
        raise UnsupportedCircuitError("no se encontró una construcción QuantumCircuit")

    environment: dict[str, Any] = {"__name__": "__main__"}
    _run_circuit_statements(tree.body, environment, circuits)
    circuit = environment.get("circuit")
    if not isinstance(circuit, QuantumCircuit):
        circuit = next(
            (environment[name] for name in circuits if isinstance(environment.get(name), QuantumCircuit)),
            None,
        )
    if not isinstance(circuit, QuantumCircuit):
        raise UnsupportedCircuitError("no se pudo construir el circuito principal")

    gates = [instruction.operation for instruction in circuit.data]
    measured = sum(operation.name == "measure" for operation in gates)
    non_barrier_gates = [
        operation for operation in gates if operation.name not in {"barrier", "measure"}
    ]
    return {
        "qubits": circuit.num_qubits,
        "bits_clasicos": circuit.num_clbits,
        "profundidad": circuit.depth(),
        "puertas": len(non_barrier_gates),
        "puertas_1_qubit": sum(operation.num_qubits == 1 for operation in non_barrier_gates),
        "puertas_2_qubits": sum(operation.num_qubits == 2 for operation in non_barrier_gates),
        "puertas_3_o_mas_qubits": sum(
            operation.num_qubits >= 3 for operation in non_barrier_gates
        ),
        "mediciones": measured,
    }


def read_active_urls(reference: Path) -> dict[str, str]:
    tree = ast.parse(reference.read_text(encoding="utf-8-sig"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "urls" for target in node.targets
        ):
            urls = ast.literal_eval(node.value)
            if not isinstance(urls, dict) or not all(
                isinstance(name, str) and isinstance(url, str)
                for name, url in urls.items()
            ):
                raise ValueError("El diccionario 'urls' debe contener nombres y URLs de texto.")
            return urls
    raise ValueError(f"No se encontró el diccionario 'urls' en {reference}.")


def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != ALLOWED_HOST
        or not parsed.path.startswith(ALLOWED_PATH_PREFIX)
    ):
        raise ValueError(
            "solo se admiten URLs HTTPS de circuitos del repositorio Qcraft-UEx/QCRAFT-Scheduler"
        )


def summarize(results: list[dict[str, Any]]) -> dict[str, tuple[float, int, int]]:
    metrics = (
        "qubits",
        "bits_clasicos",
        "profundidad",
        "puertas",
        "puertas_1_qubit",
        "puertas_2_qubits",
        "puertas_3_o_mas_qubits",
        "mediciones",
    )
    return {
        metric: (
            sum(result[metric] for result in results) / len(results),
            min(result[metric] for result in results),
            max(result[metric] for result in results),
        )
        for metric in metrics
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analiza los circuitos activos de un script de referencia sin ejecutarlos."
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=REFERENCE_SCRIPT,
        help="script que contiene el diccionario urls (por defecto, scheduler-async_IslasEdges_Short.py)",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=CSV_OUTPUT,
        help="archivo CSV de salida (por defecto: analisis_circuitos.csv)",
    )
    args = parser.parse_args()

    urls = read_active_urls(args.reference)
    results: list[dict[str, Any]] = []
    failures: list[tuple[str, str]] = []

    for name, url in urls.items():
        try:
            validate_url(url)
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            metrics = analyze_source(response.text)
            results.append({"circuito": name, "url": url, **metrics})
            print(
                f"{name}: {metrics['qubits']} qubits, profundidad "
                f"{metrics['profundidad']}, {metrics['puertas']} puertas"
            )
        except (
            requests.RequestException,
            SyntaxError,
            UnsupportedCircuitError,
            ValueError,
            TypeError,
            IndexError,
            KeyError,
            AttributeError,
        ) as error:
            failures.append((name, str(error)))
            print(f"ERROR {name}: {error}")

    columns = [
        "circuito",
        "url",
        "qubits",
        "bits_clasicos",
        "profundidad",
        "puertas",
        "puertas_1_qubit",
        "puertas_2_qubits",
        "puertas_3_o_mas_qubits",
        "mediciones",
    ]
    with args.csv.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nCircuitos analizados correctamente: {len(results)} de {len(urls)}")
    print(f"Resultados detallados guardados en: {args.csv}")
    if results:
        print("\nResumen (media, mínimo, máximo):")
        for metric, (average, minimum, maximum) in summarize(results).items():
            print(f"  {metric}: {average:.2f}, {minimum}, {maximum}")
    else:
        print("No se pudo analizar ningún circuito.")

    if failures:
        print("\nCircuitos con errores:")
        for name, error in failures:
            print(f"  {name}: {error}")
    return 1 if failures or not results else 0


if __name__ == "__main__":
    raise SystemExit(main())
