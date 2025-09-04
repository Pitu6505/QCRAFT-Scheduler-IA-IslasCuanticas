import time
import random
import uuid
import os
import sys
from collections import deque
from config import CAPACIDAD_MAXIMA, MAX_ITEMS, NUM_SAMPLES, FORCE_THRESHOLD

# Aumentamos el límite de recursión (aunque en DP iterativo no se use recursividad profunda)
sys.setrecursionlimit(10000)

#################################
# 1. Función para generar elementos de la cola
#################################
def generar_cola(num_elementos):
    """
    Genera una cola de elementos.
    
    Cada elemento es una tupla (id, valor, count) donde:
      - id: identificador único (generado con uuid4)
      - valor: entero aleatorio entre 1 y 12 (qBits)
      - count: contador de prioridad, que inicia en 0.
    
    Retorna:
      deque: cola de elementos.
    """
    cola = deque()
    for _ in range(num_elementos):
        identificador = str(uuid.uuid4())
        valor = random.randint(1, 12)
        count = 0
        cola.append((identificador, valor, count))
    return cola

#################################
# 2. Función iterativa tipo Knapsack (programación dinámica)
#################################
def iterative_knapsack(items, capacity):
    """
    Resuelve el problema de la mochila 0/1 usando programación dinámica iterativa.
    
    Cada ítem es una tupla (id, valor, count); se utiliza solo 'valor' para la suma.
    
    Retorna una tupla (suma, subset) donde:
      - suma: suma total de valores del subset seleccionado.
      - subset: lista de ítems seleccionados.
    """
    n = len(items)
    # Crear la tabla dp (n+1 x capacity+1)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    
    for i in range(1, n + 1):
        _, valor, _ = items[i - 1]
        for w in range(capacity + 1):
            if valor <= w:
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - valor] + valor)
            else:
                dp[i][w] = dp[i - 1][w]
    
    # Reconstruir la solución óptima
    selected = []
    w = capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(items[i - 1])
            w -= items[i - 1][1]
    selected.reverse()
    return dp[n][capacity], selected

#################################
# 3. Función de optimización usando programación dinámica
#################################
def optimizar_espacio_dinamico(queue, capacidad, forced_threshold=FORCE_THRESHOLD):
    """
    Optimiza la selección de elementos de la cola utilizando:
      1. Selección forzada: se eligen aquellos elementos cuyo count >= forced_threshold y que quepan.
      2. Sobre los elementos restantes se aplica el algoritmo de mochila (iterative_knapsack)
         para obtener la combinación óptima sin exceder la capacidad restante.
    
    Retorna:
      - selected: lista de elementos seleccionados (tuplas (id, valor, count))
      - total_valor: suma total de los valores seleccionados.
      - nueva_cola: cola actualizada (sin los elementos seleccionados).
    """
    forced_selected = []
    capacidad_restante = capacidad
    remaining = []
    
    # 1. Selección forzada
    for item in queue:
        ident, valor, count = item
        if count >= forced_threshold and valor <= capacidad_restante:
            forced_selected.append(item)
            capacidad_restante -= valor
        else:
            remaining.append(item)
    
    # 2. Aplicamos el knapsack iterativo a los elementos restantes
    rec_value, rec_subset = iterative_knapsack(remaining, capacidad_restante)
    
    # Combinar ambas selecciones
    selected = forced_selected + rec_subset
    total_valor = sum(item[1] for item in selected)
    
    # Actualizamos la cola eliminando los elementos seleccionados (por id)
    selected_ids = {item[0] for item in selected}
    nueva_cola = [item for item in queue if item[0] not in selected_ids]
    
    return selected, total_valor, nueva_cola

