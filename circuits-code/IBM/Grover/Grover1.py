from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
import numpy as np

qreg_q = QuantumRegister(2, 'q')
creg_meas = ClassicalRegister(2, 'meas')

circuit = QuantumCircuit(qreg_q, creg_meas)


circuit.h(qreg_q[0])
circuit.h(qreg_q[1])

circuit.x(qreg_q[1])
circuit.h(qreg_q[1])

circuit.cx(qreg_q[0], qreg_q[1])

circuit.h(qreg_q[1])
circuit.x(qreg_q[1])
circuit.h(qreg_q[1])

circuit.measure(qreg_q[0], creg_meas[0])
circuit.measure(qreg_q[1], creg_meas[1])