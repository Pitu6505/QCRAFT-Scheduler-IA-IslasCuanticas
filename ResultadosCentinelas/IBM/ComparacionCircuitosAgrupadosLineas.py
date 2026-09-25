import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ComparacionCircuitos import (
    ARCHIVOS_MODOS,
    BASE_DIR,
    RUTA_INDIVIDUALES,
    calcular_metricas,
)


GRUPOS = {
    "local": {
        "titulo": "Modos estaticos locales",
        "modos": [nombre for nombre in ARCHIVOS_MODOS if nombre.startswith("Local ")],
    },
    "global": {
        "titulo": "Modos estaticos globales",
        "modos": [nombre for nombre in ARCHIVOS_MODOS if nombre.startswith("Global ")],
    },
    "dinamico": {
        "titulo": "Modos dinamicos",
        "modos": [nombre for nombre in ARCHIVOS_MODOS if nombre.startswith("Dynamic ")],
    },
}


COLORES = {
    nombre: plt.get_cmap("tab10")(indice % 10)
    for indice, nombre in enumerate(ARCHIVOS_MODOS)
}


def cargar_json(ruta):
    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def agrupar_referencias(datos):
    referencias = defaultdict(list)
    for item in datos:
        circuito = item.get("circuit")
        distribucion = item.get("value")
        if circuito and isinstance(distribucion, dict) and distribucion:
            referencias[circuito].append(distribucion)
    return referencias


def calcular_modo_con_huecos(ruta_json, referencias):
    datos = cargar_json(ruta_json)
    usos_referencia = defaultdict(int)
    filas = []

    for posicion, item in enumerate(datos, start=1):
        circuito = item.get("circuit", "Sin circuito")
        distribucion = item.get("value")
        indice_referencia = usos_referencia[circuito]
        usos_referencia[circuito] += 1

        hellinger = np.nan
        jensen = np.nan
        if (
            circuito in referencias
            and isinstance(distribucion, dict)
            and distribucion
        ):
            indice_referencia = min(indice_referencia, len(referencias[circuito]) - 1)
            hellinger, jensen = calcular_metricas(
                referencias[circuito][indice_referencia], distribucion
            )

        filas.append({
            "Circuito": circuito,
            "Posicion": posicion,
            "Hellinger": hellinger,
            "Jensen-Shannon": jensen,
        })

    return pd.DataFrame(filas)


def guardar_grafica(grupo, datos_por_modo, columna, nombre_archivo):
    figura, eje = plt.subplots(figsize=(15, 7))
    maximo = max((len(datos) for datos in datos_por_modo.values()), default=1)

    for nombre, datos in datos_por_modo.items():
        valores = datos[columna].to_numpy(dtype=float)
        if np.isfinite(valores).any():
            eje.plot(
                datos["Posicion"],
                valores,
                marker="o",
                markersize=3.5,
                linewidth=1.3,
                color=COLORES[nombre],
                label=nombre,
            )

    eje.set_title(f"{grupo['titulo']}: {columna} por circuito")
    eje.set_xlabel("Circuito ejecutado")
    eje.set_ylabel(columna)
    eje.set_xlim(1, maximo)
    eje.set_ylim(bottom=0)
    eje.grid(True, alpha=0.3)
    eje.legend(
        loc="upper left",
        bbox_to_anchor=(1.01, 1),
        frameon=True,
        fontsize=14,
    )
    figura.tight_layout()
    figura.savefig(BASE_DIR / "graficas_agrupadas" / nombre_archivo, dpi=300, bbox_inches="tight")
    plt.close(figura)


def main():
    if not RUTA_INDIVIDUALES.exists():
        raise FileNotFoundError(f"No se encontro la referencia individual: {RUTA_INDIVIDUALES}")

    referencias = agrupar_referencias(cargar_json(RUTA_INDIVIDUALES))
    carpeta_salida = BASE_DIR / "graficas_agrupadas"
    carpeta_salida.mkdir(exist_ok=True)

    datos_modos = {}
    for nombre, ruta_json in ARCHIVOS_MODOS.items():
        if not ruta_json.exists():
            print(f"[AVISO] No existe el JSON de {nombre}: {ruta_json}")
            continue
        datos_modos[nombre] = calcular_modo_con_huecos(ruta_json, referencias)

    for clave_grupo, grupo in GRUPOS.items():
        datos_grupo = {
            nombre: datos_modos[nombre]
            for nombre in grupo["modos"]
            if nombre in datos_modos
        }
        if not datos_grupo:
            continue

        for columna, sufijo in (
            ("Hellinger", "hellinger"),
            ("Jensen-Shannon", "jensen"),
        ):
            guardar_grafica(
                grupo,
                datos_grupo,
                columna,
                f"{clave_grupo}_{sufijo}_por_circuito.png",
            )

        tabla = pd.concat(
            [datos.assign(Modo=nombre) for nombre, datos in datos_grupo.items()],
            ignore_index=True,
        )
        tabla.to_csv(
            carpeta_salida / f"tabla_{clave_grupo}_por_circuito.csv",
            index=False,
        )

        huecos = int(tabla[["Hellinger", "Jensen-Shannon"]].isna().any(axis=1).sum())
        print(f"[OK] {grupo['titulo']}: {len(datos_grupo) * 2} graficas; {huecos} registros con hueco")


if __name__ == "__main__":
    main()