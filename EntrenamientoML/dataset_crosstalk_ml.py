import json
import networkx as nx
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import classification_report
import joblib

# ==========================================
# 1. CARGA DEL GRAFO TOPOLÓGICO
# ==========================================
# G = nx.Graph(get_backend_graph("ibm_fez")[0]) # <-- Usa esto en el futuro
G = nx.grid_2d_graph(13, 12) 
G = nx.convert_node_labels_to_integers(G)

# Configuración del entrenamiento.
USAR_DATOS_SINTETICOS = True
MULTIPLICADOR_SINTETICO = 8
RUIDO_SINTETICO_STD = 0.015

def obtener_qubits_totales(layout_dict):
    return layout_dict['data'] + layout_dict['sentinel']

def calcular_distancia_minima(layout_victima, layout_global, grafo):
    if len(layout_global) <= 1:
        return 10 
    
    nodos_victima = set(obtener_qubits_totales(layout_victima))
    nodos_agresores = set()
    
    for circuito in layout_global:
        nodos_circuito = set(obtener_qubits_totales(circuito))
        if nodos_circuito != nodos_victima:
            nodos_agresores.update(nodos_circuito)
            
    distancia_min = float('inf')
    for nv in nodos_victima:
        for na in nodos_agresores:
            try:
                dist = nx.shortest_path_length(grafo, source=nv, target=na)
                if dist < distancia_min:
                    distancia_min = dist
            except nx.NetworkXNoPath:
                continue
    return distancia_min

# ==========================================
# 2. GENERADOR SINTÉTICO DUAL
# ==========================================
def aumentar_datos_sinteticos(X, y_ataque, y_algo, multiplicador=8, ruido_std=0.015):
    """Aumenta los datos manteniendo la coherencia de ambas etiquetas."""
    X_aug, y_atq_aug, y_alg_aug = [], [], []
    
    for i in range(len(X)):
        vector = X.iloc[i].values
        lbl_ataque = y_ataque.iloc[i]
        lbl_algo = y_algo.iloc[i]
        
        # Guardar original
        X_aug.append(vector)
        y_atq_aug.append(lbl_ataque)
        y_alg_aug.append(lbl_algo)
        
        # Generar clones con ruido térmico
        for _ in range(multiplicador):
            ruido = np.random.normal(0, ruido_std, size=len(vector))
            vector_modificado = np.clip(vector + ruido, 0.0, 1.0)
            
            X_aug.append(vector_modificado)
            y_atq_aug.append(lbl_ataque)
            y_alg_aug.append(lbl_algo)
            
    return pd.DataFrame(X_aug, columns=X.columns), pd.Series(y_atq_aug), pd.Series(y_alg_aug)

# ==========================================
# 3. PARSEO DE LOS DATASETS
# ==========================================
def cargar_dataset(ruta_dataset, nombre_origen):
    datos_procesados = []

    with ruta_dataset.open(encoding='utf-8') as f:
        for line in f:
            registro = json.loads(line)
            if 'layout_global_batch' not in registro:
                continue

            vector = registro['tasas_error_v0_v4']
            distancia = calcular_distancia_minima(
                registro['layout'],
                registro['layout_global_batch'],
                G,
            )

            es_ataque = 1 if distancia < 5 else 0
            nombre_crudo = registro['circuito'].split('_')[0]
            algoritmo = nombre_crudo.replace('-noancilla', '')

            datos_procesados.append({
                'algoritmo': algoritmo,
                'v0': vector[0],
                'v1': vector[1],
                'v2': vector[2],
                'v3': vector[3],
                'v4': vector[4],
                'distancia': distancia,
                'label_ataque': es_ataque,
                'origen_dataset': nombre_origen,
            })

    return datos_procesados


print("📥 Cargando datasets JSON...")
directorio_proyecto = Path(__file__).resolve().parents[2]
datos_procesados = []

datasets = [
    ('dataset_crosstalk_ml.json', 'crosstalk'),
    ('EjecucionesTopologicamenteDiferente.json', 'topologia'),
]

for nombre_dataset, nombre_origen in datasets:
    ruta_dataset = directorio_proyecto / nombre_dataset
    datos_procesados.extend(cargar_dataset(ruta_dataset, nombre_origen))

df = pd.DataFrame(datos_procesados)
print(f"✅ Muestras originales cargadas: {len(df)}")
print("📊 Muestras por dataset:")
print(df['origen_dataset'].value_counts().to_string())
print("📊 Muestras por algoritmo:")
print(df['algoritmo'].value_counts().to_string())

