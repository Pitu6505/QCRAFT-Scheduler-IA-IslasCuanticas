from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
import numpy as np

qreg = QuantumRegister(2, 'q')
creg = ClassicalRegister(2, 'meas')

circuit = QuantumCircuit(qreg, creg)


circuit.h(qreg[0])
circuit.h(qreg[1])

circuit.x(qreg[1])
circuit.h(qreg[1])

circuit.cx(qreg[0], qreg[1])

circuit.h(qreg[1])
circuit.x(qreg[1])
circuit.h(qreg[1])

circuit.measure(qreg[0], creg[0])
circuit.measure(qreg[1], creg[1])