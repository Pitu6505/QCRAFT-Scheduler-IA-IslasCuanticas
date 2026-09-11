import pandas as pd
import glob
import re
from pathlib import Path

# 1. Cargar todos los CSV de resultados desde 40Circuitos_3D
BASE_DIR = Path(__file__).resolve().parent
PATRON_CSV = str(BASE_DIR / '40Circuitos_3D' / '**' / 'resultados_experimentacion.csv')

archivos_csv = glob.glob(PATRON_CSV, recursive=True)
if not archivos_csv:
    raise FileNotFoundError(f'No se encontraron CSV con el patron: {PATRON_CSV}')

lista_dfs = [pd.read_csv(archivo, sep=';') for archivo in archivos_csv]
df_total = pd.concat(lista_dfs, ignore_index=True)

archivo_complejidad = BASE_DIR / '40Circuitos_3D' / 'complejidad_circuitos.csv'
df_complejidad = pd.read_csv(archivo_complejidad, sep=';')

# 2. Asegurarnos de que tenemos las columnas necesarias
# Columnas reales en los CSV de resultados_experimentacion.csv
columna_hora = 'Fecha_Hora'  # Identifica cada lote/iteracion multiplexada
columna_circuito = 'Circuito_Nombre'
columna_qubits = 'Qubits_Logicos'

columnas_requeridas = [columna_hora, columna_circuito]
faltantes = [col for col in columnas_requeridas if col not in df_total.columns]
if faltantes:
    raise ValueError(f'Faltan columnas requeridas en los CSV: {faltantes}. Columnas detectadas: {list(df_total.columns)}')

if columna_qubits not in df_complejidad.columns:
    raise ValueError(f'Falta la columna requerida en el CSV de complejidad: {columna_qubits}')

df_total = df_total.merge(
    df_complejidad[[columna_circuito, columna_qubits]],
    on=columna_circuito,
    how='left',
    validate='many_to_one'
)

if df_total[columna_qubits].isna().any():
    if 'Layout_Circuito' not in df_total.columns:
        circuitos_faltantes = df_total.loc[df_total[columna_qubits].isna(), columna_circuito].unique().tolist()
        raise ValueError(f'No se encontraron qubits para los circuitos: {circuitos_faltantes}')

    # Algunos circuitos no aparecen en el CSV de complejidad; su layout conserva
    # el número de qubits usados y permite completar esos registros.
    qubits_desde_layout = df_total['Layout_Circuito'].map(
        lambda layout: len(re.findall(r'\d+', str(layout)))
    )
    df_total[columna_qubits] = df_total[columna_qubits].fillna(qubits_desde_layout)

if df_total[columna_qubits].isna().any() or (df_total[columna_qubits] <= 0).any():
    raise ValueError('Todos los circuitos deben tener un número de qubits positivo')

# --- AQUÍ VA TU FÓRMULA DE LA METODOLOGÍA ---
precio_iteracion = 1.6

def calcular_coste_circuito(fila, total_qubits_iteracion):
    """
    Asigna el precio de la iteración al circuito según sus qubits.
    """
    return precio_iteracion * (fila[columna_qubits] / total_qubits_iteracion)

def calcular_coste_multiplexado(grupo_iteracion):
    """
    Calcula el coste de la iteración conjunta, pagado una sola vez.
    """
    return precio_iteracion
# ---------------------------------------------

# 3. Agrupar por la hora de ejecución (cada grupo es una iteración multiplexada)
agrupado = df_total.groupby(columna_hora)

resultados_economicos = []

for hora, grupo in agrupado:
    num_circuitos = len(grupo)
    total_qubits_iteracion = grupo[columna_qubits].sum()
    grupo = grupo.copy()
    grupo['Coste_Secuencial'] = grupo.apply(
        calcular_coste_circuito,
        axis=1,
        total_qubits_iteracion=total_qubits_iteracion
    )
    coste_secuencial_total = grupo['Coste_Secuencial'].sum()
    coste_multiplexado = calcular_coste_multiplexado(grupo)
    ahorro_absoluto = coste_secuencial_total - coste_multiplexado
    ahorro_porcentaje = (ahorro_absoluto / coste_secuencial_total) * 100 if coste_secuencial_total > 0 else 0
    
    resultados_economicos.append({
        'Iteración (Hora)': hora,
        'Circuitos Empaquetados': num_circuitos,
        'Coste Secuencial ($)': coste_secuencial_total,
        'Coste Multiplexado ($)': coste_multiplexado,
        'Ahorro Absoluto ($)': ahorro_absoluto,
        'Ahorro (%)': ahorro_porcentaje
    })

# 4. Crear el DataFrame final y mostrar el resumen
df_economia = pd.DataFrame(resultados_economicos)

print("--- RESUMEN ECONÓMICO GLOBAL ---")
coste_total_secuencial = df_economia['Coste Secuencial ($)'].sum()
coste_total_multiplexado = df_economia['Coste Multiplexado ($)'].sum()
ahorro_total = coste_total_secuencial - coste_total_multiplexado
porcentaje_ahorro_total = (ahorro_total / coste_total_secuencial) * 100

print(f"Coste Total si fuera Secuencial: ${coste_total_secuencial:.2f}")
print(f"Coste Total Multiplexado: ${coste_total_multiplexado:.2f}")
print(f"AHORRO TOTAL LOGRADO: ${ahorro_total:.2f} ({porcentaje_ahorro_total:.2f}%)")

# Para imprimir las 5 iteraciones con más ahorro a modo de ejemplo
print("\n--- TOP 5 ITERACIONES CON MAYOR AHORRO ---")
print(df_economia.sort_values('Ahorro Absoluto ($)', ascending=False).head().to_string(index=False))