# ==========================================
# 4. PREPARACIÓN DE ENTRENAMIENTO (SPLIT)
# ==========================================
X = df[['v0', 'v1', 'v2', 'v3', 'v4']]
y_ataque = df['label_ataque']
y_algoritmo = df['algoritmo']

# División estratificada para asegurar que todos los algoritmos estén en el test
X_train, X_test, y_train_atq, y_test_atq, y_train_alg, y_test_alg = train_test_split(
    X, y_ataque, y_algoritmo, test_size=0.2, random_state=42, stratify=y_algoritmo
)

if USAR_DATOS_SINTETICOS:
    print("🧬 Aumentando datos de entrenamiento con ruido NISQ...")
    X_train_model, y_train_atq_model, y_train_alg_model = aumentar_datos_sinteticos(
        X_train,
        y_train_atq,
        y_train_alg,
        multiplicador=MULTIPLICADOR_SINTETICO,
        ruido_std=RUIDO_SINTETICO_STD,
    )
else:
    print("📊 Entrenando únicamente con las muestras originales...")
    X_train_model = X_train
    y_train_atq_model = y_train_atq
    y_train_alg_model = y_train_alg

# ==========================================
# 5. MODELO 1: DETECTOR DE ATAQUE (BINARIO)
# ==========================================
print("\n🛡️ Entrenando Modelo 1: Detector de Ataque/Interferencia...")
clf_ataque = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
clf_ataque.fit(X_train_model, y_train_atq_model)

pred_ataque = clf_ataque.predict(X_test)
print("\n--- REPORTE MODELO 1 (DETECCIÓN) ---")
print(classification_report(y_test_atq, pred_ataque, target_names=["Normal (0)", "Ataque (1)"]))

# ==========================================
# 6. MODELO 2: CLASIFICADOR FORENSE (MULTICLASE)F
# ==========================================
print("\n🔎 Entrenando Modelo 2: Identificador Forense de Algoritmos...")
clf_algoritmo = ExtraTreesClassifier(
    n_estimators=300,
    max_depth=8,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)
clf_algoritmo.fit(X_train_model, y_train_alg_model)

pred_algoritmo = clf_algoritmo.predict(X_test)
print("\n--- REPORTE MODELO 2 (IDENTIFICACIÓN DE FIRMA) ---")
print(classification_report(y_test_alg, pred_algoritmo))

# ==========================================
# 7. SIMULACIÓN DE PIPELINE EN PRODUCCIÓN
# ==========================================
print("\n🚀 SIMULACIÓN DE LA TUBERÍA EN TIEMPO REAL:")
print("-" * 50)
for i in range(5): # Probamos con 5 vectores aleatorios del set de pruebas
    vector_prueba = X_test.iloc[i].values
    algoritmo_real = y_test_alg.iloc[i]
    ataque_real = "Ataque" if y_test_atq.iloc[i] == 1 else "Normal"
    
    # Fase 1: El vector entra al sistema de detección
    vector_df = pd.DataFrame([vector_prueba], columns=['v0', 'v1', 'v2', 'v3', 'v4'])
    es_ataque_pred = clf_ataque.predict(vector_df)[0]
    causante = clf_algoritmo.predict(vector_df)[0]
    firma_limpia = clf_algoritmo.predict(vector_df)[0]    
    if es_ataque_pred == 1:
        # Fase 2: Si es un ataque, llamamos al modelo forense para saber qué lo causó
        causante = clf_algoritmo.predict(vector_df)[0]
        estado = f"🚨 ALERTA: Interferencia detectada. Causante más probable: [{causante.upper()}]"
    else:
        # Si es normal, predecimos de quién es la firma limpia
        firma_limpia = clf_algoritmo.predict(vector_df)[0]
        estado = f"✅ Ejecución limpia. Firma validada: [{firma_limpia.upper()}]"
        
    print(f"Vector: {[round(v, 3) for v in vector_prueba]}")
    print(f"  -> Realidad: {ataque_real} | {algoritmo_real.upper()}")
    print(f"  -> Pipeline: {estado}\n")

joblib.dump(clf_ataque, 'modelo_detector_ataque.pkl')
joblib.dump(clf_algoritmo, 'modelo_forense_algoritmo.pkl')

print("💾 Modelos exportados correctamente listos para producción.")