from qiskit_ibm_runtime import QiskitRuntimeService

API_KEY = "yhRRwO2NxmhyTE7lyMxCJtCS6NRcuWTOFOwoGlZsyEU0"
INSTANCE_CRN = "crn:v1:bluemix:public:quantum-computing:us-east:a/37297326da5a450689b06b550cc955db:28638ea8-9632-4e4f-988f-143097488ae3::"

def get_backend_graph(backend_name="ibm_brisbane"):
    service = QiskitRuntimeService(
        channel="ibm_cloud",
        token=API_KEY,
        instance=INSTANCE_CRN
    )
    backend = service.backend(backend_name)
    properties = backend.properties()
    coupling_map = backend.configuration().coupling_map
    qubit_props = properties.to_dict()
    gate_props = properties.gates
    return coupling_map, qubit_props, gate_props
