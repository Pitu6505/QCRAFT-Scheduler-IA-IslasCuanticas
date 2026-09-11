import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import jensenshannon

BASE_DIR = Path(__file__).resolve().parent

def cargar_json(ruta):
    with open(ruta, 'r') as f:
        return json.load(f)

def calcular_hellinger(p, q):
    """Calcula la distancia de Hellinger entre dos distribuciones."""
    return np.sqrt(np.sum((np.sqrt(p) - np.sqrt(q)) ** 2)) / np.sqrt(2)

def procesar_distribuciones(dict_indiv, dict_multi):
    """Normaliza los conteos a probabilidades y unifica los bitstrings."""
    # Obtener todos los bitstrings únicos
    claves_todas = set(dict_indiv.keys()).union(set(dict_multi.keys()))
    claves_ordenadas = sorted(list(claves_todas))
    
    # Crear arrays de conteos rellenando con 0 si la clave no existe
    conteos_indiv = np.array([dict_indiv.get(k, 0) for k in claves_ordenadas], dtype=float)
    conteos_multi = np.array([dict_multi.get(k, 0) for k in claves_ordenadas], dtype=float)
    
    # Normalizar a probabilidades relativas
    prob_indiv = conteos_indiv / np.sum(conteos_indiv)
    prob_multi = conteos_multi / np.sum(conteos_multi)
    
    return prob_indiv, prob_multi

def comparar_ejecuciones(ruta_indiv, ruta_multi):
    datos_indiv = cargar_json(ruta_indiv)
    datos_multi = cargar_json(ruta_multi)
    
    # Convertir listas a diccionarios indexados por el nombre del circuito
    mapa_indiv = {item['circuit']: item['value'] for item in datos_indiv}
    mapa_multi = {item['circuit']: item['value'] for item in datos_multi}
    
    circuitos_comunes = set(mapa_indiv.keys()).intersection(set(mapa_multi.keys()))
    
    resultados = {}
    for circ in circuitos_comunes:
        p_indiv, p_multi = procesar_distribuciones(mapa_indiv[circ], mapa_multi[circ])
        
        # Calcular métricas
        hellinger = calcular_hellinger(p_indiv, p_multi)
        jsd = jensenshannon(p_indiv, p_multi)
        
        resultados[circ] = {
            'Hellinger': hellinger,
            'JSD': jsd
        }
        
    return resultados

def graficar_metricas(resultados, ruta_salida_figura=None):
    circuitos = list(resultados.keys())
    hellinger_vals = [resultados[c]['Hellinger'] for c in circuitos]
    jsd_vals = [resultados[c]['JSD'] for c in circuitos]
    max_valor = max(hellinger_vals + jsd_vals) if circuitos else 0.0
    
    x = np.arange(len(circuitos))
    width = 0.35  # Ajustado para dos barras

    # Use a broken y-axis to emphasize low values and still show that scale reaches 1.
    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        sharex=True,
        figsize=(14, 6),
        gridspec_kw={'height_ratios': [1, 3]}
    )

    # Draw the same bars on both axes; each axis shows a different y-range.
    ax_bottom.bar(x - width/2, hellinger_vals, width, label='Hellinger Distance', color='#1f77b4')
    ax_bottom.bar(x + width/2, jsd_vals, width, label='Jensen-Shannon Distance', color='#ff7f0e')
    ax_top.bar(x - width/2, hellinger_vals, width, color='#1f77b4')
    ax_top.bar(x + width/2, jsd_vals, width, color='#ff7f0e')

    # Dynamic cut: if values are below 0.9, show detail up to the max value and
    # keep a top segment (0.9 to 1.0) to indicate the full theoretical scale.
    if max_valor < 0.9:
        lim_inferior_superior = max(max_valor, 0.05)
        ax_bottom.set_ylim(0, lim_inferior_superior)
        ax_top.set_ylim(0.9, 1.0)

        # Create visual break between the two y-ranges.
        ax_top.spines['bottom'].set_visible(False)
        ax_bottom.spines['top'].set_visible(False)
        ax_top.tick_params(labeltop=False)
        ax_bottom.xaxis.tick_bottom()

        d = 0.012
        kwargs = dict(color='k', clip_on=False)
        ax_top.plot((-d, +d), (-d, +d), transform=ax_top.transAxes, **kwargs)
        ax_top.plot((1 - d, 1 + d), (-d, +d), transform=ax_top.transAxes, **kwargs)
        ax_bottom.plot((-d, +d), (1 - d, 1 + d), transform=ax_bottom.transAxes, **kwargs)
        ax_bottom.plot((1 - d, 1 + d), (1 - d, 1 + d), transform=ax_bottom.transAxes, **kwargs)
        ax_top.set_yticks([0.9, 1.0])
    else:
        # If values are already high, use a standard full scale and hide the top axis.
        ax_bottom.set_ylim(0, 1.0)
        ax_top.set_visible(False)

    ax_bottom.set_ylabel('Divergence Distance (0 to 1)')
    ax_bottom.set_xticks(x)
    ax_bottom.set_xticklabels(circuitos, rotation=45, ha="right")

    handles, labels = ax_bottom.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper right', bbox_to_anchor=(0.95, 0.9))
    fig.tight_layout()

    if ruta_salida_figura is not None:
        fig.savefig(ruta_salida_figura, dpi=300, bbox_inches='tight')

    plt.show()

