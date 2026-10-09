from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit.visualization import plot_gate_map
import matplotlib.pyplot as plt

# 1. Cargar tu cuenta y el backend
service = QiskitRuntimeService(channel="ibm_cloud", token="", instance="")
backend = service.backend("ibm_fez")

# 2. Extraer la lista matemática de conexiones (nodos conectados)
conexiones = backend.coupling_map.get_edges()
print(f"Total de qubits: {backend.num_qubits}")
print("Lista de conexiones físicas:", conexiones)

# 3. Dibujar el mapa topológico en pantalla
plot_gate_map(backend, title="Topología de ibm_fez")
plt.show()