import time
import random
import uuid
import os
from collections import deque

import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data
from config import CAPACIDAD_MAXIMA, MAX_ITEMS, NUM_SAMPLES, FORCE_THRESHOLD


#################################
# 1. Función para generar elementos de la cola
#################################
def generar_cola(num_elementos):
    """
    Genera una cola de elementos.

    Cada elemento es una tupla (id, valor, count) donde:
      - id: identificador único (generado con uuid4),
      - valor: entero aleatorio entre 1 y 12 (qBits),
      - count: contador de prioridad, que inicia en 0.
    
    Parámetro:
      num_elementos (int): número de elementos a generar.
    
    Retorna:
      deque: cola (estructura deque) de elementos.
    """
    cola = deque()
    for _ in range(num_elementos):
        identificador = str(uuid.uuid4())
        valor = random.randint(1, 12)
        count = 0
        cola.append((identificador, valor, count))
    return cola

#################################
# 2. Función target (greedy) usando contador de iteraciones
#################################
def optimizar_espacio_target(queue, capacidad, forced_threshold=FORCE_THRESHOLD):
    """
    Dada una cola (lista de tuplas (id, valor, count)) y la capacidad,
    retorna una lista binaria (0 o 1) indicando para cada elemento si es seleccionado.

    La política es:
      1. Forzar la selección de los elementos cuyo count >= forced_threshold.
      2. De los restantes, seleccionar primero los de mayor valor y, en caso de empate, los de mayor count.
      3. Si queda capacidad, completar con los que tengan mayor count.
    """
    seleccionados = [0] * len(queue)
    capacidad_restante = capacidad
    indices = list(range(len(queue)))

    # 1. Forzados: elementos cuyo count >= forced_threshold
    forced_indices = [i for i in indices if queue[i][2] >= forced_threshold]
    forced_indices = sorted(forced_indices, key=lambda i: queue[i][2], reverse=True)
    for i in forced_indices:
        _id, valor, count = queue[i]
        if valor <= capacidad_restante:
            seleccionados[i] = 1
            capacidad_restante -= valor

    # 2. Seleccionar de los restantes los de mayor valor; en caso de empate, los de mayor count
    remaining_indices = [i for i in indices if seleccionados[i] == 0]
    sorted_remaining = sorted(remaining_indices, key=lambda i: (queue[i][1], queue[i][2]), reverse=True)
    for i in sorted_remaining:
        _id, valor, count = queue[i]
        if valor <= capacidad_restante:
            seleccionados[i] = 1
            capacidad_restante -= valor

    # 3. Si queda capacidad, seleccionar los que tengan mayor count
    remaining_indices = [i for i in indices if seleccionados[i] == 0]
    sorted_by_count = sorted(remaining_indices, key=lambda i: queue[i][2], reverse=True)
    for i in sorted_by_count:
        _id, valor, count = queue[i]
        if valor <= capacidad_restante:
            seleccionados[i] = 1
            capacidad_restante -= valor

    return seleccionados

#################################
# 3. Definición del modelo de red neuronal
#################################
class SeleccionadorNN(nn.Module):
    def __init__(self, input_dim=2, hidden_dim=16):
        """
        La red recibe por cada elemento un vector de características:
            [valor_normalizado, count_normalizado]
        """
        super(SeleccionadorNN, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, 1)  # Salida: score (se aplicará sigmoid)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # x tiene forma (batch, num_items, input_dim)
        batch_size, num_items, input_dim = x.size()
        x = x.view(-1, input_dim)  # Aplanar para procesar cada elemento
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.sigmoid(x)
        x = x.view(batch_size, num_items)  # Volver a la forma (batch, num_items)
        return x

#################################
# 4. Generación de datos de entrenamiento
#################################
class ColaDataset(torch.utils.data.Dataset):
    def __init__(self, num_samples=NUM_SAMPLES, max_items=MAX_ITEMS, capacidad=CAPACIDAD_MAXIMA, forced_threshold=FORCE_THRESHOLD):
        self.num_samples = num_samples
        self.max_items = max_items
        self.capacidad = capacidad
        self.forced_threshold = forced_threshold
        self.samples = []
        self.generate_samples()

    def generate_samples(self):
        for _ in range(self.num_samples):
            n_items = random.randint(5, self.max_items)
            queue = []
            # Generamos identificadores de ejemplo y simulamos un contador aleatorio
            for i in range(n_items):
                ident = f"E{i+1}"
                valor = random.randint(1, self.capacidad)
                count = random.randint(0, self.forced_threshold + 2)
                queue.append((ident, valor, count))
            features = []
            for (_id, valor, count) in queue:
                # Normalizamos: valor / capacidad y count / forced_threshold
                features.append([valor / float(self.capacidad), count / float(self.forced_threshold)])
            target = optimizar_espacio_target(queue, self.capacidad, self.forced_threshold)
            # Padding para tener max_items elementos
            while len(features) < self.max_items:
                features.append([0.0, 0.0])
                target.append(0)
            features = features[:self.max_items]
            target = target[:self.max_items]
            self.samples.append((features, target))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        features, target = self.samples[idx]
        return (torch.tensor(features, dtype=torch.float32),
                torch.tensor(target, dtype=torch.float32))