def calcular_media_metricas(metricas):
    """Calcula la media de cada distancia sobre todos los circuitos analizados."""
    if not metricas:
        return {'Hellinger': 0.0, 'JSD': 0.0}

    return {
        'Hellinger': float(np.mean([vals['Hellinger'] for vals in metricas.values()])),
        'JSD': float(np.mean([vals['JSD'] for vals in metricas.values()]))
    }


def construir_salida_texto(metricas):
    lineas = []
    media = calcular_media_metricas(metricas)

    for circ, vals in metricas.items():
        lineas.append(f"Circuito: {circ}")
        lineas.append(f"  - Hellinger: {vals['Hellinger']:.4f}")
        lineas.append(f"  - JSD:       {vals['JSD']:.4f}")
        lineas.append("")

    lineas.append("Resumen global")
    lineas.append(f"  - Media Hellinger: {media['Hellinger']:.4f}")
    lineas.append(f"  - Media JSD:       {media['JSD']:.4f}")
    return "\n".join(lineas)

# --- Ejecución ---
ruta_individual = BASE_DIR / 'Individuales' / 'Fez' / 'EjecucionesIndividuales.json'
ruta_multiplexada = BASE_DIR / '40Circuitos_3D' / 'ModoDinamicoV2' / 'MedidaFirstIndependiente' / 'dynamic_local_initial_ramsey' / '2' / '2.json'
if not ruta_individual.exists():
    raise FileNotFoundError(f'No se encontró el archivo individual: {ruta_individual}')
if not ruta_multiplexada.exists():
    raise FileNotFoundError(f'No se encontró el archivo multiplexado: {ruta_multiplexada}')

metricas = comparar_ejecuciones(str(ruta_individual), str(ruta_multiplexada))
media_metricas = calcular_media_metricas(metricas)
ruta_carpeta_salida = ruta_multiplexada.parent
ruta_carpeta_salida.mkdir(parents=True, exist_ok=True)

ruta_figura = ruta_carpeta_salida / 'comparacion_metricas.png'
ruta_txt = ruta_carpeta_salida / 'comparacion_metricas.txt'

graficar_metricas(metricas, ruta_figura)

salida_texto = construir_salida_texto(metricas)
ruta_txt.write_text(salida_texto, encoding='utf-8')

print(f'Grafica guardada en: {ruta_figura}')
print(f'Salida de metricas guardada en: {ruta_txt}')
print(f"Media total Hellinger: {media_metricas['Hellinger']:.4f}")
print(f"Media total JSD:       {media_metricas['JSD']:.4f}")

# Imprimir resultados por consola
print(salida_texto)