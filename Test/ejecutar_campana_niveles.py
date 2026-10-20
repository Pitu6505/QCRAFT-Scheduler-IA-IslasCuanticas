"""Lanza escenarios de colocación en serie y espera sus resultados reales."""

import argparse
import asyncio
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import aiohttp
import requests

SCHEDULER_URL = "http://localhost:8082"
BACKEND = "ibm_fez"
SHOTS = 10_000
POLL_SECONDS = 15
TIMEOUT_SECONDS = 6 * 60 * 60

# El orden de esta lista es el orden real de lanzamiento.
SCENARIOS = (
    ("nivel_3", "Solo nivel 3", "Islas_Cuanticas_Edges_Nivel3"),
    ("niveles_2_3", "Niveles 2 + 3", "Islas_Cuanticas_Edges_Nivel2_3"),
    ("niveles_1_2_3", "Niveles 1 + 2 + 3", "Islas_Cuanticas_Edges_Nivel1_2_3"),
)

TEST_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = TEST_DIR.parent
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from analizar_niveles_colocacion import load_url_entries


class CampaignTimeout(TimeoutError):
    def __init__(self, message, completed):
        super().__init__(message)
        self.completed = completed


def decode_result_response(payload):
    """El endpoint /result serializa dos veces el JSON de MongoDB."""
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, list):
        raise ValueError("La respuesta de /result no contiene una lista de resultados.")
    return payload


def completed_documents(payload):
    documents = decode_result_response(payload)
    return documents if any(document.get("value") for document in documents) else None


def matching_job_metrics(records, submitted_ids):
    matched = []
    observed_ids = set()
    for record in records:
        users = {str(user) for user in record.get("users", [])}
        matched_users = users.intersection(submitted_ids)
        if matched_users:
            matched.append(record)
            observed_ids.update(matched_users)

    missing_ids = submitted_ids - observed_ids
    if missing_ids:
        raise RuntimeError(
            "Faltan métricas de transpilation para los circuitos con ID: "
            + ", ".join(sorted(missing_ids))
        )
    return matched


def read_metrics(path):
    metrics_path = Path(path)
    if not metrics_path.exists():
        return []
    records = []
    with metrics_path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Métricas JSONL inválidas en la línea {line_number}: {error}"
                ) from error
    return records


async def submit_circuit(session, scheduler_url, name, url, policy, shots):
    submitted_at = time.monotonic()
    try:
        async with session.post(
            f"{scheduler_url.rstrip('/')}/circuit",
            json={
                "url": url,
                "shots": shots,
                "provider": "ibm",
                "policy": policy,
            },
        ) as response:
            response.raise_for_status()
            response_text = await response.text()
        circuit_id = response_text.strip().strip('"')
        if not circuit_id.isdigit():
            raise RuntimeError(
                f"El scheduler devolvió un ID no válido: {response_text!r}"
            )
        return name, circuit_id, submitted_at, None
    except Exception as error:
        return name, None, submitted_at, error


async def submit_scenario(
    scheduler_url,
    circuits,
    policy,
    shots,
):
    timeout = aiohttp.ClientTimeout(total=180)
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [
            asyncio.create_task(
                submit_circuit(
                    session,
                    scheduler_url,
                    name,
                    url,
                    policy,
                    shots,
                )
            )
            for name, url in circuits
        ]
        submitted = {}
        errors = []
        for index, task in enumerate(asyncio.as_completed(tasks), start=1):
            name, circuit_id, submitted_at, error = await task
            if error is not None:
                errors.append((name, error))
                print(f"  Falló el envío de {name}: {error}")
                continue
            submitted[circuit_id] = {
                "name": name,
                "submitted_at": submitted_at,
            }
            print(f"  Enviado [{index}/{len(circuits)}] {name} ({circuit_id})")
    return submitted, errors


