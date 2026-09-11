import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import re
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# 1. Configuración de los archivos (Ajusta las rutas a tus archivos reales)
# Formato: "Nombre del Modo": ("ruta_al_txt.txt", "ruta_al_csv.csv", "Categoria")
archivos_modos = {
    # Modos Estáticos Locales
    "Local Completo": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "completo" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "completo" / "resultados_experimentacion.csv", "Estático Local"),
    "Local DD": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "dd" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "dd" / "resultados_experimentacion.csv", "Estático Local"),
    "Local Robust": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "Robust" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "Robust" / "resultados_experimentacion.csv", "Estático Local"),
    "Local Standard": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "Standard" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "Standard" / "resultados_experimentacion.csv", "Estático Local"),
    "Local T1_decay": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "t1_decay" / "ResultadosDistancias.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoLocal" / "t1_decay" / "resultados_experimentacion.csv", "Estático Local"),
    
    # Modos Estáticos Globales
    "Global Completo": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "completo" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "completo" / "resultados_experimentacion.csv", "Estático Global"),
    "Global DD": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "dd" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "dd" / "resultados_experimentacion.csv", "Estático Global"),
    "Global Robust": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "Robust" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "Robust" / "resultados_experimentacion.csv", "Estático Global"),
    "Global Standard": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "Standard" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "Standard" / "resultados_experimentacion.csv", "Estático Global"),
    "Global T1_decay": (BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "t1_decay" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoEstatico" / "ModoGlobal" / "t1_decay" / "resultados_experimentacion.csv", "Estático Global"),

    # Modos Dinámicos
    "Dynamic T1": (BASE_DIR / "40Circuitos_3D" / "ModoDinamicoV2" / "MedidaInFirst" / "dynamic_t1" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoDinamicoV2" / "MedidaInFirst" / "dyNamic_t1" / "resultados_experimentacion.csv", "Dinámico"),
    "Dynamic Ramsey": (BASE_DIR / "40Circuitos_3D" / "ModoDinamicoV2" / "MedidaInFirst" / "dynamic_ramsey" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoDinamicoV2" / "MedidaInFirst" / "dynamic_ramsey" / "resultados_experimentacion.csv", "Dinámico"),
    "Dynamic Local T1": (BASE_DIR / "40Circuitos_3D" / "ModoDinamicoV2" / "MedidaInMiddle" / "dynamic_local_t1" / "comparacion_metricas.txt", BASE_DIR / "40Circuitos_3D" / "ModoDinamicoV2" / "MedidaInMiddle" / "dynamic_local_t1" / "resultados_experimentacion.csv", "Dinámico"),
    "Dynamic Local Ramsey": (BASE_DIR / "40Circuitos_3D" / "ModoDinamicoV2" / "MedidaInMiddle" / "dynamic_local_ramsey" / "comparacion_metricas.txt", BASE_DIR /"40Circuitos_3D" /"ModoDinamicoV2"/"MedidaInMiddle"/"dynamic_local_ramsey"/"resultados_experimentacion.csv", "Dinámico"),
}
def procesar_txt(ruta_txt):
    """Extrae la media de Hellinger y JSD del txt"""
    if not os.path.exists(ruta_txt): return None, None
    hellinger_vals = []
    with open(ruta_txt, 'r') as f:
        for line in f:
            if line.strip().startswith("- Hellinger:"):
                hellinger_vals.append(float(line.split(":")[1].strip()))
    return sum(hellinger_vals)/len(hellinger_vals) if hellinger_vals else None

def procesar_csv(ruta_csv):
    """Extrae la tasa de supervivencia o descartes del csv"""
    if not os.path.exists(ruta_csv): return None
    # AJUSTA AQUI: el separador (sep) y el nombre de la columna de supervivencia o descarte
    df = pd.read_csv(ruta_csv, sep=';') 
    
    columna_supervivencia = 'Supervivencia_(%)' # Cambia esto por el nombre real de tu columna
    if columna_supervivencia in df.columns:
        return df[columna_supervivencia].mean()
    return None

# 3. Procesamiento masivo
resultados = []
for modo, (txt, csv, categoria) in archivos_modos.items():
    media_hellinger = procesar_txt(txt)
    media_supervivencia = procesar_csv(csv)
    
    if media_hellinger is not None and media_supervivencia is not None:
        resultados.append({
            "Modo": modo,
            "Categoría": categoria,
            "Divergencia Hellinger (Media)": media_hellinger,
            "Tasa de Supervivencia (%)": media_supervivencia
        })

df_resultados = pd.DataFrame(resultados)

# 4. Mostrar la tabla para pasarla a LaTeX
print("--- TABLA RESUMEN PARA EL ARTÍCULO ---")
print(df_resultados.to_string(index=False))

# 5. Generar la gráfica Scatter Plot
plt.figure(figsize=(10, 7))
sns.set_theme(style="whitegrid")

scatter = sns.scatterplot(
    data=df_resultados, 
    x="Tasa de Supervivencia (%)", 
    y="Divergencia Hellinger (Media)", 
    hue="Categoría", 
    style="Categoría",
    s=150, # Tamaño de los puntos
    palette="deep"
)

# Añadir etiquetas a cada punto para saber qué modo es
for i in range(df_resultados.shape[0]):
    plt.text(
        df_resultados["Tasa de Supervivencia (%)"][i] + 0.5, 
        df_resultados["Divergencia Hellinger (Media)"][i], 
        df_resultados["Modo"][i], 
        horizontalalignment='left', 
        size='small', 
        color='black', 
        weight='semibold'
    )

plt.title('Trade-off: Fidelidad de Estado vs Tasa de Supervivencia', fontsize=14, pad=15)
plt.xlabel('Tasa de Supervivencia Media (%)', fontsize=12)
plt.ylabel('Divergencia Hellinger Media', fontsize=12)
# Invertir el eje Y si quieres que "Mejor fidelidad (0)" esté arriba. 
# Por defecto 0 está abajo, lo cual es intuitivo (menor error = mejor).
plt.tight_layout()
plt.savefig("grafica_tradeoff_fidelidad_supervivencia.png", dpi=300)
plt.show()