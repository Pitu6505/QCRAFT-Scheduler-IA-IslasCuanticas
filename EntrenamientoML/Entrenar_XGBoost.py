import json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multioutput import ClassifierChain
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    multilabel_confusion_matrix,
    precision_score,
)
from xgboost import XGBClassifier
import matplotlib.pyplot as plt
import seaborn as sns

USAR_DATOS_SINTETICOS = True
FACTOR_AUMENTO_SINTETICO = 5
RUIDO_SINTETICO_STD = 0.008


def cargar_dataset(ruta_json):
    """Carga las muestras originales del dataset."""
    X_originales = []
    densidad_originales = []
    y_originales = []
    layouts_originales = []
    victimas_originales = []

    with open(ruta_json, 'r') as f:
        for linea in f:
            if not linea.strip():
                continue
            datos = json.loads(linea)
            X_originales.append(datos['vector_25d'])
            densidad_originales.append(datos['total_circuitos'])
            layouts_originales.append(datos.get('layout_global', []))
            victimas = [
                nombre.replace('.qasm', '')
                for nombre in datos['victimas_concurrentes']
            ]
            victimas_originales.append(victimas)
            familias = []
            for nombre in victimas:
                familia = nombre.split('_indep_qiskit_', 1)[0]
                if familia.startswith('grover-'):
                    familia = 'grover'
                familias.append(familia)
            y_originales.append(familias)

    return (
        X_originales,
        densidad_originales,
        y_originales,
        layouts_originales,
        victimas_originales,
        len(X_originales),
    )


def aumentar_datos_entrenamiento(X_train, y_train, factor_aumento=5, std_ruido=0.008):
    """Añade ruido a los 25 radares de entrenamiento, manteniendo las etiquetas."""
    if factor_aumento < 1:
        raise ValueError("factor_aumento debe ser al menos 1")

    rng = np.random.default_rng(42)
    X_aug = []
    y_aug = []

    for vector, etiquetas in zip(X_train.to_numpy(dtype=float), y_train):
        X_aug.append(vector)
        y_aug.append(etiquetas)

        for _ in range(factor_aumento - 1):
            vector_sintetico = vector.copy()
            ruido = rng.normal(0, std_ruido, size=25)
            vector_sintetico[:25] = np.clip(
                vector_sintetico[:25] + ruido, 0.0, 1.0
            ).round(4)
            X_aug.append(vector_sintetico)
            y_aug.append(etiquetas)

    return (
        pd.DataFrame(X_aug, columns=X_train.columns),
        np.asarray(y_aug),
    )

# --- INICIO DEL FLUJO ---
print("Loading dataset...")
X_raw, densidad_raw, y_raw, layouts_raw, victimas_raw, n_reales = cargar_dataset(
    "dataset_radar_distribuido.json"
)

# 3. Construcción del DataFrame
X = pd.DataFrame(X_raw, columns=[f'radar_{i}' for i in range(25)])
X['densidad_qubits'] = densidad_raw

# 4. Binarización de etiquetas
mlb = MultiLabelBinarizer()
y = mlb.fit_transform(y_raw)
clases = mlb.classes_

print(f"Detected families: {', '.join(clases)}")

# 5. Split before augmentation to prevent synthetic copies entering the test set
X_train, X_test, y_train, y_test, layouts_train, layouts_test, victimas_train, victimas_test = train_test_split(
    X,
    y,
    layouts_raw,
    victimas_raw,
    test_size=0.2,
    random_state=42,
)
num_entrenamiento_original = len(X_train)
if USAR_DATOS_SINTETICOS:
    X_train, y_train = aumentar_datos_entrenamiento(
        X_train,
        y_train,
        factor_aumento=FACTOR_AUMENTO_SINTETICO,
        std_ruido=RUIDO_SINTETICO_STD,
    )
    estado_aumento = "synthetic augmentation enabled"
else:
    estado_aumento = "synthetic augmentation disabled"

print(
    f"Original samples: {n_reales} | "
    f"Training samples: {num_entrenamiento_original} -> {len(X_train)} "
    f"({estado_aumento}) | Test samples: {len(X_test)}"
)

# 6. Configuración regularizada de XGBoost
print("\nTraining regularized XGBoost ClassifierChain...")
xgb_base = XGBClassifier(
    objective='binary:logistic',
    eval_metric='logloss',
    n_estimators=100,
    learning_rate=0.03,          # Moderate learning rate to reduce overfitting
    max_depth=4,                 # Limit tree depth
    subsample=0.8,
    colsample_bytree=0.8,
    reg_alpha=0.1,               # L1 regularization
    reg_lambda=1.2,              # L2 regularization
    random_state=42
)

# ClassifierChain passes earlier class predictions as features to later classifiers.
modelo_crosstalk = ClassifierChain(xgb_base, order='random', random_state=42)
modelo_crosstalk.fit(X_train, y_train)