#################################
# 4. Función interactiva para procesar la cola usando DP iterativo
#################################
def procesar_cola_dinamico(cola, capacidad, forced_threshold=FORCE_THRESHOLD):
    """
    Procesa la cola de forma interactiva utilizando programación dinámica.
    
    Formato:
      - Se pregunta al usuario cuántas veces desea procesar la cola.
          * Si se ingresa 0, se procesan iteraciones hasta vaciar la cola.
      - En cada iteración se incrementa el contador (count) de cada elemento.
      - Se muestra el estado de la cola (id, valor, count).
      - Se procesa la cola usando optimizar_espacio_dinamico.
      - **Si se selecciona la opción 0, en cada iteración se añaden automáticamente 3 nuevos elementos a la cola.**
      - Al finalizar, se permite al usuario añadir manualmente nuevos elementos.
    """
    iter_global = 0
    num_iteraciones = int(input("¿Cuántas veces deseas procesar la cola? (0 para vaciarla automáticamente, en cuyo caso se inyectan 3 nuevos elementos cada iteración): "))
    
    if num_iteraciones == 0:
        # Modo vaciado automático: procesar iteraciones hasta vaciar la cola
        while cola:
            # Incrementar count de cada elemento
            cola = deque([(ident, valor, count + 1) for (ident, valor, count) in cola])
            iter_global += 1
            print(f"\nIteración {iter_global} - Estado de la cola:")
            for item in cola:
                ident, valor, count = item
                # print(f"  Elemento {ident}: Valor = {valor}, Iteraciones = {count}")
            
            # **Cada iteración se añaden 3 nuevos elementos automáticamente**
            print("\n--- Se añaden 3 nuevos elementos a la cola automáticamente ---")
            nuevos_elementos = generar_cola(3)
            for elem in nuevos_elementos:
                cola.append(elem)
            
            selected, total_valor, nueva_cola = optimizar_espacio_dinamico(list(cola), capacidad, forced_threshold)
            print(f"\nProcesando cola en iteración {iter_global}:")
            print(f"  Cola actual (IDs): {[item[0] for item in nueva_cola]}")
            print(f"  Elementos seleccionados (IDs): {[item[0] for item in selected]}")
            print(f"  Valor total obtenido: {total_valor}")
            cola = deque(nueva_cola)
        print("La cola se ha vaciado.")
    else:
        # Modo iterativo: procesar el número de iteraciones indicado por el usuario
        for _ in range(num_iteraciones):
            cola = deque([(ident, valor, count + 1) for (ident, valor, count) in cola])
            iter_global += 1
            print(f"\nIteración {iter_global} - Estado de la cola:")
            for item in cola:
                ident, valor, count = item
                print(f"  Elemento {ident}: Valor = {valor}, Iteraciones = {count}")
            
            # En modo iterativo, se puede decidir no añadir elementos automáticamente,
            # pero si se desea, se puede incorporar la misma línea que en el modo 0.
            # Por ejemplo, descomenta las siguientes líneas para inyectar nuevos elementos:
            # print("\n--- Se añaden 3 nuevos elementos a la cola automáticamente ---")
            # nuevos_elementos = generar_cola(3)
            # for elem in nuevos_elementos:
            #     cola.append(elem)
            
            selected, total_valor, nueva_cola = optimizar_espacio_dinamico(list(cola), capacidad, forced_threshold)
            print(f"\nProcesando cola en iteración {iter_global}:")
            print(f"  Cola actual (IDs): {[item[0] for item in nueva_cola]}")
            print(f"  Elementos seleccionados (IDs): {[item[0] for item in selected]}")
            print(f"  Valor total obtenido: {total_valor}")
            cola = deque(nueva_cola)
        if cola:
            añadir = input("\n¿Deseas añadir nuevos elementos a la cola? (s/n): ").lower()
            if añadir == 's':
                nuevos = input("Introduce los pares id:valor separados por espacios: ").split()
                for par in nuevos:
                    try:
                        ident, valor_str = par.split(':')
                        valor = int(valor_str)
                        cola.append((ident, valor, 0))
                    except Exception as e:
                        print(f"Error al procesar '{par}': {e}")
            procesar_cola_dinamico(cola, capacidad, forced_threshold)

#################################
# Programa principal
#################################
if __name__ == "__main__":

    start_time = time.perf_counter()
    # Generar una cola inicial con 20 elementos
    cola_inicial = generar_cola(5000)
    print("\nProcesando cola usando programación dinámica (sin redes neuronales)...")
    procesar_cola_dinamico(cola_inicial, CAPACIDAD_MAXIMA, forced_threshold=FORCE_THRESHOLD)
    end_time = time.perf_counter()
    print(f"\nTiempo total de ejecución: {end_time - start_time:.4f} segundos")
