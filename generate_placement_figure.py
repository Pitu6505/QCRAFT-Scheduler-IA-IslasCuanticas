"""
Script para generar figura de la estrategia de 3 niveles de placement
Para artículo científico
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import networkx as nx
import numpy as np

def create_three_level_diagram():
    """
    Crea diagrama de flujo de la estrategia de 3 niveles
    """
    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')
    
    # Colores profesionales
    color_level1 = '#4A90E2'  # Azul
    color_level2 = '#7ED321'  # Verde
    color_level3 = '#F5A623'  # Naranja
    color_fail = '#D0021B'    # Rojo
    
    # ==================== INICIO ====================
    start_box = FancyBboxPatch(
        (5.5, 9), 3, 0.6,
        boxstyle="round,pad=0.1",
        edgecolor='black', facecolor='lightgray',
        linewidth=2
    )
    ax.add_patch(start_box)
    ax.text(7, 9.3, 'INICIO\nCircuito lógico + Hardware', 
            ha='center', va='center', fontsize=10, weight='bold')
    
    # Flecha a decisión size
    ax.annotate('', xy=(7, 8.2), xytext=(7, 9),
                arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    
    # ==================== DECISIÓN: SIZE > 4? ====================
    decision_size = mpatches.FancyBboxPatch(
        (5, 7.5), 4, 0.7,
        boxstyle="round,pad=0.05",
        edgecolor='black', facecolor='#FFE5B4',
        linewidth=2, linestyle='--'
    )
    ax.add_patch(decision_size)
    ax.text(7, 7.85, '¿Size > 4 qubits?', 
            ha='center', va='center', fontsize=9, weight='bold', style='italic')
    
    # Flecha SÍ a NIVEL 1
    ax.annotate('', xy=(2.5, 6.5), xytext=(5, 7.85),
                arrowprops=dict(arrowstyle='->', lw=2, color=color_level1))
    ax.text(3.5, 7.3, 'SÍ', fontsize=8, weight='bold', color=color_level1)
    
    # Flecha NO a NIVEL 2
    ax.annotate('', xy=(11.5, 6.5), xytext=(9, 7.85),
                arrowprops=dict(arrowstyle='->', lw=2, color='gray'))
    ax.text(10.5, 7.3, 'NO', fontsize=8, weight='bold', color='gray')
    
    # ==================== NIVEL 1: ISOMORFISMO ====================
    level1_box = FancyBboxPatch(
        (0.5, 5.5), 4, 1,
        boxstyle="round,pad=0.1",
        edgecolor=color_level1, facecolor='#E3F2FD',
        linewidth=3
    )
    ax.add_patch(level1_box)
    ax.text(2.5, 6.3, 'NIVEL 1', ha='center', fontsize=11, weight='bold', color=color_level1)
    ax.text(2.5, 6.0, 'Isomorfismo de Grafos', ha='center', fontsize=9, weight='bold')
    ax.text(2.5, 5.75, '(VF2 Algorithm)', ha='center', fontsize=7, style='italic')
    
    # Detalles Nivel 1
    ax.text(0.7, 5.45, '• Busca subgrafo idéntico', fontsize=7, va='top')
    ax.text(0.7, 5.25, '• Preserva topología 100%', fontsize=7, va='top')
    ax.text(0.7, 5.05, '• CERO SWAP gates', fontsize=7, va='top', weight='bold')
    
    # Flecha éxito Nivel 1
    ax.annotate('', xy=(2.5, 4.5), xytext=(2.5, 5.5),
                arrowprops=dict(arrowstyle='->', lw=2, color='green'))
    ax.text(3.0, 5.0, 'ÉXITO', fontsize=7, weight='bold', color='green')
    
    # Flecha fallo Nivel 1 → Nivel 2
    ax.annotate('', xy=(4.5, 4.8), xytext=(4.5, 5.5),
                arrowprops=dict(arrowstyle='->', lw=2, color=color_fail, linestyle='dashed'))
    ax.text(5.5, 5.1, 'FALLO', fontsize=7, weight='bold', color=color_fail)
    ax.annotate('', xy=(9.5, 4.8), xytext=(4.5, 4.8),
                arrowprops=dict(arrowstyle='->', lw=2, color=color_fail, linestyle='dashed'))
    
    # ==================== NIVEL 2: COMPONENTES ====================
    level2_box = FancyBboxPatch(
        (9.5, 3.8), 4, 1,
        boxstyle="round,pad=0.1",
        edgecolor=color_level2, facecolor='#F1F8E9',
        linewidth=3
    )
    ax.add_patch(level2_box)
    ax.text(11.5, 4.6, 'NIVEL 2', ha='center', fontsize=11, weight='bold', color=color_level2)
    ax.text(11.5, 4.3, 'Detección de Componentes', ha='center', fontsize=9, weight='bold')
    ax.text(11.5, 4.05, '(nx.connected_components)', ha='center', fontsize=7, style='italic')
    
    # Detalles Nivel 2
    ax.text(9.7, 3.75, '• Divide en subgrafos conectados', fontsize=7, va='top')
    ax.text(9.7, 3.55, '• Qubits aislados → mejor qubit', fontsize=7, va='top')
    ax.text(9.7, 3.35, '• Componentes → BFS individual', fontsize=7, va='top')
    
    # Flecha éxito Nivel 2
    ax.annotate('', xy=(11.5, 2.8), xytext=(11.5, 3.8),
                arrowprops=dict(arrowstyle='->', lw=2, color='green'))
    ax.text(12.0, 3.3, 'ÉXITO', fontsize=7, weight='bold', color='green')
    
    # Flecha fallo Nivel 2 → Nivel 3
    ax.annotate('', xy=(9.5, 3.1), xytext=(9.5, 3.8),
                arrowprops=dict(arrowstyle='->', lw=2, color=color_fail, linestyle='dashed'))
    ax.text(8.5, 3.5, 'FALLO', fontsize=7, weight='bold', color=color_fail)
    ax.annotate('', xy=(4.5, 3.1), xytext=(9.5, 3.1),
                arrowprops=dict(arrowstyle='->', lw=2, color=color_fail, linestyle='dashed'))
    
    # ==================== NIVEL 3: BFS ====================
    level3_box = FancyBboxPatch(
        (0.5, 2.1), 4, 1,
        boxstyle="round,pad=0.1",
        edgecolor=color_level3, facecolor='#FFF3E0',
        linewidth=3
    )
    ax.add_patch(level3_box)
    ax.text(2.5, 2.9, 'NIVEL 3', ha='center', fontsize=11, weight='bold', color=color_level3)
    ax.text(2.5, 2.6, 'BFS Optimizado', ha='center', fontsize=9, weight='bold')
    ax.text(2.5, 2.35, '(Breadth-First Search)', ha='center', fontsize=7, style='italic')
    
    # Detalles Nivel 3
    ax.text(0.7, 2.05, '• Explora desde nodos bajo ruido', fontsize=7, va='top')
    ax.text(0.7, 1.85, '• Encuentra grupos conectados', fontsize=7, va='top')
    ax.text(0.7, 1.65, '• Minimiza ruido total', fontsize=7, va='top')
    
    # Flecha éxito Nivel 3
    ax.annotate('', xy=(2.5, 1.1), xytext=(2.5, 2.1),
                arrowprops=dict(arrowstyle='->', lw=2, color='green'))
    ax.text(3.0, 1.6, 'ÉXITO', fontsize=7, weight='bold', color='green')
    
    # Flecha fallo Nivel 3 → ERROR
    ax.annotate('', xy=(4.5, 1.6), xytext=(4.5, 2.1),
                arrowprops=dict(arrowstyle='->', lw=2, color=color_fail, linestyle='dashed'))
    ax.text(5.5, 1.8, 'FALLO', fontsize=7, weight='bold', color=color_fail)
    ax.annotate('', xy=(11.5, 1.6), xytext=(4.5, 1.6),
                arrowprops=dict(arrowstyle='->', lw=2, color=color_fail, linestyle='dashed'))
    
    # ==================== SALIDAS ====================
    # Éxito
    success_box = FancyBboxPatch(
        (5.5, 0.5), 3, 0.6,
        boxstyle="round,pad=0.1",
        edgecolor='green', facecolor='#C8E6C9',
        linewidth=2
    )
    ax.add_patch(success_box)
    ax.text(7, 0.8, 'PLACEMENT EXITOSO', 
            ha='center', va='center', fontsize=9, weight='bold', color='green')
    
    # Convergencia de éxitos
    ax.annotate('', xy=(6.5, 0.8), xytext=(2.5, 1.1),
                arrowprops=dict(arrowstyle='->', lw=2, color='green'))
    ax.annotate('', xy=(7.5, 0.8), xytext=(11.5, 2.8),
                arrowprops=dict(arrowstyle='->', lw=2, color='green'))
    
    # Error
    error_box = FancyBboxPatch(
        (10, 0.5), 3, 0.6,
        boxstyle="round,pad=0.1",
        edgecolor=color_fail, facecolor='#FFCDD2',
        linewidth=2
    )
    ax.add_patch(error_box)
    ax.text(11.5, 0.8, 'ERROR: No placement', 
            ha='center', va='center', fontsize=9, weight='bold', color=color_fail)
    
    ax.annotate('', xy=(11.5, 1.1), xytext=(11.5, 1.6),
                arrowprops=dict(arrowstyle='->', lw=2, color=color_fail))
    
    # ==================== ESTADÍSTICAS ====================
    stats_box = FancyBboxPatch(
        (0.2, 0.05), 6, 0.35,
        boxstyle="round,pad=0.05",
        edgecolor='gray', facecolor='white',
        linewidth=1, linestyle=':'
    )
    ax.add_patch(stats_box)
    ax.text(0.4, 0.27, '📊 Reducción de SWAP gates:', fontsize=7, weight='bold')
    ax.text(0.4, 0.15, 'Nivel 1: ~58% | Nivel 2: ~35% | Nivel 3: ~15%', fontsize=6)
    
    plt.title('Estrategia de Placement de 3 Niveles Jerárquicos\nQCRAFT Quantum Scheduler', 
              fontsize=14, weight='bold', pad=20)
    
    plt.tight_layout()
    return fig

def create_example_comparison():
    """
    Crea ejemplos visuales de cada nivel con grafos
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # ==================== NIVEL 1: ISOMORFISMO ====================
    ax1 = axes[0]
    ax1.set_title('NIVEL 1: Isomorfismo de Grafos', fontsize=12, weight='bold', color='#4A90E2')
    
    # Circuito lógico
    logical = nx.Graph()
    logical.add_edges_from([(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)])
    pos_logical = {0: (0, 1), 1: (1, 1), 2: (1, 0), 3: (0, 0)}
    
    # Hardware (subgrafo)
    hardware = nx.Graph()
    hardware.add_edges_from([(10, 11), (11, 12), (12, 13), (13, 10), (10, 12)])
    pos_hardware = {10: (3, 1), 11: (4, 1), 12: (4, 0), 13: (3, 0)}
    
    nx.draw(logical, pos_logical, ax=ax1, node_color='lightblue', 
            node_size=800, with_labels=True, font_weight='bold', 
            edge_color='blue', width=2)
    nx.draw(hardware, pos_hardware, ax=ax1, node_color='lightgreen', 
            node_size=800, with_labels=True, font_weight='bold', 
            edge_color='green', width=2)
    
    # Flecha de mapeo
    ax1.annotate('', xy=(2.8, 0.5), xytext=(1.2, 0.5),
                 arrowprops=dict(arrowstyle='->', lw=3, color='red'))
    ax1.text(2, 0.6, 'Mapeo\n1:1', ha='center', fontsize=9, weight='bold', color='red')
    
    ax1.set_xlim(-0.5, 4.5)
    ax1.set_ylim(-0.5, 1.5)
    ax1.axis('off')
    
    # ==================== NIVEL 2: COMPONENTES ====================
    ax2 = axes[1]
    ax2.set_title('NIVEL 2: Componentes Desconectados', fontsize=12, weight='bold', color='#7ED321')
    
    # Circuito con componentes
    circuit_comp = nx.Graph()
    circuit_comp.add_edges_from([(0, 1), (1, 2)])  # Componente 1
    # Qubit 3 aislado
    circuit_comp.add_node(3)
    
    pos_comp = {0: (0, 1), 1: (0.5, 0.5), 2: (1, 1), 3: (2, 0.5)}
    
    colors = ['lightblue', 'lightblue', 'lightblue', 'yellow']
    nx.draw(circuit_comp, pos_comp, ax=ax2, node_color=colors, 
            node_size=800, with_labels=True, font_weight='bold', 
            edge_color='blue', width=2)
    
    # Anotaciones
    ax2.text(0.5, 1.3, 'Componente 1\n{0,1,2}', ha='center', fontsize=8, 
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
    ax2.text(2, 0.9, 'Aislado\n{3}', ha='center', fontsize=8,
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    ax2.set_xlim(-0.5, 2.5)
    ax2.set_ylim(-0.2, 1.5)
    ax2.axis('off')
    
    # ==================== NIVEL 3: BFS ====================
    ax3 = axes[2]
    ax3.set_title('NIVEL 3: BFS desde Mejor Qubit', fontsize=12, weight='bold', color='#F5A623')
    
    # Hardware con ruido
    hw_bfs = nx.Graph()
    edges_bfs = [(0, 1), (1, 2), (0, 3), (3, 4), (4, 5)]
    hw_bfs.add_edges_from(edges_bfs)
    
    pos_bfs = {0: (0, 1), 1: (1, 1), 2: (2, 1), 3: (0, 0), 4: (1, 0), 5: (2, 0)}
    noise_values = {0: 150, 1: 200, 2: 450, 3: 180, 4: 220, 5: 500}
    
    # Colorear por ruido
    node_colors = ['#90EE90' if noise_values[n] < 200 else 
                   '#FFD700' if noise_values[n] < 300 else '#FF6B6B' 
                   for n in hw_bfs.nodes()]
    
    nx.draw(hw_bfs, pos_bfs, ax=ax3, node_color=node_colors, 
            node_size=800, with_labels=True, font_weight='bold', 
            edge_color='gray', width=2)
    
    # Etiquetas de ruido
    for node, (x, y) in pos_bfs.items():
        ax3.text(x, y-0.2, f'{noise_values[node]}', ha='center', fontsize=7,
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Camino BFS seleccionado
    path = [0, 1, 4]
    path_edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
    nx.draw_networkx_edges(hw_bfs, pos_bfs, path_edges, ax=ax3,
                           edge_color='red', width=4, style='dashed')
    
    ax3.text(1, 1.4, 'Camino BFS: [0→1→4]\nRuido total: 570', 
             ha='center', fontsize=9, weight='bold',
             bbox=dict(boxstyle='round', facecolor='#FFE5B4', alpha=0.9))
    
    ax3.set_xlim(-0.5, 2.5)
    ax3.set_ylim(-0.5, 1.6)
    ax3.axis('off')
    
    plt.suptitle('Ejemplos Visuales de los 3 Niveles de Placement', 
                 fontsize=14, weight='bold', y=1.02)
    plt.tight_layout()
    return fig

if __name__ == '__main__':
    # Generar diagrama de flujo
    fig1 = create_three_level_diagram()
    fig1.savefig('placement_3_niveles_flowchart.png', dpi=300, bbox_inches='tight')
    print("✅ Generado: placement_3_niveles_flowchart.png")
    
    # Generar ejemplos visuales
    fig2 = create_example_comparison()
    fig2.savefig('placement_3_niveles_examples.png', dpi=300, bbox_inches='tight')
    print("✅ Generado: placement_3_niveles_examples.png")
    
    plt.show()
