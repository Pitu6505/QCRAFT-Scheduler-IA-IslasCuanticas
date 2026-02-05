# config.py
CAPACIDAD_MAXIMA = 156
MAX_ITEMS = 25
NUM_SAMPLES = 2000
FORCE_THRESHOLD = 12  # Umbral de iteraciones para forzar la prioridad
NUM_ENTRENAMIENTO = 30

# Distancia mínima entre circuitos (número de nodos)
MIN_CIRCUIT_DISTANCE = 0

# Umbral máximo aceptable de ruido/temperatura para usar un nodo
MAX_NOISE_THRESHOLD = 312.15 #0.05575   # Ajustado para máquinas no-Brisbane (era 312.0550)

Porcentaje_util = 90  # Porcentaje de qubits a utilizar según el umbral dinámico, valor entre 0 y 100

#Configuracion de la particiones del grafo 
USE_PARTITION = False       
PARTITIONS = 4           
PARTITION_INDEX = 1        
PARTITION_RANGES = None