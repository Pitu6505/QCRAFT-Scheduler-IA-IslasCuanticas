import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon


BASE_DIR = Path(__file__).resolve().parent
RUTA_INDIVIDUALES = BASE_DIR / "Individuales" / "Fez" / "EjecucionesIndividuales.json"


ARCHIVOS_MODOS = {
    "Local Completo": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "completo" / "completoLocal.json",
    "Local DD": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "dd" / "ddLocal.json",
    "Local Robust": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "Robust" / "robust_local.json",
    "Local Standard": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "Standard" / "standard_local.json",
    "Local T1 decay": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "t1_decay" / "t1_decay_local.json",
    "Global Completo": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "completo" / "completo.json",
    "Global DD": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "dd" / "dd.json",
    "Global Robust": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "robust" / "robust.json",
    "Global Standard": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "standard" / "standard.json",
    "Global T1 decay": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "t1_decay" / "t1_decay.json",
    "Dynamic T1": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaInFirst" / "dynamic_t1" / "dynamic_t1.json",
    "Dynamic Ramsey": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaInFirst" / "dynamic_ramsey" / "dynamic_ramsey.json",
    "Dynamic Local T1": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaInMiddle" / "dynamic_t1_local" / "dynamic_t1_local.json",
    "Dynamic Local Ramsey": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaInMiddle" / "dynamic_local_ramsey" / "dynamic_local_ramsey.json",
    "Dynamic Local Initial T1": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaFirstIndependiente" / "dynamic_local_t1_initial" / "dynamic_local_t1_initial.json",
    "Dynamic Local Initial Ramsey": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaFirstIndependiente" / "dynamic_local_initial_ramsey" / "dynamic_local_initial_ramsey.json",
}


def cargar_json(ruta):
    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def agrupar_por_circuito(datos):
    ejecuciones = defaultdict(list)
    for item in datos:
        circuito = item.get("circuit")
        distribucion = item.get("value")
        if circuito and isinstance(distribucion, dict) and distribucion:
            ejecuciones[circuito].append(distribucion)
    return ejecuciones


def calcular_metricas(distribucion_referencia, distribucion_ejecucion):
    claves = sorted(set(distribucion_referencia) | set(distribucion_ejecucion))
    referencia = np.array([distribucion_referencia.get(clave, 0) for clave in claves], dtype=float)
    ejecucion = np.array([distribucion_ejecucion.get(clave, 0) for clave in claves], dtype=float)
    referencia /= referencia.sum()
    ejecucion /= ejecucion.sum()

    hellinger = np.sqrt(np.sum((np.sqrt(referencia) - np.sqrt(ejecucion)) ** 2)) / np.sqrt(2)
    jensen = float(jensenshannon(referencia, ejecucion))
    return float(hellinger), jensen


def comparar_con_referencia(ruta_modo):
    referencia = agrupar_por_circuito(cargar_json(RUTA_INDIVIDUALES))
    ejecuciones = agrupar_por_circuito(cargar_json(ruta_modo))
    resultados = []
    omitidos = 0

    for circuito, distribuciones in ejecuciones.items():
        if circuito not in referencia:
            omitidos += len(distribuciones)
            continue
        for numero, distribucion in enumerate(distribuciones, start=1):
            referencia_ejecucion = referencia[circuito][min(numero - 1, len(referencia[circuito]) - 1)]
            hellinger, jensen = calcular_metricas(referencia_ejecucion, distribucion)
            resultados.append({
                "Circuito": circuito,
                "Ejecucion": numero,
                "Hellinger": hellinger,
                "Jensen-Shannon": jensen,
            })

    return pd.DataFrame(resultados), omitidos


def guardar_grafica(datos, columna, titulo, ruta_salida, color):
    figura, eje = plt.subplots(figsize=(14, 6))
    eje.plot(
        np.arange(1, len(datos) + 1),
        datos[columna],
        color=color,
        marker="o",
        markersize=4,
        linewidth=1.2,
    )
    eje.set_title(titulo)
    eje.set_xlabel("Circuito ejecutado")
    eje.set_ylabel(columna)
    eje.set_xlim(1, max(len(datos), 1))
    eje.set_ylim(bottom=0)
    eje.grid(True, alpha=0.3)
    figura.tight_layout()
    figura.savefig(ruta_salida, dpi=300, bbox_inches="tight")
    plt.close(figura)


def procesar_modo(nombre, ruta_json):
    if not ruta_json.exists():
        print(f"[AVISO] No existe el JSON de {nombre}: {ruta_json}")
        return

    datos, omitidos = comparar_con_referencia(ruta_json)
    if datos.empty:
        print(f"[AVISO] No hay comparaciones validas para {nombre}")
        return

    carpeta_salida = ruta_json.parent
    datos.to_csv(carpeta_salida / "metricas_por_circuito.csv", index=False)
    datos[["Circuito", "Ejecucion", "Hellinger"]].to_csv(
        carpeta_salida / "tabla_hellinger.csv", index=False
    )
    datos[["Circuito", "Ejecucion", "Jensen-Shannon"]].to_csv(
        carpeta_salida / "tabla_jensen.csv", index=False
    )
    guardar_grafica(
        datos,
        "Hellinger",
        f"Distancia de Hellinger por circuito - {nombre}",
        carpeta_salida / "grafica_hellinger_por_circuito.png",
        "#176b87",
    )
    guardar_grafica(
        datos,
        "Jensen-Shannon",
        f"Distancia de Jensen-Shannon por circuito - {nombre}",
        carpeta_salida / "grafica_jensen_por_circuito.png",
        "#d95f02",
    )

    aviso = f"; {omitidos} omitidos sin referencia o distribucion" if omitidos else ""
    print(f"[OK] {nombre}: {len(datos)} comparaciones{aviso}")


def main():
    parser = argparse.ArgumentParser(description="Genera graficas de Hellinger y Jensen-Shannon por circuito.")
    parser.add_argument("--modo", choices=ARCHIVOS_MODOS, help="Procesa solo el modo indicado")
    args = parser.parse_args()

    if not RUTA_INDIVIDUALES.exists():
        raise FileNotFoundError(f"No se encontro la referencia individual: {RUTA_INDIVIDUALES}")

    modos = {args.modo: ARCHIVOS_MODOS[args.modo]} if args.modo else ARCHIVOS_MODOS
    for nombre, ruta_json in modos.items():
        procesar_modo(nombre, ruta_json)


if __name__ == "__main__":
    main()