#################################
# 5. Función de entrenamiento del modelo
#################################
def train_model(model, dataset, num_epochs=30, batch_size=32, learning_rate=0.001):
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
    criterion = nn.BCELoss()  # Pérdida binaria para clasificación por elemento
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    for epoch in range(num_epochs):
        epoch_loss = 0.0
        for batch_features, batch_targets in dataloader:
            optimizer.zero_grad()
            outputs = model(batch_features)  # Salida: (batch, num_items)
            loss = criterion(outputs, batch_targets)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * batch_features.size(0)
        print(f"Epoch {epoch+1}/{num_epochs}, Loss: {epoch_loss / len(dataset):.4f}")
    return model

#################################
# 6. Función knapsack con bonus (para elementos restantes)
#################################
def knapsack_with_bonus(items, capacity):
    """
    Resuelve el problema de la mochila 0/1 para un conjunto de ítems.
    Cada ítem es una tupla (id, valor, count, profit) donde:
      - valor: espacio que ocupa
      - profit: beneficio ajustado (valor con bonus)
    Retorna:
      - selected: lista de ítems seleccionados (con id, valor y count)
    """
    n = len(items)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        _id, valor, count, profit = items[i - 1]
        for w in range(capacity + 1):
            if valor <= w:
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - valor] + profit)
            else:
                dp[i][w] = dp[i - 1][w]
    selected = []
    w = capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected.append(items[i - 1])
            w -= items[i - 1][1]
    selected.reverse()
    return selected, dp[n][capacity]

#################################
# 7. Función para optimizar la cola usando el modelo entrenado (con knapsack y bonus)
#################################
def optimizar_espacio_ml(model, queue, capacidad, forced_threshold=FORCE_THRESHOLD, alpha=1.0, lambda_penalty=0.5):
    """
    Procesa la cola usando el modelo entrenado combinando:
      1. Selección forzada: elementos cuyo count >= forced_threshold.
      2. Para los restantes, se obtiene la probabilidad del modelo y se calcula un bonus ajustado.
         Luego se aplica knapsack para escoger la combinación óptima.
    
    Retorna:
      - seleccionados: lista de elementos seleccionados (tuplas (id, valor, count)).
      - total_valor: suma total de los valores seleccionados.
      - nueva_cola: cola actualizada (sin los elementos seleccionados).
    """
    seleccionados = []
    capacidad_restante = capacidad
    forced_indices = []

    #print("\n🔹 Estado inicial de la cola:", queue)

    # 1. Selección forzada
    for idx, (ident, valor, count) in enumerate(queue):
        if count >= forced_threshold:
            if valor <= capacidad_restante:
                seleccionados.append((ident, valor, count))
                capacidad_restante -= valor
                forced_indices.append(idx)

    #print(f"✅ Elementos en prioridad seleccionados: {seleccionados}")
    #print(f"⚡ Capacidad restante después de prioridad: {capacidad_restante}")

    # 2. Elementos restantes (no forzados)
    queue_restante = [item for idx, item in enumerate(queue) if idx not in forced_indices]

    # **Corrección**: Verificar correctamente si no hay seleccionados para aplicar solo knapsack
    if not seleccionados:
        print("📌 No hay elementos en prioridad, aplicando solo knapsack.")

    # Preparar características para el modelo ML (valor y count normalizados)
    features = [[valor / float(capacidad), count / float(forced_threshold)] for (ident, valor, count) in queue_restante]

    if features:
        input_tensor = torch.tensor([features], dtype=torch.float32)
        with torch.no_grad():
            probs = model(input_tensor)
        probs = probs.squeeze(0).tolist()
    else:
        probs = []

    #print(f"🔍 Probabilidades asignadas por el modelo: {probs}")

    # Ajustar bonus si hay muchos elementos de alta prioridad
    num_high_priority = sum(1 for ident, valor, count in queue_restante if count >= forced_threshold)
    penalty_factor = 1 + lambda_penalty * num_high_priority

    # Calcular profit para cada elemento restante
    remaining_items = []
    for i, (ident, valor, count) in enumerate(queue_restante):
        prob = probs[i] if i < len(probs) else 0
        profit = valor * (1 + alpha * prob) * (count / penalty_factor)
        remaining_items.append((ident, valor, count, profit))

    # **Corrección**: Verificar si la lista `remaining_items` no está vacía antes de aplicar knapsack
    if not remaining_items:
        print("⚠️ No hay elementos disponibles para la mochila. Se seleccionará el de mayor valor.")
        if queue:
            best_element = max(queue, key=lambda x: x[1])  # Seleccionar el de mayor valor
            remaining_items.append((best_element[0], best_element[1], best_element[2], best_element[1]))

    #print(f"🎯 Elementos enviados al knapsack: {remaining_items}")
    
    # 3. Aplicar knapsack para los elementos restantes
    selected_knapsack, _ = knapsack_with_bonus(remaining_items, capacidad_restante)
    selected_knapsack_clean = [(ident, valor, count) for (ident, valor, count, profit) in selected_knapsack]

    # Combinar ambas selecciones
    seleccionados += selected_knapsack_clean
    total_valor = sum(valor for (ident, valor, count) in seleccionados)

    # Actualizar la cola: eliminar elementos seleccionados (comparando por id)
    seleccionados_ids = {ident for (ident, valor, count) in seleccionados}
    nueva_cola = [item for item in queue if item[0] not in seleccionados_ids]

    #print(f"✅ Elementos seleccionados después del knapsack: {seleccionados}")
    #print(f"🆕 Cola restante después de optimización: {nueva_cola}")

    return seleccionados, total_valor, nueva_cola

