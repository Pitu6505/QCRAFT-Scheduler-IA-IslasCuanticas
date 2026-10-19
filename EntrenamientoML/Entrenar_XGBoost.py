import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multioutput import ClassifierChain
from sklearn.metrics import classification_report, accuracy_score, multilabel_confusion_matrix
from xgboost import XGBClassifier
import matplotlib.pyplot as plt
import seaborn as sns

def cargar_y_aumentar_dataset(ruta_json, factor_aumento=5, std_ruido=0.008):
    """
    Carga el dataset real y genera muestras sintéticas añadiendo ruido gaussiano
    controlado a los vectores de error 25D.
    """
    X_originales = []
    densidad_originales = []
    y_originales = []

    # 1. Carga de datos reales
    with open(ruta_json, 'r') as f:
        for linea in f:
            if not linea.strip():
                continue
            datos = json.loads(linea)
            X_originales.append(datos['vector_25d'])
            densidad_originales.append(datos['total_circuitos'])
            nombres_limpios = [n.replace('.qasm', '') for n in datos['victimas_concurrentes']]
            y_originales.append(nombres_limpios)

    X_aug = []
    densidad_aug = []
    y_aug = []

    # 2. Generación sintética
    for vec, dens, label in zip(X_originales, densidad_originales, y_originales):
        # Muestra real original
        X_aug.append(vec)
        densidad_aug.append(dens)
        y_aug.append(label)

        # Copias sintéticas con variación gaussiana
        for _ in range(factor_aumento - 1):
            ruido = np.random.normal(0, std_ruido, size=len(vec))
            vec_sintetico = np.clip(np.array(vec) + ruido, 0.0, 1.0).round(4).tolist()
            
            X_aug.append(vec_sintetico)
            densidad_aug.append(dens)
            y_aug.append(label)

    return X_aug, densidad_aug, y_aug, len(X_originales)

# --- INICIO DEL FLUJO ---
print("⚙️ Cargando y aumentando dataset con física sintética...")
X_raw, densidad_raw, y_raw, n_reales = cargar_y_aumentar_dataset(
    "dataset_radar_distribuido.json", 
    factor_aumento=5,   # Multiplica x5 las muestras (245 -> ~1225)
    std_ruido=0.008     # Varianza equivalente a ~1000-4096 shots
)

# 3. Construcción del DataFrame
X = pd.DataFrame(X_raw, columns=[f'radar_{i}' for i in range(25)])
X['densidad_qubits'] = densidad_raw

# 4. Binarización de etiquetas
mlb = MultiLabelBinarizer()
y = mlb.fit_transform(y_raw)
clases = mlb.classes_

print(f"📊 Muestras originales: {n_reales} | Muestras tras Data Augmentation: {len(X)}")
print(f"🎯 Clases detectadas: {', '.join(clases)}")

# 5. División de datos (Estratificada por distribución multi-etiqueta)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 6. Configuración regularizada de XGBoost
print("\n🧠 Entrenando ClassifierChain con XGBoost regularizado...")
xgb_base = XGBClassifier(
    objective='binary:logistic',
    eval_metric='logloss',
    n_estimators=100,
    learning_rate=0.03,      # Gradiente moderado para evitar memorización
    max_depth=4,             # Control de profundidad de árbol
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,           # Regularización L1
    reg_lambda=1.2,          # Regularización L2
    random_state=42
)

# ClassifierChain pasa las predicciones de una clase como características de la siguiente
modelo_crosstalk = ClassifierChain(xgb_base, order='random', random_state=42)
modelo_crosstalk.fit(X_train, y_train)

# 7. Evaluación
y_pred = modelo_crosstalk.predict(X_test)
exact_acc = accuracy_score(y_test, y_pred)

print("\n✅ Reporte de Clasificación (Dataset Aumentado):\n")
print(classification_report(y_test, y_pred, target_names=clases, zero_division=0))
print(f"🎯 Exact Match Accuracy (Acierto Conjunto Perfecto): {exact_acc:.2%}")

