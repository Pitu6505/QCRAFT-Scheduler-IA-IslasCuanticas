from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram

# Configuración de disparos (shots)
shots = 1024

# 1. Inicializar el circuito
# En Qiskit, debemos especificar cuántos qubits usaremos (índices 0 y 1 = 2 qubits)
qc = QuantumCircuit(2)

# 2. Aplicar las puertas (Traducción directa de Braket)
qc.h(0)
qc.h(1)

qc.x(1)
qc.h(1)

# En Qiskit, CNOT se escribe generalmente como .cx()
qc.cx(0, 1) 

qc.h(1)
qc.x(1)
qc.h(1)

qc.measure_all()