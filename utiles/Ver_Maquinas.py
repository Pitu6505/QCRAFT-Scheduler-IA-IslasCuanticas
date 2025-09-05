from qiskit_ibm_runtime import QiskitRuntimeService

# Usa el canal nuevo recomendado
service = QiskitRuntimeService(channel="ibm_cloud")

print("Backends disponibles:")
for backend in service.backends(simulator=False):
    config = backend.configuration()
    status = backend.status()
    print(f"{backend.name} | Qubits: {config.num_qubits} | Offline: {not status.operational}")