# 7. Evaluación
y_pred = modelo_crosstalk.predict(X_test)
exact_acc = accuracy_score(y_test, y_pred)
precision_macro = precision_score(y_test, y_pred, average='macro', zero_division=0)

print("\nClassification report:\n")
print(classification_report(y_test, y_pred, target_names=clases, zero_division=0))
print(f"Macro precision (average across families): {precision_macro:.2%}")
print(f"Exact-match accuracy (all labels correct): {exact_acc:.2%}")

# Save the trained model together with the label encoder and input feature order.
ruta_modelo = Path(__file__).resolve().parent / "modelo_crosstalk_familias.joblib"
joblib.dump(
    {
        "model": modelo_crosstalk,
        "label_binarizer": mlb,
        "feature_names": X.columns.tolist(),
        "families": clases.tolist(),
    },
    ruta_modelo,
)
print(f"Trained model saved to: {ruta_modelo}")

# 8. Prueba de inferencia a ciegas en test
print("\nBlind inference on a test sample:")
idx_sample = 0
ejemplo = X_test.iloc[[idx_sample]]
pred_bin = modelo_crosstalk.predict(ejemplo)[0]

reales_names = mlb.inverse_transform(y_test[[idx_sample]])[0]
pred_names = mlb.inverse_transform(np.array([pred_bin]))[0]

print(f" - Actual families:    {reales_names}")
print(f" - Predicted families: {pred_names}")

# ==============================================================================
# 1. MATRIZ DE CONFUSIÓN MULTI-ETIQUETA (Eficacia de Detección por Algoritmo)
# ==============================================================================
mcm = multilabel_confusion_matrix(y_test, y_pred)
n_columnas = 2
n_filas = (len(clases) + n_columnas - 1) // n_columnas
fig, axes = plt.subplots(n_filas, n_columnas, figsize=(16, 6 * n_filas))
axes = np.atleast_1d(axes).ravel()

# Paleta de colores científicos
cmap = sns.light_palette("navy", as_cmap=True)

for i, (matrix, name) in enumerate(zip(mcm, clases)):
    sns.heatmap(matrix, annot=True, fmt='d', cmap=cmap, cbar=False, ax=axes[i],
                annot_kws={"size": 22, "weight": "bold"},
                xticklabels=['Absent', 'Present'],
                yticklabels=['Absent', 'Present'],
                square=True)
    axes[i].set_xlabel(f'Predicted {name}', fontsize=19, labelpad=12)
    axes[i].set_ylabel(f'Actual {name}', fontsize=19, labelpad=12)
    axes[i].tick_params(axis='both', labelsize=17, pad=8)

for ax in axes[len(clases):]:
    ax.set_visible(False)

fig.tight_layout()
plt.savefig('matriz_confusion_crosstalk.pdf', dpi=300, bbox_inches='tight') # Formato PDF para LaTeX
plt.show()

# ==============================================================================
# 2. IMPORTANCIA DE LOS RADARES (Explicabilidad del Modelo - XAI)
# ==============================================================================
# Extraemos el peso (Information Gain) de las características en la cadena XGBoost
# Como son 4 modelos en cadena, promediamos la importancia de las 26 variables originales
importancias = np.mean([est.feature_importances_[:26] for est in modelo_crosstalk.estimators_], axis=0)
nombres_features = [f'Sentinel v{i%5} (Zone {i//5})' for i in range(25)] + ['Logical qubit density']

# Ordenamos de mayor a menor relevancia
indices = np.argsort(importancias)[::-1]
importancias_ordenadas = importancias[indices]
nombres_ordenados = [nombres_features[i] for i in indices]

plt.figure(figsize=(15, 10))
sns.barplot(x=importancias_ordenadas[:12], y=nombres_ordenados[:12], palette='magma')
plt.xlabel('Feature importance (XGBoost)', fontsize=19, labelpad=12)
plt.ylabel('Feature', fontsize=19, labelpad=12)
plt.xticks(fontsize=16)
plt.yticks(fontsize=16)
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
print("\nGenerating topological heatmap animation (10 test samples)...")

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
indices_prueba = np.random.choice(
    len(X_test), min(num_frames, len(X_test)), replace=False
)

# Normalizador global basado en los datos de esas 10 muestras
todas_las_tasas = X_test.iloc[indices_prueba].values[:, :25].flatten()
norm = mcolors.Normalize(vmin=min(todas_las_tasas), vmax=max(todas_las_tasas))
cmap_termico = cm.get_cmap('magma')

fig, ax = plt.subplots(figsize=(12, 8))
colores_victimas = {
    'grover': '#D4A017',
    'qaoa': '#2CA02C',
    'qft': '#C23B9A',
    'vqe': '#17A2B8',
}
colores_fondo = '#E0E0E0'
fig.subplots_adjust(right=0.70, bottom=0.16)

