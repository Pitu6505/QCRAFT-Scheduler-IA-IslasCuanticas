"""Validación local reproducible de los modelos ML exportados."""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import RepeatedStratifiedKFold


FEATURES = ["v0", "v1", "v2", "v3", "v4"]
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def iter_records(path):
    with path.open(encoding="utf-8") as file:
        content = file.read().strip()

    if not content:
        return

    if content.startswith("["):
        records = json.loads(content)
    else:
        records = (json.loads(line) for line in content.splitlines() if line.strip())

    yield from records


def algorithm_label(record):
    value = record.get("algoritmo") or record.get("algoritmo_real")
    if value:
        return value

    circuit = record.get("circuito")
    if not circuit:
        raise ValueError("Cada registro necesita 'circuito' o 'algoritmo_real'.")

    return circuit.split("_")[0].replace("-noancilla", "")


def load_dataset(path):
    rows = []
    for record in iter_records(path):
        vector = record.get("tasas_error_v0_v4")
        if not isinstance(vector, list) or len(vector) != len(FEATURES):
            continue

        rows.append({
            **dict(zip(FEATURES, vector)),
            "algoritmo": algorithm_label(record),
        })

    if not rows:
        raise ValueError(f"No se encontraron registros válidos en {path}.")

    return pd.DataFrame(rows)


def print_report(title, y_true, y_pred, labels):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")
    print(f"Muestras: {len(y_true)}")
    print(f"Accuracy: {accuracy_score(y_true, y_pred):.4f}")
    print(f"Balanced accuracy: {balanced_accuracy_score(y_true, y_pred):.4f}")
    print("\nInforme por clase:")
    print(classification_report(y_true, y_pred, labels=labels, zero_division=0))
    print("Matriz de confusión (filas=real, columnas=predicha):")
    print(pd.DataFrame(confusion_matrix(y_true, y_pred, labels=labels), index=labels, columns=labels))


def cross_validate(model, data, labels, repeats, folds, seed):
    X = data[FEATURES]
    y = data["algoritmo"]
    splitter = RepeatedStratifiedKFold(
        n_splits=folds,
        n_repeats=repeats,
        random_state=seed,
    )
    scores = []
    all_true = []
    all_predictions = []
    for train_indices, test_indices in splitter.split(X, y):
        fold_model = clone(model)
        fold_model.fit(X.iloc[train_indices], y.iloc[train_indices])
        fold_predictions = fold_model.predict(X.iloc[test_indices])
        fold_true = y.iloc[test_indices]
        scores.append(accuracy_score(fold_true, fold_predictions))
        all_true.extend(fold_true.tolist())
        all_predictions.extend(fold_predictions.tolist())

    print_report("Validación cruzada repetida", all_true, all_predictions, labels)
    print(f"Accuracy media por partición: {np.mean(scores):.4f}")
    print(f"Desviación estándar: {np.std(scores, ddof=1):.4f}")


def evaluate_external(model, train_data, test_data, labels, title):
    model.fit(train_data[FEATURES], train_data["algoritmo"])
    predictions = model.predict(test_data[FEATURES])
    print_report(title, test_data["algoritmo"], predictions, labels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        nargs="+",
        default=[
            str(PROJECT_ROOT / "dataset_crosstalk_ml.json"),
            str(PROJECT_ROOT / "EjecucionesTopologicamenteDiferente.json"),
        ],
        help="Uno o varios datasets JSON/JSONL para combinar.",
    )
    parser.add_argument(
        "--model",
        default=str(PROJECT_ROOT / "modelo_forense_algoritmo.pkl"),
        help="Ruta al modelo forense exportado.",
    )
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    datasets = [load_dataset(Path(path)) for path in args.dataset]
    combined = pd.concat(datasets, ignore_index=True)
    labels = sorted(combined["algoritmo"].unique())
    model = joblib.load(args.model)

    print(f"Muestras combinadas: {len(combined)}")
    print("Distribución por clase:")
    print(combined["algoritmo"].value_counts().sort_index().to_string())
    cross_validate(model, combined, labels, args.repeats, args.folds, args.seed)

    if len(datasets) == 2:
        evaluate_external(
            joblib.load(args.model),
            datasets[0],
            datasets[1],
            labels,
            "Entrenamiento en el primer dataset y prueba en el segundo",
        )
        evaluate_external(
            joblib.load(args.model),
            datasets[1],
            datasets[0],
            labels,
            "Entrenamiento en el segundo dataset y prueba en el primero",
        )


if __name__ == "__main__":
    main()
