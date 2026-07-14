from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
import numpy as np

qreg_q = QuantumRegister(2, 'q')
creg_meas = ClassicalRegister(2, 'meas')

circuit = QuantumCircuit(qreg_q, creg_meas)

# Preparación de un Estado de Bell (Entrelazamiento básico)
circuit.h(qreg_q[0])
circuit.cx(qreg_q[0], qreg_q[1])

# Rotaciones estáticas para mantener el enfoque variacional sin usar ParameterVector
circuit.rx(np.pi/2, qreg_q[0])
circuit.ry(np.pi/4, qreg_q[1])

# Medición explícita para que la API la intercepte
circuit.measure(qreg_q[0], creg_meas[0])
circuit.measure(qreg_q[1], creg_meas[1])