# 3. Función de actualización para cada fotograma del GIF
def update(frame):
    ax.clear()
    idx = indices_prueba[frame]
    ejemplo = X_test.iloc[[idx]]
    vector_termico = ejemplo.values[0][:25]
    layout_actual = layouts_test[idx]
    victimas_actuales = victimas_test[idx]

    nodos_circuitos = [
        nodo for nodo in layout_actual if isinstance(nodo, int)
    ]
    nodos_por_victima = []
    puntero = 0
    for nombre in victimas_actuales:
        try:
            tamano_circuito = int(nombre.rsplit('_', 1)[1])
        except (IndexError, ValueError) as error:
            raise ValueError(
                f"Cannot determine qubit count for victim circuit: {nombre}"
            ) from error
        nodos_por_victima.append(
            (
                nombre,
                nodos_circuitos[puntero:puntero + tamano_circuito],
            )
        )
        puntero += tamano_circuito

    if puntero != len(nodos_circuitos):
        raise ValueError(
            "The victim circuit sizes do not match the physical layout "
            f"for test sample {idx}."
        )
    
    # Inferencia
    pred_bin = modelo_crosstalk.predict(ejemplo)[0]
    algoritmos_predichos = mlb.inverse_transform(np.array([pred_bin]))[0]
    algoritmos_reales = mlb.inverse_transform(y_test[[idx]])[0]
    
    pred_str = ", ".join(algoritmos_predichos) if algoritmos_predichos else "None"
    real_str = ", ".join(algoritmos_reales) if algoritmos_reales else "None"

    # Asignación de colores
    node_colors = []
    vector_idx = 0
    for nodo in G_topology.nodes():
        if nodo in sentinelas_idx:
            node_colors.append(cmap_termico(norm(vector_termico[vector_idx])))
            vector_idx += 1
        else:
            color_victima = colores_fondo
            for nombre, nodos in nodos_por_victima:
                if nodo in nodos:
                    familia = nombre.split('_indep_qiskit_', 1)[0]
                    if familia.startswith('grover-'):
                        familia = 'grover'
                    color_victima = colores_victimas.get(
                        familia, colores_fondo
                    )
                    break
            node_colors.append(color_victima)

    # Dibujado del grafo
    nx.draw_networkx_edges(G_topology, pos, alpha=0.3, edge_color='gray', ax=ax)
    nx.draw_networkx_nodes(G_topology, pos, node_size=350, node_color=node_colors, edgecolors='black', linewidths=0.5, ax=ax)
    nx.draw_networkx_labels(G_topology, pos, labels=etiquetas, font_size=7, font_color='white', ax=ax)

    leyenda_elementos = [
        plt.Line2D(
            [0],
            [0],
            marker='o',
            color='w',
            markerfacecolor=color,
            markeredgecolor='black',
            markersize=9,
            label=family.upper(),
        )
        for family, color in colores_victimas.items()
    ]
    leyenda_elementos.append(
        plt.Line2D(
            [0],
            [0],
            marker='o',
            color='w',
            markerfacecolor=colores_fondo,
            markeredgecolor='black',
            markersize=9,
            label='Unused qubit',
        )
    )
    ax.legend(
        handles=leyenda_elementos,
        loc='upper left',
        bbox_to_anchor=(1.02, 1.0),
        framealpha=0.9,
    )
    
    texto = f"Actual: {real_str}\nPredicted: {pred_str}"
    
    # Colorear el borde del texto: Verde si acierta todo, Rojo si falla algo
    borde_color = 'green' if set(algoritmos_predichos) == set(algoritmos_reales) else 'red'
    ax.text(0.5, -0.05, texto, ha='center', va='center', transform=ax.transAxes, 
            fontsize=12, bbox=dict(facecolor='white', alpha=0.9, edgecolor=borde_color, boxstyle='round,pad=0.5', linewidth=2))
    
    ax.axis('off')

# 4. Compilación y exportación de la animación
ani = animation.FuncAnimation(
    fig, update, frames=len(indices_prueba), interval=2000, repeat=True
)

# Barra de color estática
sm = plt.cm.ScalarMappable(cmap=cmap_termico, norm=norm)
cax = fig.add_axes([0.92, 0.22, 0.02, 0.56])
cbar = fig.colorbar(sm, cax=cax)
cbar.set_label('Quantum error rate', rotation=270, labelpad=20)

# Guarda el GIF (Requiere tener la librería 'pillow' instalada: pip install pillow)
ani.save('auditoria_crosstalk_animada.gif', writer='pillow', dpi=150)
print("Animation saved as 'auditoria_crosstalk_animada.gif'")
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