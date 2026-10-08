"""Evalúa un modelo exportado usando resultados ya obtenidos de IBM Quantum.

El fichero de entrada puede ser JSONL (un objeto por línea) o un array JSON.
Cada registro debe contener ``tasas_error_v0_v4`` y ``circuito`` o
``algoritmo_real``. Este script no envía trabajos a IBM.
"""

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
)


FEATURES = ["v0", "v1", "v2", "v3", "v4"]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def iter_records(path):
    with path.open(encoding="utf-8") as file:
        content = file.read().strip()

    if not content:
        return
    records = json.loads(content) if content.startswith("[") else (
        json.loads(line) for line in content.splitlines() if line.strip()
    )
    yield from records


def get_label(record, label_field):
    if label_field in record:
        return record[label_field]
    if label_field != "algoritmo_real" and "algoritmo_real" in record:
        return record["algoritmo_real"]
    circuit = record.get("circuito")
    if circuit:
        return circuit.split("_")[0].replace("-noancilla", "")
    raise ValueError(
        "No se encontró la etiqueta real. Añade 'algoritmo_real' "
        "o 'circuito' al resultado de IBM."
    )


def load_ibm_results(path, label_field):
    rows = []
    for record in iter_records(path):
        vector = record.get("tasas_error_v0_v4")
        if not isinstance(vector, list) or len(vector) != len(FEATURES):
            continue
        rows.append({
            **dict(zip(FEATURES, vector)),
            "algoritmo_real": get_label(record, label_field),
        })

    if not rows:
        raise ValueError(f"No se encontraron resultados IBM válidos en {path}.")
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        required=True,
        help="JSON/JSONL exportado con resultados y tasas v0..v4.",
    )
    parser.add_argument(
        "--model",
        default=str(PROJECT_ROOT / "modelo_forense_algoritmo.pkl"),
        help="Ruta al modelo forense exportado.",
    )
    parser.add_argument(
        "--label-field",
        default="algoritmo_real",
        help="Campo que contiene la etiqueta conocida de cada ejecución.",
    )
    parser.add_argument(
        "--output",
        help="Ruta opcional para guardar las predicciones en CSV.",
    )
    args = parser.parse_args()

    data = load_ibm_results(Path(args.results), args.label_field)
    model = joblib.load(args.model)
    predictions = model.predict(data[FEATURES])
    data["prediccion"] = predictions
    data["correcta"] = data["prediccion"] == data["algoritmo_real"]
    labels = sorted(set(data["algoritmo_real"]) | set(predictions))

    print(f"Resultados IBM evaluados: {len(data)}")
    print(f"Accuracy: {accuracy_score(data['algoritmo_real'], predictions):.4f}")
    print(
        "Balanced accuracy: "
        f"{balanced_accuracy_score(data['algoritmo_real'], predictions):.4f}"
    )
    print("\nInforme por clase:")
    print(classification_report(
        data["algoritmo_real"],
        predictions,
        labels=labels,
        zero_division=0,
    ))
    print("Matriz de confusión (filas=real, columnas=predicha):")
    print(pd.DataFrame(
        confusion_matrix(data["algoritmo_real"], predictions, labels=labels),
        index=labels,
        columns=labels,
    ))

    if args.output:
        data.to_csv(args.output, index=False)
        print(f"\nPredicciones guardadas en: {args.output}")


if __name__ == "__main__":
    main()
