def generar_circuito_masivo(nombre_archivo="circuito_estres_10q.py"):
    codigo = [
        "from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit",
        "import numpy as np\n",
        "qreg_q = QuantumRegister(10, 'q')",
        "creg_c = ClassicalRegister(10, 'c')",
        "circuit = QuantumCircuit(qreg_q, creg_c)\n",
        "# ================================",
        "# CAPA 1: Preparación Densa (Rotaciones)",
        "# ================================"
    ]

    # 1. Rotaciones desenrolladas
    for i in range(10):
        codigo.append(f"circuit.rx(np.pi/2, qreg_q[{i}])")
        codigo.append(f"circuit.rz(np.pi/4, qreg_q[{i}])")

    codigo.append("\n# ================================")
    codigo.append("# CAPA 2: Entrelazamiento Masivo (Crosstalk)")
    codigo.append("# ================================")
    # 2. Escalera de CX hacia adelante
    for i in range(9):
        codigo.append(f"circuit.cx(qreg_q[{i}], qreg_q[{i+1}])")
    codigo.append(f"circuit.cx(qreg_q[9], qreg_q[0])")

    # 3. Escalera de CX hacia atrás (Empeora el ruido electromagnético)
    for i in range(9, 0, -1):
        codigo.append(f"circuit.cx(qreg_q[{i}], qreg_q[{i-1}])")

    codigo.append("\n# ================================")
    codigo.append("# CAPA 3: SWAPs y Toffolis (Fatiga Térmica T1)")
    codigo.append("# ================================")
    # 4. SWAPs (Se compilan como 3 CX cada uno, saturando el bus de microondas)
    for i in range(0, 8, 2):
        codigo.append(f"circuit.swap(qreg_q[{i}], qreg_q[{i+2}])")

    # 5. Toffolis (Aumentan la profundidad masivamente disparando el T1_decay)
    for i in range(0, 7, 3):
        codigo.append(f"circuit.ccx(qreg_q[{i}], qreg_q[{i+1}], qreg_q[{i+2}])")

    codigo.append("\n# ================================")
    codigo.append("# CAPA 4: Rotaciones de Colisión Final")
    codigo.append("# ================================")
    for i in range(10):
        codigo.append(f"circuit.u(np.pi/2, np.pi/4, np.pi/8, qreg_q[{i}])")

    codigo.append("\n# ================================")
    codigo.append("# Barrera y Mediciones")
    codigo.append("# ================================")
    codigo.append("circuit.barrier()")
    
    # 6. Mediciones explícitas de los 10 qubits
    for i in range(10):
        codigo.append(f"circuit.measure(qreg_q[{i}], creg_c[{i}])")

    # Escribir todo el código plano en el archivo
    with open(nombre_archivo, "w") as f:
        f.write("\n".join(codigo))

    print(f"✅ Archivo '{nombre_archivo}' generado con éxito.")
    print(f"📏 Total de instrucciones planas inyectadas: {len(codigo)}")

# Ejecutar el generador
if __name__ == "__main__":
    generar_circuito_masivo()