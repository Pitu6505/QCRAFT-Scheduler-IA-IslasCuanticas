import os

from qiskit_ibm_runtime import QiskitRuntimeService


def get_backend_graph(backend_name="ibm_fez"):
    token = os.getenv("IBM_QUANTUM_TOKEN")
    instance = os.getenv("IBM_QUANTUM_INSTANCE")
    if token is not None or instance is not None:
        if not token or not instance:
            raise ValueError(
                "Configura conjuntamente IBM_QUANTUM_TOKEN e IBM_QUANTUM_INSTANCE."
            )
        service = QiskitRuntimeService(
            channel="ibm_cloud",
            token=token,
            instance=instance,
        )
    else:
        service = QiskitRuntimeService()
    backend = service.backend(backend_name)
    properties = backend.properties()
    coupling_map = backend.configuration().coupling_map
    qubit_props = properties.to_dict()
    gate_props = properties.gates
    return coupling_map, qubit_props, gate_props
