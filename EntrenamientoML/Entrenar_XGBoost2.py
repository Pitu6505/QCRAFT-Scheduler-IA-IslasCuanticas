import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multioutput import ClassifierChain
from sklearn.metrics import classification_report, accuracy_score
from xgboost import XGBClassifier
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
import networkx as nx

# Intento de cargar la topología real de IBM Fez
try:
    from qiskit_ibm_runtime.fake_provider import FakeFez
    backend_fez = FakeFez()
    edges_fez = backend_fez.coupling_map.get_edges()
except ImportError:
    print("⚠️ No se pudo cargar FakeFez. Usa get_backend_graph('ibm_fez').")
    edges_fez = []

def cargar_y_aumentar_dataset(ruta_json, factor_aumento=5, std_ruido=0.008):
    X_originales, densidad_originales, y_originales, layouts_originales, victimas_ordenadas = [], [], [], [], []

    with open(ruta_json, 'r') as f:
        for linea in f:
            if not linea.strip(): continue
            datos = json.loads(linea)
            X_originales.append(datos['vector_25d'])
            densidad_originales.append(datos['total_circuitos'])
            nombres_limpios = [n.replace('.qasm', '') for n in datos['victimas_concurrentes']]
            
            y_originales.append(nombres_limpios)
            layouts_originales.append(datos.get('layout_global', []))
            # Guardamos el orden original de inyección para colorear correctamente los nodos
            victimas_ordenadas.append(nombres_limpios)

    X_aug, densidad_aug, y_aug, layouts_aug, victimas_aug = [], [], [], [], []

    for vec, dens, label, layout, vics in zip(X_originales, densidad_originales, y_originales, layouts_originales, victimas_ordenadas):
        X_aug.append(vec); densidad_aug.append(dens); y_aug.append(label); layouts_aug.append(layout); victimas_aug.append(vics)
        
        for _ in range(factor_aumento - 1):
            ruido = np.random.normal(0, std_ruido, size=len(vec))
            vec_sintetico = np.clip(np.array(vec) + ruido, 0.0, 1.0).round(4).tolist()
            X_aug.append(vec_sintetico); densidad_aug.append(dens); y_aug.append(label); layouts_aug.append(layout); victimas_aug.append(vics)

    return X_aug, densidad_aug, y_aug, layouts_aug, victimas_aug, len(X_originales)

# ==============================================================================
# 1. CARGA, ENTRENAMIENTO Y PREDICCIÓN
# ==============================================================================
print("⚙️ Cargando dataset y configurando entorno...")
X_raw, densidad_raw, y_raw, layouts_raw, victimas_raw, n_reales = cargar_y_aumentar_dataset("dataset_radar_distribuido.json")

X = pd.DataFrame(X_raw, columns=[f'radar_{i}' for i in range(25)])
X['densidad_qubits'] = densidad_raw

mlb = MultiLabelBinarizer()
y = mlb.fit_transform(y_raw)
clases = mlb.classes_

# Pasamos también los layouts y el orden de víctimas al split
X_train, X_test, y_train, y_test, layouts_train, layouts_test, vic_train, vic_test = train_test_split(
    X, y, layouts_raw, victimas_raw, test_size=0.2, random_state=42
)

print("🧠 Entrenando modelo ClassifierChain...")
xgb_base = XGBClassifier(
    objective='binary:logistic', eval_metric='logloss',
    n_estimators=100, learning_rate=0.03, max_depth=4,
    subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.2, random_state=42
)
modelo_crosstalk = ClassifierChain(xgb_base, order='random', random_state=42)
modelo_crosstalk.fit(X_train, y_train)

# ==============================================================================
# 2. ANIMACIÓN TOPOLÓGICA CON COLORES POR ALGORITMO Y LEYENDA
# ==============================================================================
print("\n🎬 Generando animación topológica (GIF)...")

G_topology = nx.Graph()
if edges_fez:
    G_topology.add_edges_from(edges_fez)
else:
    G_topology = nx.convert_node_labels_to_integers(nx.grid_2d_graph(13, 12))

# Layout anticolisión: Fuerza los nodos a separarse como imanes (k ajusta la repulsión)
pos = nx.spring_layout(G_topology, k=0.18, iterations=150, seed=42)

sentinelas_idx = [5, 6, 7, 8, 9, 40, 41, 42, 43, 44, 71, 72, 73, 74, 75, 85, 86, 87, 88, 89, 146, 147, 148, 149, 150]
etiquetas = {nodo: nodo for nodo in G_topology.nodes()}

num_frames = 10
np.random.seed(42)
indices_prueba = np.random.choice(len(X_test), num_frames, replace=False)

todas_las_tasas = X_test.iloc[indices_prueba].values[:, :25].flatten()
norm = mcolors.Normalize(vmin=min(todas_las_tasas), vmax=max(todas_las_tasas))
cmap_termico = cm.get_cmap('magma')

# Diccionario de colores para los algoritmos víctima
colores_victimas = {
    'grover': "#D0FF00", # Cian
    'qaoa': '#39FF14',   # Verde Neón
    'qft': '#FF00FF',    # Magenta
    'vqe': "#00FFFB"     # Naranja
}