def wait_for_results(session, scheduler_url, submitted, timeout_seconds, poll_seconds):
    pending = set(submitted)
    completed = {}
    deadline = time.monotonic() + timeout_seconds

    while pending:
        for circuit_id in tuple(pending):
            response = session.get(
                f"{scheduler_url.rstrip('/')}/result",
                params={"id": circuit_id},
                timeout=60,
            )
            response.raise_for_status()
            documents = completed_documents(response.json())
            if documents is not None:
                completed[circuit_id] = {
                    "documents": documents,
                    "elapsed_seconds": time.monotonic()
                    - submitted[circuit_id]["submitted_at"],
                }
                pending.remove(circuit_id)
                print(
                    f"  Resultado recibido: {submitted[circuit_id]['name']} "
                    f"({circuit_id})"
                )

        if pending:
            if time.monotonic() >= deadline:
                raise CampaignTimeout(
                    "Se agotó el tiempo de espera; no se iniciará el siguiente escenario. "
                    f"IDs pendientes: {', '.join(sorted(pending))}",
                    completed,
                )
            print(f"  Esperando {len(pending)} resultados...")
            time.sleep(poll_seconds)

    return completed


def write_csv(path, fieldnames, rows):
    with Path(path).open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ejecuta los escenarios IBM uno tras otro y espera cada tanda."
    )
    parser.add_argument("--scheduler-url", default=SCHEDULER_URL)
    parser.add_argument("--shots", type=int, default=SHOTS)
    parser.add_argument("--timeout-hours", type=float, default=6)
    parser.add_argument("--poll-seconds", type=int, default=POLL_SECONDS)
    parser.add_argument(
        "--scenarios",
        default=",".join(scenario[0] for scenario in SCENARIOS),
        help="IDs en orden y separados por comas: nivel_3,niveles_2_3,niveles_1_2_3",
    )
    parser.add_argument(
        "--urls-file",
        type=Path,
        default=TEST_DIR / "scheduler-async_IslasEdges_Short.py",
    )
    parser.add_argument("--output-prefix", type=Path, default=Path("resultados_campana"))
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Permite enviar trabajos reales a IBM; sin esta opción solo muestra el plan.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.shots < 1 or args.shots > 20_000:
        raise ValueError("Los shots deben estar entre 1 y 20000.")
    if args.timeout_hours <= 0 or args.poll_seconds <= 0:
        raise ValueError("El timeout y el intervalo de consulta deben ser positivos.")
    selected_ids = [item.strip() for item in args.scenarios.split(",") if item.strip()]
    scenario_by_id = {scenario[0]: scenario for scenario in SCENARIOS}
    if not selected_ids or len(set(selected_ids)) != len(selected_ids):
        raise ValueError("Indica uno o más escenarios válidos, sin repetir.")
    unknown_ids = set(selected_ids) - set(scenario_by_id)
    if unknown_ids:
        raise ValueError(f"Escenarios desconocidos: {', '.join(sorted(unknown_ids))}")
    scenarios = [scenario_by_id[scenario_id] for scenario_id in selected_ids]
    circuits = load_url_entries(args.urls_file)
    total_shots = len(circuits) * len(scenarios) * args.shots

    print(f"QPU: {BACKEND}; scheduler: {args.scheduler_url}")
    print(f"Circuitos: {len(circuits)}; shots por circuito: {args.shots}")
    print("Orden: " + " -> ".join(scenario[1] for scenario in scenarios))
    print(
        f"Muestras lógicas solicitadas: {total_shots:,} circuit-shots "
        "(no equivale a shots/jobs IBM: el scheduler puede agrupar circuitos)."
    )
    print("Envío: todas las peticiones del escenario se lanzan simultáneamente.")
    print("Cada escenario espera a que todos sus resultados estén guardados antes de continuar.")
    if not args.execute:
        print("Modo de planificación: no se ha enviado ningún trabajo. Añade --execute para lanzar.")
        return

    confirmation = input(
        f"Vas a enviar {total_shots:,} circuit-shots a IBM {BACKEND}. "
        "Escribe EJECUTAR para confirmar: "
    )
    if confirmation != "EJECUTAR":
        print("Campaña cancelada; no se ha enviado ningún trabajo.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_prefix = args.output_prefix
    if not output_prefix.is_absolute():
        output_prefix = Path.cwd() / output_prefix
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    circuit_csv = output_prefix.with_name(f"{output_prefix.name}_{timestamp}_circuitos.csv")
    jobs_csv = output_prefix.with_name(f"{output_prefix.name}_{timestamp}_lotes.csv")
    metrics_path = REPOSITORY_ROOT / "resultados_metricas_ibm.jsonl"

    circuit_rows = []
    job_rows = []
    session = requests.Session()

    for scenario_id, scenario_name, policy in scenarios:
        print(f"\nIniciando escenario: {scenario_name} ({policy})")
        submitted, submission_errors = asyncio.run(
            submit_scenario(
                args.scheduler_url,
                circuits,
                policy,
                args.shots,
            )
        )

        timeout_error = None
        if submitted:
            try:
                completed = wait_for_results(
                    session,
                    args.scheduler_url,
                    submitted,
                    args.timeout_hours * 60 * 60,
                    args.poll_seconds,
                )
            except CampaignTimeout as error:
                completed = error.completed
                timeout_error = error

            for circuit_id, result in completed.items():
                circuit_rows.append({
                    "scenario": scenario_name,
                    "scenario_id": scenario_id,
                    "circuit": submitted[circuit_id]["name"],
                    "user_id": circuit_id,
                    "backend": BACKEND,
                    "shots": args.shots,
                    "elapsed_seconds": round(result["elapsed_seconds"], 3),
                    "result": json.dumps(result["documents"], sort_keys=True),
                })
            metric_records = matching_job_metrics(
                read_metrics(metrics_path),
                set(completed),
            )
            for metric in metric_records:
                job_rows.append({
                    "scenario": scenario_name,
                    "job_id": metric["job_id"],
                    "backend": metric["backend"],
                    "users": json.dumps(metric["users"]),
                    "circuit_names": json.dumps(metric["circuit_names"]),
                    "shots": metric["shots"],
                    "placement_layout_applied": metric["placement_layout_applied"],
                    "transpilation_seconds": metric["transpilation_seconds"],
                    "execution_seconds": metric["execution_seconds"],
                    "transpiled_depth": metric["transpiled_depth"],
                    "swap_gate_count": metric["swap_gate_count"],
                    "two_qubit_gate_count": metric["two_qubit_gate_count"],
                    "operation_counts": json.dumps(metric["operation_counts"], sort_keys=True),
                })

        write_csv(
            circuit_csv,
            (
                "scenario", "scenario_id", "circuit", "user_id", "backend",
                "shots", "elapsed_seconds", "result",
            ),
            circuit_rows,
        )
        write_csv(
            jobs_csv,
            (
                "scenario", "job_id", "backend", "users", "circuit_names", "shots",
                "placement_layout_applied", "transpilation_seconds",
                "execution_seconds", "transpiled_depth",
                "swap_gate_count", "two_qubit_gate_count", "operation_counts",
            ),
            job_rows,
        )

        if timeout_error is not None:
            raise timeout_error

        if submission_errors:
            failures = "; ".join(
                f"{name}: {error}" for name, error in submission_errors
            )
            raise RuntimeError(
                f"Falló el envío de {scenario_name}; no se lanzarán los siguientes "
                f"escenarios. Envíos correctos: {len(submitted)}/{len(circuits)}. "
                f"Errores: {failures}"
            )

        scenario_jobs = [
            row for row in job_rows if row["scenario"] == scenario_name
        ]
        print(
            f"Escenario completado: {len(submitted)} circuitos, "
            f"{len(scenario_jobs)} lotes IBM. "
            f"SWAP explícitos en circuitos transpiled: "
            f"{sum(row['swap_gate_count'] for row in scenario_jobs)}."
        )

    print(f"\nResultados por circuito: {circuit_csv}")
    print(f"Métricas por lote IBM: {jobs_csv}")


if __name__ == "__main__":
    main()
