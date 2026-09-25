import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from scipy.spatial.distance import jensenshannon


BASE_DIR = Path(__file__).resolve().parent
BASE_JSON_DIR = BASE_DIR / "100Circuitos"
RUTA_INDIVIDUALES = BASE_DIR / "Individuales" / "Fez" / "EjecucionesIndividuales.json"
SALIDA_DIR = BASE_DIR / "graficas_agrupadas_json_ibm"

ARCHIVOS_MODOS = {
    "Dynamic T1": BASE_JSON_DIR / "ModoDinamico" / "MedidaInFirst" / "dynamic_t1" / "dynamic_t1.json",
    "Quantum Island": BASE_JSON_DIR / "Islas2" / "Islas3Buena.json",
    "Time": BASE_JSON_DIR / "Time" / "EjecucionTime.json",
}

COLORES = {
    nombre: plt.get_cmap("tab10")(indice % 10)
    for indice, nombre in enumerate(ARCHIVOS_MODOS)
}


def cargar_json(ruta):
    with ruta.open("r", encoding="utf-8") as archivo:
        datos = json.load(archivo)

    if not isinstance(datos, list):
        raise ValueError(f"El JSON debe contener una lista: {ruta}")
    return datos


def agrupar_por_circuito(datos):
    ejecuciones = defaultdict(list)

    for item in datos:
        circuito = item.get("circuit") if isinstance(item, dict) else None
        distribucion = item.get("value") if isinstance(item, dict) else None
        if circuito and isinstance(distribucion, dict) and distribucion:
            ejecuciones[circuito].append(distribucion)

    return ejecuciones


def validar_distribucion(distribucion, ruta, circuito):
    valores = list(distribucion.values())
    if any(not isinstance(valor, (int, float)) or valor < 0 for valor in valores):
        raise ValueError(f"Valores invalidos en {ruta}, circuito {circuito}")
    if sum(valores) <= 0:
        raise ValueError(f"La distribucion no tiene shots validos en {ruta}, circuito {circuito}")


def calcular_metricas(distribucion_a, distribucion_b):
    claves = sorted(set(distribucion_a) | set(distribucion_b))
    valores_a = np.array([distribucion_a.get(clave, 0) for clave in claves], dtype=float)
    valores_b = np.array([distribucion_b.get(clave, 0) for clave in claves], dtype=float)
    valores_a /= valores_a.sum()
    valores_b /= valores_b.sum()

    hellinger = np.sqrt(np.sum((np.sqrt(valores_a) - np.sqrt(valores_b)) ** 2)) / np.sqrt(2)
    jensen = float(jensenshannon(valores_a, valores_b))
    return float(hellinger), jensen


def calcular_modo_con_huecos(ruta_json, referencias):
    filas = []
    usos_referencia = defaultdict(int)

    for posicion, item in enumerate(cargar_json(ruta_json), start=1):
        circuito = item.get("circuit", "Unknown circuit")
        distribucion = item.get("value")
        indice = usos_referencia[circuito]
        usos_referencia[circuito] += 1
        hellinger = np.nan
        jensen = np.nan

        if circuito in referencias and isinstance(distribucion, dict) and distribucion:
            indice = min(indice, len(referencias[circuito]) - 1)
            hellinger, jensen = calcular_metricas(
                referencias[circuito][indice], distribucion
            )

        filas.append({
            "Circuit": circuito,
            "Position": posicion,
            "Hellinger": hellinger,
            "Jensen-Shannon": jensen,
        })

    return pd.DataFrame(filas)


def guardar_grafica_barras(datos_por_modo, columna, nombre_archivo):
    figura, eje = plt.subplots(figsize=(15, 7))
    tamano_fuente = 20
    tamano_fuente_leyenda = 16
    maximo = max((len(datos) for datos in datos_por_modo.values()), default=1)
    posiciones = np.arange(1, maximo + 1)

    valores_por_modo = {
        nombre: datos.set_index("Position")[columna].reindex(posiciones).to_numpy(dtype=float)
        for nombre, datos in datos_por_modo.items()
    }
    for indice, posicion in enumerate(posiciones):
        modos_ordenados = sorted(
            datos_por_modo,
            key=lambda nombre: (
                np.isnan(valores_por_modo[nombre][indice]),
                valores_por_modo[nombre][indice],
            ),
            reverse=True,
        )
        for nombre in modos_ordenados:
            valor = valores_por_modo[nombre][indice]
            if np.isfinite(valor):
                eje.bar(
                    posicion,
                    valor,
                    width=0.82,
                    color=COLORES[nombre],
                    alpha=0.78,
                    edgecolor="black",
                    linewidth=0.25,
                    label="_nolegend_",
                )

    eje.set_xlabel("Executed circuit", fontsize=tamano_fuente)
    eje.set_ylabel(columna, fontsize=tamano_fuente)
    eje.set_xlim(1, maximo)
    eje.set_ylim(bottom=0)
    eje.tick_params(axis="both", labelsize=tamano_fuente)
    eje.grid(True, alpha=0.3)
    eje.legend(
        handles=[
            Patch(facecolor=COLORES[nombre], edgecolor="black", label=nombre)
            for nombre in datos_por_modo
        ],
        loc="upper right",
        bbox_to_anchor=(0.98, 0.98),
        borderaxespad=0.0,
        frameon=True,
        fontsize=tamano_fuente_leyenda,
    )
    figura.tight_layout()
    figura.savefig(SALIDA_DIR / nombre_archivo, dpi=300, bbox_inches="tight")
    plt.close(figura)


def normalizar_nombre(nombre):
    return "_".join(nombre.lower().replace("-", "").split())


def main():
    parser = argparse.ArgumentParser(
        description="Compare IBM JSON modes against individual circuit results."
    )
    parser.add_argument(
        "--modo", choices=ARCHIVOS_MODOS, help="Process only the selected mode."
    )
    args = parser.parse_args()

    if not RUTA_INDIVIDUALES.exists():
        raise FileNotFoundError(f"Individual reference not found: {RUTA_INDIVIDUALES}")

    SALIDA_DIR.mkdir(exist_ok=True)
    referencias = agrupar_por_circuito(cargar_json(RUTA_INDIVIDUALES))
    modos = {args.modo: ARCHIVOS_MODOS[args.modo]} if args.modo else ARCHIVOS_MODOS
    datos_modos = {}

    for nombre, ruta_json in modos.items():
        if not ruta_json.exists():
            print(f"[WARNING] JSON not found for {nombre}: {ruta_json}")
            continue
        datos = calcular_modo_con_huecos(ruta_json, referencias)
        datos_modos[nombre] = datos
        datos.assign(Mode=nombre).to_csv(
            SALIDA_DIR / f"table_{normalizar_nombre(nombre)}.csv", index=False
        )
        print(f"[OK] {nombre}: {len(datos)} circuits processed")

    if not datos_modos:
        print("[WARNING] No valid JSON modes were found")
        return

    for columna in ("Hellinger", "Jensen-Shannon"):
        sufijo = "hellinger" if columna == "Hellinger" else "jensen"
        guardar_grafica_barras(datos_modos, columna, f"{sufijo}_por_circuito.png")

    tabla = pd.concat(
        [datos.assign(Mode=nombre) for nombre, datos in datos_modos.items()],
        ignore_index=True,
    )
    tabla.to_csv(SALIDA_DIR / "table_all_modes.csv", index=False)
    huecos = int(tabla[["Hellinger", "Jensen-Shannon"]].isna().any(axis=1).sum())
    print(f"[OK] {len(datos_modos)} modes processed; {huecos} missing comparisons")


if __name__ == "__main__":
    main()