fig, ax = plt.subplots(figsize=(16, 12)) # Lienzo más grande para evitar sobrepisos
plt.subplots_adjust(right=0.75) # Deja espacio a la derecha para la leyenda

def update(frame):
    ax.clear()
    idx = indices_prueba[frame]
    ejemplo = X_test.iloc[[idx]]
    vector_termico = ejemplo.values[0][:25]
    layout_actual = layouts_test[idx]
    orden_victimas_reales = vic_test[idx]
    
    # 1. Asignar los nodos a cada circuito basado en su tamaño (ej. qiskit_9 -> 9 nodos)
    nodos_enteros = [n for n in layout_actual if isinstance(n, int)]
    mapa_nodos_algoritmo = {}
    puntero = 0
    
    for vic in orden_victimas_reales:
        try:
            # Extrae el número del final del nombre del archivo
            size = int(vic.split('_')[-1])
        except ValueError:
            size = 10 # Fallback por seguridad
            
        mapa_nodos_algoritmo[vic] = nodos_enteros[puntero : puntero + size]
        puntero += size

    # 2. Inferencias del modelo
    pred_bin = modelo_crosstalk.predict(ejemplo)[0]
    algoritmos_pred = mlb.inverse_transform(np.array([pred_bin]))[0]
    algoritmos_real = mlb.inverse_transform(y_test[[idx]])[0]

    # 3. Asignación de colores nodo a nodo
    node_colors = []
    vector_idx = 0
    
    for nodo in G_topology.nodes():
        if nodo in sentinelas_idx:
            node_colors.append(cmap_termico(norm(vector_termico[vector_idx])))
            vector_idx += 1
        else:
            color_asignado = '#E0E0E0' # Gris inactivo por defecto
            for vic_name, nodos_vic in mapa_nodos_algoritmo.items():
                if nodo in nodos_vic:
                    # Busca qué algoritmo es para darle su color
                    for clave, hex_color in colores_victimas.items():
                        if clave in vic_name:
                            color_asignado = hex_color
                            break
            node_colors.append(color_asignado)

    # 4. Dibujar Grafo (Nodos más pequeños y fuente diminuta)
    nx.draw_networkx_edges(G_topology, pos, alpha=0.3, edge_color='gray', ax=ax)
    nx.draw_networkx_nodes(G_topology, pos, node_size=180, node_color=node_colors, edgecolors='black', linewidths=0.5, ax=ax)
    nx.draw_networkx_labels(G_topology, pos, labels=etiquetas, font_size=5, font_color='black', ax=ax)
    
    # 5. Generar la Leyenda Dinámica
    leyenda_elementos = []
    for vic_name in orden_victimas_reales:
        color = '#E0E0E0'
        for clave, hex_color in colores_victimas.items():
            if clave in vic_name: color = hex_color
        leyenda_elementos.append(mpatches.Patch(color=color, label=f'Activo: {vic_name.split("_")[0]}'))
        
    leyenda_elementos.append(mpatches.Patch(color='#E0E0E0', label='Qubit Inactivo / Vacío'))
    
    # Colocamos la leyenda fija a la derecha, fuera del grafo
    ax.legend(handles=leyenda_elementos, loc='center left', bbox_to_anchor=(1.05, 0.8), 
              title="Distribución Física", fontsize=10, title_fontsize=12, framealpha=0.9)

    # 6. Textos e Información
    pred_str = ", ".join([p.split("_")[0] for p in algoritmos_pred]) if algoritmos_pred else "Ninguno"
    real_str = ", ".join([r.split("_")[0] for r in algoritmos_real]) if algoritmos_real else "Ninguno"

    ax.set_title(f'Inspección {frame + 1}/10: Detección de Diafonía Cuántica', fontsize=16, weight='bold', pad=10)
    texto = f"Verdad Fundamental: {real_str}\nInferencia XGBoost (Crosstalk): {pred_str}"
    
    borde_color = 'green' if set(algoritmos_pred) == set(algoritmos_real) else 'red'
    ax.text(0.5, -0.05, texto, ha='center', va='center', transform=ax.transAxes, 
            fontsize=13, bbox=dict(facecolor='white', alpha=0.9, edgecolor=borde_color, boxstyle='round,pad=0.5', linewidth=2.5))
    ax.axis('off')

ani = animation.FuncAnimation(fig, update, frames=num_frames, interval=3000, repeat=True)

# Añadimos la barra de calor
sm = plt.cm.ScalarMappable(cmap=cmap_termico, norm=norm)
cbar = plt.colorbar(sm, ax=ax, shrink=0.6, pad=0.02, location='right')
cbar.set_label('Tasa de Error (Crosstalk Leakage)', rotation=270, labelpad=20, fontsize=11)

ani.save('auditoria_crosstalk_animada.gif', writer='pillow', dpi=150)
print("✅ Animación generada con éxito ('auditoria_crosstalk_animada.gif').")
plt.close()