# 8. Prueba de inferencia a ciegas en test
print("\n🔍 Prueba de Inferencia a Ciegas sobre muestra sintética de validación:")
idx_sample = 0
ejemplo = X_test.iloc[[idx_sample]]
pred_bin = modelo_crosstalk.predict(ejemplo)[0]

reales_names = mlb.inverse_transform(y_test[[idx_sample]])[0]
pred_names = mlb.inverse_transform(np.array([pred_bin]))[0]

print(f" - Algoritmos reales ejecutándose: {reales_names}")
print(f" - El modelo deduce que son:      {pred_names}")

# ==============================================================================
# 1. MATRIZ DE CONFUSIÓN MULTI-ETIQUETA (Eficacia de Detección por Algoritmo)
# ==============================================================================
mcm = multilabel_confusion_matrix(y_test, y_pred)
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.ravel()

# Paleta de colores científicos
cmap = sns.light_palette("navy", as_cmap=True)

for i, (matrix, name) in enumerate(zip(mcm, clases)):
    sns.heatmap(matrix, annot=True, fmt='d', cmap=cmap, cbar=False, ax=axes[i],
                annot_kws={"size": 14, "weight": "bold"},
                xticklabels=['Ausente (Pred)', 'Presente (Pred)'],
                yticklabels=['Ausente (Real)', 'Presente (Real)'])
    axes[i].set_title(f'Detector: {name}', fontsize=12, pad=10)
    axes[i].set_xlabel('Predicción de XGBoost', fontsize=10)
    axes[i].set_ylabel('Verdad Fundamental', fontsize=10)

plt.suptitle('Matrices de Confusión de Ataque de Canal Lateral (Crosstalk)', fontsize=16, weight='bold')
plt.tight_layout()
plt.savefig('matriz_confusion_crosstalk.pdf', dpi=300, bbox_inches='tight') # Formato PDF para LaTeX
plt.show()

# ==============================================================================
# 2. IMPORTANCIA DE LOS RADARES (Explicabilidad del Modelo - XAI)
# ==============================================================================
# Extraemos el peso (Information Gain) de las características en la cadena XGBoost
# Como son 4 modelos en cadena, promediamos la importancia de las 26 variables originales
importancias = np.mean([est.feature_importances_[:26] for est in modelo_crosstalk.estimators_], axis=0)
nombres_features = [f'Centinela v{i%5} (Zona {i//5})' for i in range(25)] + ['Densidad Lógica (Qubits)']

# Ordenamos de mayor a menor relevancia
indices = np.argsort(importancias)[::-1]
importancias_ordenadas = importancias[indices]
nombres_ordenados = [nombres_features[i] for i in indices]

