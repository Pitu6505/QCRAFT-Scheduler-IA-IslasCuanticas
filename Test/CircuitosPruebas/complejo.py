from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
import numpy as np

qreg_q = QuantumRegister(5, 'q')
creg_meas = ClassicalRegister(5, 'meas')

circuit = QuantumCircuit(qreg_q, creg_meas)

# ================================
# CAPA 1: Rotaciones y Entrelazamiento
# ================================
circuit.rx(np.pi/2, qreg_q[0])
circuit.rz(np.pi/4, qreg_q[0])
circuit.rx(np.pi/2, qreg_q[1])
circuit.rz(np.pi/4, qreg_q[1])
circuit.rx(np.pi/2, qreg_q[2])
circuit.rz(np.pi/4, qreg_q[2])
circuit.rx(np.pi/2, qreg_q[3])
circuit.rz(np.pi/4, qreg_q[3])
circuit.rx(np.pi/2, qreg_q[4])
circuit.rz(np.pi/4, qreg_q[4])

# Escalera de CX (Generador principal de Crosstalk)
circuit.cx(qreg_q[0], qreg_q[1])
circuit.cx(qreg_q[1], qreg_q[2])
circuit.cx(qreg_q[2], qreg_q[3])
circuit.cx(qreg_q[3], qreg_q[4])
circuit.cx(qreg_q[4], qreg_q[0])

# ================================
# CAPA 2: Aumento de la profundidad
# ================================
circuit.rx(np.pi/3, qreg_q[0])
circuit.rz(np.pi/5, qreg_q[0])
circuit.rx(np.pi/3, qreg_q[1])
circuit.rz(np.pi/5, qreg_q[1])
circuit.rx(np.pi/3, qreg_q[2])
circuit.rz(np.pi/5, qreg_q[2])
circuit.rx(np.pi/3, qreg_q[3])
circuit.rz(np.pi/5, qreg_q[3])
circuit.rx(np.pi/3, qreg_q[4])
circuit.rz(np.pi/5, qreg_q[4])

# Escalera secundaria de CX
circuit.cx(qreg_q[0], qreg_q[1])
circuit.cx(qreg_q[1], qreg_q[2])
circuit.cx(qreg_q[2], qreg_q[3])
circuit.cx(qreg_q[3], qreg_q[4])
circuit.cx(qreg_q[4], qreg_q[0])

# ================================
# Mediciones Finales
# ================================
circuit.measure(qreg_q[0], creg_meas[0])
circuit.measure(qreg_q[1], creg_meas[1])
circuit.measure(qreg_q[2], creg_meas[2])
circuit.measure(qreg_q[3], creg_meas[3])
circuit.measure(qreg_q[4], creg_meas[4])