#################################
# 8. Función interactiva para procesar la cola con ML
#################################
def procesar_cola_ml(cola, capacidad, model, forced_threshold=FORCE_THRESHOLD, alpha=1.0):
    """
    Procesa la cola de forma interactiva. El formato es:
      1. Se pregunta al usuario cuántas veces desea procesar la cola.
         - Si se introduce un número mayor que 0, se ejecutan esa cantidad de iteraciones.
         - Si se introduce 0, se procesan todas las combinaciones hasta vaciar la cola.
      2. Además, cada 3 iteraciones se añaden automáticamente 3 nuevos elementos a la cola.
    
    En cada iteración:
      - Se incrementa el contador (count) de cada elemento en 1.
      - Se muestra el estado de la cola (se muestran los identificadores, valor y count).
      - Se procesa la cola usando optimizar_espacio_ml.
    """
    iter_global = 0  # Contador global de iteraciones

    # Preguntar al usuario la opción de procesamiento:
    num_iteraciones = int(input("¿Cuántas veces deseas procesar la cola? (0 para vaciarla automáticamente): "))

    if num_iteraciones == 0:
        # Modo vaciado automático: se procesan iteraciones hasta que la cola esté vacía.
        while cola:
            # Incrementar count en cada elemento
            cola = deque([(ident, valor, count + 1) for (ident, valor, count) in cola])
            iter_global += 1
            print(f"\nIteración {iter_global} - Estado de la cola:")
            for item in cola:
                ident, valor, count = item
                print(f"  Elemento {ident}: Valor = {valor}, Iteraciones = {count}")
            # Cada 3 iteraciones, añadir 3 nuevos elementos automáticamente
            if iter_global % 3 == 0:
                print("\n--- Se añaden 3 nuevos elementos a la cola automáticamente ---")
                nuevos_elementos = generar_cola(3)
                for elem in nuevos_elementos:
                    cola.append(elem)
            seleccionados, valor_total, nueva_cola = optimizar_espacio_ml(
                model, list(cola), capacidad, forced_threshold, alpha)
            print(f"\nProcesando cola en iteración {iter_global}:")
            print(f"  Cola actual (IDs): {[ident for (ident, valor, count) in nueva_cola]}")
            print(f"  Elementos seleccionados (IDs): {[ident for (ident, valor, count) in seleccionados]}")
            print(f"  Valor total obtenido: {valor_total}")
            cola = deque(nueva_cola)
    else:
        # Modo iterativo: se procesan el número de iteraciones indicado por el usuario.
        for _ in range(num_iteraciones):
            # Incrementar count en cada elemento
            cola = deque([(ident, valor, count + 1) for (ident, valor, count) in cola])
            iter_global += 1
            print(f"\nIteración {iter_global} - Estado de la cola:")
            for item in cola:
                ident, valor, count = item
                print(f"  Elemento {ident}: Valor = {valor}, Iteraciones = {count}")
            # Cada 3 iteraciones, añadir 3 nuevos elementos automáticamente
            if iter_global % 3 == 0:
                print("\n--- Se añaden 3 nuevos elementos a la cola automáticamente ---")
                nuevos_elementos = generar_cola(3)
                for elem in nuevos_elementos:
                    cola.append(elem)
            seleccionados, valor_total, nueva_cola = optimizar_espacio_ml(
                model, list(cola), capacidad, forced_threshold, alpha)
            print(f"\nProcesando cola en iteración {iter_global}:")
            print(f"  Cola actual (IDs): {[ident for (ident, valor, count) in nueva_cola]}")
            print(f"  Elementos seleccionados (IDs): {[ident for (ident, valor, count) in seleccionados]}")
            print(f"  Valor total obtenido: {valor_total}")
            cola = deque(nueva_cola)
        # Tras finalizar las iteraciones indicadas, se pregunta si se desean añadir nuevos elementos
        if cola:
            añadir = input("\n¿Deseas añadir nuevos elementos a la cola? (s/n): ").lower()
            if añadir == 's':
                nuevos = input("Introduce los pares id:valor separados por espacios: ").split()
                for par in nuevos:
                    try:
                        ident, valor_str = par.split(':')
                        valor = int(valor_str)
                        cola.append((ident, valor, 0))  # count inicia en 0
                    except Exception as e:
                        print(f"Error al procesar '{par}': {e}")
            # Se puede continuar iterando si se desea (opcional)
            procesar_cola_ml(cola, capacidad, model, forced_threshold, alpha)