plt.figure(figsize=(12, 8))
sns.barplot(x=importancias_ordenadas[:12], y=nombres_ordenados[:12], palette='magma')
plt.title('Top 12 Nodos Topológicos con Mayor Fuga de Información (Information Gain)', fontsize=14, weight='bold')
plt.xlabel('Relevancia en la Clasificación (Puntuación XGBoost)', fontsize=12)
plt.ylabel('Característica', fontsize=12)
plt.grid(axis='x', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig('importancia_radares.pdf', dpi=300, bbox_inches='tight')
plt.show()

import networkx as nx
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ==============================================================================
# 3. ANIMACIÓN DEL MAPA DE CALOR TOPOLÓGICO (GIF - 10 PRUEBAS)
# ==============================================================================
print("\n🎬 Generando animación topológica (GIF) de 10 pruebas a ciegas...")

# 1. Reconstruimos la topología base y extraemos coordenadas reales
G_grid = nx.grid_2d_graph(13, 12)
# Anclamos la posición geométrica: (x, -y) para que dibuje una matriz perfecta
pos_geometrica_original = {nodo: (nodo[0], -nodo[1]) for nodo in G_grid.nodes()}

# Convertimos a enteros para que coincida con tu formato
G_topology = nx.convert_node_labels_to_integers(G_grid)
# Mapeamos las coordenadas geométricas a los nuevos nodos enteros
pos = {i: pos_geometrica_original[old_node] for i, old_node in enumerate(G_grid.nodes())}

sentinelas_idx = [5, 6, 7, 8, 9, 40, 41, 42, 43, 44, 71, 72, 73, 74, 75, 85, 86, 87, 88, 89, 146, 147, 148, 149, 150]
etiquetas = {nodo: nodo for nodo in sentinelas_idx}

# 2. Seleccionamos aleatoriamente 10 muestras de test
num_frames = 10
np.random.seed(42) # Fijo para repetibilidad, puedes quitarlo
indices_prueba = np.random.choice(len(X_test), num_frames, replace=False)

# Normalizador global basado en los datos de esas 10 muestras
todas_las_tasas = X_test.iloc[indices_prueba].values[:, :25].flatten()
norm = mcolors.Normalize(vmin=min(todas_las_tasas), vmax=max(todas_las_tasas))
cmap_termico = cm.get_cmap('magma')

fig, ax = plt.subplots(figsize=(10, 8))

# 3. Función de actualización para cada fotograma del GIF
def update(frame):
    ax.clear()
    idx = indices_prueba[frame]
    ejemplo = X_test.iloc[[idx]]
    vector_termico = ejemplo.values[0][:25]
    
    # Inferencia
    pred_bin = modelo_crosstalk.predict(ejemplo)[0]
    algoritmos_predichos = mlb.inverse_transform(np.array([pred_bin]))[0]
    algoritmos_reales = mlb.inverse_transform(y_test[[idx]])[0]
    
    pred_str = ", ".join(algoritmos_predichos) if algoritmos_predichos else "Ninguno"
    real_str = ", ".join(algoritmos_reales) if algoritmos_reales else "Ninguno"

    # Asignación de colores
    node_colors = []
    vector_idx = 0
    for nodo in G_topology.nodes():
        if nodo in sentinelas_idx:
            node_colors.append(cmap_termico(norm(vector_termico[vector_idx])))
            vector_idx += 1
        else:
            node_colors.append('#E0E0E0') # Gris claro para víctimas y huecos

    # Dibujado del grafo
    nx.draw_networkx_edges(G_topology, pos, alpha=0.3, edge_color='gray', ax=ax)
    nx.draw_networkx_nodes(G_topology, pos, node_size=350, node_color=node_colors, edgecolors='black', linewidths=0.5, ax=ax)
    nx.draw_networkx_labels(G_topology, pos, labels=etiquetas, font_size=7, font_color='white', ax=ax)
    
    # Textos dinámicos
    ax.set_title(f'Radar Cuántico: Inspección {frame + 1}/10', fontsize=16, weight='bold', pad=10)
    texto = f"Verdad Fundamental: {real_str}\nPredicción XGBoost: {pred_str}"
    
    # Colorear el borde del texto: Verde si acierta todo, Rojo si falla algo
    borde_color = 'green' if set(algoritmos_predichos) == set(algoritmos_reales) else 'red'
    ax.text(0.5, -0.05, texto, ha='center', va='center', transform=ax.transAxes, 
            fontsize=12, bbox=dict(facecolor='white', alpha=0.9, edgecolor=borde_color, boxstyle='round,pad=0.5', linewidth=2))
    
    ax.axis('off')

# 4. Compilación y exportación de la animación
ani = animation.FuncAnimation(fig, update, frames=num_frames, interval=2000, repeat=True)

# Barra de color estática
sm = plt.cm.ScalarMappable(cmap=cmap_termico, norm=norm)
cbar = plt.colorbar(sm, ax=ax, shrink=0.7, pad=0.05)
cbar.set_label('Tasa de Error Cuántico', rotation=270, labelpad=20)

# Guarda el GIF (Requiere tener la librería 'pillow' instalada: pip install pillow)
ani.save('auditoria_crosstalk_animada.gif', writer='pillow', dpi=150)
print("✅ Animación guardada como 'auditoria_crosstalk_animada.gif'")
plt.close()

# import networkx as nx
# import matplotlib.cm as cm
# import matplotlib.colors as mcolors

# # ==============================================================================
# # 3. VISUALIZACIÓN DEL MAPA DE CALOR TOPOLÓGICO (IBM FEZ - 156 QUBITS)
# # ==============================================================================
# print("\n🎨 Generando Mapa de Calor Topológico del Ataque...")

# # 1. Reconstruimos la topología base (usamos el grid 13x12 = 156 qubits)
# G_topology = nx.grid_2d_graph(13, 12)
# G_topology = nx.convert_node_labels_to_integers(G_topology)

# # 2. Definimos las posiciones de los 25 centinelas según tu layout de QCRAFT
# sentinelas_idx = [5, 6, 7, 8, 9, 40, 41, 42, 43, 44, 71, 72, 73, 74, 75, 85, 86, 87, 88, 89, 146, 147, 148, 149, 150]

# # 3. Tomamos el vector de la muestra de prueba y la predicción del modelo
# vector_termico = ejemplo.values[0][:25] # Excluimos la densidad, solo los 25 sensores
# algoritmos_predichos_str = ", ".join(pred_names) if len(pred_names) > 0 else "Ninguno (Ruido de fondo)"
# algoritmos_reales_str = ", ".join(reales_names)

# # 4. Asignamos colores a los nodos
# node_colors = []
# # Creamos un normalizador para mapear la tasa de error (ej. de 0.20 a 0.55) a colores
# norm = mcolors.Normalize(vmin=min(vector_termico), vmax=max(vector_termico))
# cmap_termico = cm.get_cmap('magma') # Paleta termográfica

# vector_idx = 0
# for nodo in G_topology.nodes():
#     if nodo in sentinelas_idx:
#         # Si es un centinela, le damos el color correspondiente a su tasa de error
#         color = cmap_termico(norm(vector_termico[vector_idx]))
#         node_colors.append(color)
#         vector_idx += 1
#     else:
#         # Si es un qubit de las víctimas o vacío, lo dejamos en gris oscuro
#         node_colors.append('#D3D3D3')

# # 5. Dibujamos el grafo
# plt.figure(figsize=(12, 10))
# pos = nx.spring_layout(G_topology, seed=42) # Layout estético para el chip

# nx.draw_networkx_edges(G_topology, pos, alpha=0.2, edge_color='gray')
# nx.draw_networkx_nodes(G_topology, pos, node_size=300, node_color=node_colors, edgecolors='black', linewidths=0.5)

# # Añadimos etiquetas solo a los centinelas para saber cuál es cuál
# etiquetas = {nodo: nodo for nodo in sentinelas_idx}
# nx.draw_networkx_labels(G_topology, pos, labels=etiquetas, font_size=8, font_color='white')

# # 6. Leyenda y Títulos (Explicabilidad XAI)
# sm = plt.cm.ScalarMappable(cmap=cmap_termico, norm=norm)
# cbar = plt.colorbar(sm, ax=plt.gca(), shrink=0.7, pad=0.05)
# cbar.set_label('Tasa de Error Cuántico (Crosstalk Leakage)', rotation=270, labelpad=20, fontsize=12)

# plt.title('Radar Distribuido: Huella Térmica en IBM Fez (156 qubits)', fontsize=16, weight='bold')
# texto_prediccion = (
#     f"Verdad Fundamental: {algoritmos_reales_str}\n"
#     f"Inferencia XGBoost: {algoritmos_predichos_str}"
# )
# plt.text(0.5, -0.05, texto_prediccion, ha='center', va='center', transform=plt.gca().transAxes, 
#          fontsize=12, bbox=dict(facecolor='white', alpha=0.8, edgecolor='black', boxstyle='round,pad=0.5'))

# plt.axis('off')
# plt.tight_layout()
# plt.savefig('mapa_topologico_ataque.pdf', dpi=300, bbox_inches='tight')
# plt.show()