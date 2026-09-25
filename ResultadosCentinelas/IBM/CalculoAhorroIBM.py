import argparse
import re
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
PRECIO_ITERACION = 5.0

ARCHIVOS_MODOS = {
    "Local Completo": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "completo" / "resultados_experimentacion.csv",
    "Local DD": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "dd" / "resultados_experimentacion.csv",
    "Local Robust": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "Robust" / "resultados_experimentacion.csv",
    "Local Standard": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "Standard" / "resultados_experimentacion.csv",
    "Local T1 decay": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoLocal" / "t1_decay" / "resultados_experimentacion.csv",
    "Global Completo": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "completo" / "resultados_experimentacion.csv",
    "Global DD": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "dd" / "resultados_experimentacion.csv",
    "Global Robust": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "robust" / "resultados_experimentacion.csv",
    "Global Standard": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "standard" / "resultados_experimentacion.csv",
    "Global T1 decay": BASE_DIR / "100Circuitos" / "ModoEstatico" / "ModoGlobal" / "t1_decay" / "resultados_experimentacion.csv",
    "Dynamic T1": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaInFirst" / "dynamic_t1" / "resultados_experimentacion.csv",
    "Dynamic Ramsey": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaInFirst" / "dynamic_ramsey" / "resultados_experimentacion.csv",
    "Dynamic Local T1": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaInMiddle" / "dynamic_t1_local" / "resultados_experimentacion.csv",
    "Dynamic Local Ramsey": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaInMiddle" / "dynamic_local_ramsey" / "resultados_experimentacion.csv",
    "Dynamic Local Initial T1": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaFirstIndependiente" / "dynamic_local_t1_initial" / "resultados_experimentacion.csv",
    "Dynamic Local Initial Ramsey": BASE_DIR / "100Circuitos" / "ModoDinamico" / "MedidaFirstIndependiente" / "dynamic_local_initial_ramsey" / "resultados_experimentacion.csv",
}

SALIDA_DIR = BASE_DIR / "ahorro_ibm"
COLUMNAS_REQUERIDAS = {"Fecha_Hora", "Layout_Circuito", "Layout_Centinela"}


def extraer_qubits_layout(valor):
    """Cuenta los qubits indicados en un layout como '[1- 2- 3];[24]'."""
    if pd.isna(valor) or str(valor).strip().upper() in {"", "N/A", "NA", "NONE"}:
        return None

    texto = str(valor).strip()
    grupos = re.findall(r"\[([^\]]*)\]", texto)
    if not grupos:
        return None

    cantidad = 0
    for grupo in grupos:
        cantidad += len(re.findall(r"\d+", grupo))
    return cantidad or None


def cargar_csv(ruta):
    datos = pd.read_csv(ruta, sep=";", dtype=str)
    faltantes = COLUMNAS_REQUERIDAS - set(datos.columns)
    if faltantes:
        raise ValueError(f"{ruta} no contiene las columnas requeridas: {sorted(faltantes)}")
    return datos


def calcular_modo(nombre, ruta):
    datos = cargar_csv(ruta)
    datos["Qubits_Circuito"] = datos["Layout_Circuito"].map(extraer_qubits_layout)
    datos["Qubits_Centinela"] = datos["Layout_Centinela"].map(extraer_qubits_layout)
    datos["Circuit_Qubits"] = datos[["Qubits_Circuito", "Qubits_Centinela"]].sum(axis=1, min_count=2)

    grupos = []
    filas_sin_qubits = 0
    for fecha_hora, grupo in datos.groupby("Fecha_Hora", sort=False, dropna=False):
        if grupo["Circuit_Qubits"].isna().any():
            filas_sin_qubits += int(grupo["Circuit_Qubits"].isna().sum())
            continue

        total_qubits = float(grupo["Circuit_Qubits"].sum())
        coste_agrupado = PRECIO_ITERACION
        for indice, fila in grupo.iterrows():
            coste_circuito = PRECIO_ITERACION * (fila["Circuit_Qubits"] / total_qubits)
            grupos.append({
                "Modo": nombre,
                "Fecha_Hora": fecha_hora,
                "Circuito": fila.get("Circuito_Nombre", ""),
                "Circuit_Qubits": int(fila["Circuit_Qubits"]),
                "Total_Qubits_Iteracion": int(total_qubits),
                "Circuitos_Iteracion": len(grupo),
                "Circuit_Cost": coste_circuito,
                "Iteration_Cost": coste_agrupado,
                "Ahorro_Circuito": PRECIO_ITERACION - coste_circuito,
            })

    detalle = pd.DataFrame(grupos)
    circuitos_validos = len(detalle)
    iteraciones = detalle[["Fecha_Hora"]].drop_duplicates().shape[0] if not detalle.empty else 0
    coste_sin_agrupacion = circuitos_validos * PRECIO_ITERACION
    coste_con_agrupacion = iteraciones * PRECIO_ITERACION
    ahorro = coste_sin_agrupacion - coste_con_agrupacion
    porcentaje = ahorro / coste_sin_agrupacion * 100 if coste_sin_agrupacion else 0.0

    resumen = {
        "Modo": nombre,
        "Circuitos_Validos": circuitos_validos,
        "Iteraciones_Paralelas": iteraciones,
        "Precio_Iteracion": PRECIO_ITERACION,
        "Coste_Sin_Agrupacion": coste_sin_agrupacion,
        "Coste_Con_Agrupacion": coste_con_agrupacion,
        "Ahorro": ahorro,
        "Ahorro_Porcentaje": porcentaje,
        "Filas_Sin_Qubits": filas_sin_qubits,
    }
    return resumen, detalle


def main():
    parser = argparse.ArgumentParser(
        description="Calcula el ahorro de costes de las ejecuciones paralelas en IBM Cloud."
    )
    parser.add_argument("--modo", choices=ARCHIVOS_MODOS, help="Procesa solamente el modo indicado.")
    args = parser.parse_args()

    SALIDA_DIR.mkdir(exist_ok=True)
    archivos = {args.modo: ARCHIVOS_MODOS[args.modo]} if args.modo else ARCHIVOS_MODOS
    resumenes = []
    detalles = []

    for nombre, ruta in archivos.items():
        if not ruta.exists():
            print(f"[AVISO] No existe el CSV de {nombre}: {ruta}")
            continue
        resumen, detalle = calcular_modo(nombre, ruta)
        resumenes.append(resumen)
        if not detalle.empty:
            detalles.append(detalle)
        print(
            f"[OK] {nombre}: {resumen['Circuitos_Validos']} circuitos, "
            f"{resumen['Iteraciones_Paralelas']} iteraciones, "
            f"ahorro={resumen['Ahorro']:.2f} ({resumen['Ahorro_Porcentaje']:.2f}%)"
        )

    if not resumenes:
        print("[AVISO] No se pudo procesar ningun CSV")
        return

    tabla_resumen = pd.DataFrame(resumenes)
    tabla_resumen.to_csv(SALIDA_DIR / "tabla_ahorro_por_modo.csv", index=False)
    tabla_resumen.to_latex(
        SALIDA_DIR / "tabla_ahorro_por_modo.tex",
        index=False,
        float_format="%.2f",
    )
    if detalles:
        pd.concat(detalles, ignore_index=True).to_csv(
            SALIDA_DIR / "detalle_costes_por_circuito.csv", index=False
        )

    print("\n--- TABLA DE AHORRO POR MODO ---")
    print(tabla_resumen.to_string(index=False))


if __name__ == "__main__":
    main()