# Funciones para guardar y cargar metadata (por ejemplo, el valor de capacidad con el que se entrenó el modelo)
def guardar_metadata(capacidad, metadata_path="Machine_Learnig/metadata.txt"):
    with open(metadata_path, "w") as f:
        f.write(str(capacidad))

def cargar_metadata(metadata_path="Machine_Learnig/metadata.txt"):
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            try:
                return int(f.read().strip())
            except:
                return None
    return None

#################################
# 9. Programa principal: Entrenamiento y procesamiento de la cola
#################################
if __name__ == "__main__":
    start_time = time.perf_counter()


    print("Generando dataset de entrenamiento...")
    dataset = ColaDataset(num_samples=NUM_SAMPLES, max_items=MAX_ITEMS,
                           capacidad=CAPACIDAD_MAXIMA, forced_threshold=FORCE_THRESHOLD)
    model = SeleccionadorNN(input_dim=2, hidden_dim=16)
    MODEL_PATH = "Machine_Learnig/modelo_entrenado.pth"
    METADATA_PATH = "Machine_Learnig/metadata.txt"

    # Cargar la capacidad con la que se entrenó el modelo previamente
    capacidad_entrenada = cargar_metadata(METADATA_PATH)
    # Solo se reentrena si el modelo no existe, o si la diferencia entre la capacidad actual y la entrenada es >= 50.
    if os.path.exists(MODEL_PATH) and capacidad_entrenada is not None and abs(CAPACIDAD_MAXIMA - capacidad_entrenada) < 1000:
        print("Cargando modelo entrenado...")
        model.load_state_dict(torch.load(MODEL_PATH))
        model.eval()
    else:
        print("Entrenando el modelo...")
        model = train_model(model, dataset, num_epochs=30, batch_size=32, learning_rate=0.001)
        torch.save(model.state_dict(), MODEL_PATH)
        guardar_metadata(CAPACIDAD_MAXIMA, METADATA_PATH)

    # Generar la cola inicial (por ejemplo, 20 elementos)
    # print("\nGenerando cola inicial...")
    cola = generar_cola(1)

    # Procesar la cola usando el modelo entrenado
    print("\nProcesando cola usando el modelo de Machine Learning...")
    procesar_cola_ml(cola, CAPACIDAD_MAXIMA, model, forced_threshold=FORCE_THRESHOLD, alpha=1.0)

    end_time = time.perf_counter()
    print(f"\nTiempo total de ejecución: {end_time - start_time:.4f} segundos")
