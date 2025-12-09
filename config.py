# config.py
CAPACIDAD_MAXIMA = 133
MAX_ITEMS = 25
NUM_SAMPLES = 2000
FORCE_THRESHOLD = 12  # Umbral de iteraciones para forzar la prioridad
NUM_ENTRENAMIENTO = 30

# Distancia mínima entre circuitos (número de nodos)
MIN_CIRCUIT_DISTANCE = 2

# Umbral máximo aceptable de ruido/temperatura para usar un nodo
MAX_NOISE_THRESHOLD = 312.15 #0.05575   # Ajustado para máquinas no-Brisbane (era 312.0550)

Porcentaje_util = 70  # Porcentaje de qubits a utilizar según el umbral dinámico, valor entre 0 y 100

#Configuracion de la particiones del grafo 
USE_PARTITION = False       # True para activar particionado
PARTITIONS = 4             # número de particiones si se usa particionado uniforme
PARTITION_INDEX = 1        # índice para ver en que partición estamos (1-based), si queremos moverlo debemos de aumentarlo en 1 hasta el maximo de particiones que haya
# Ejemplo de ranges personalizados (opcional). Cada tupla es (start, end) inclusive.
# Si lo defines, se usa esta lista y se ignora PARTITIONS.
PARTITION_RANGES = None