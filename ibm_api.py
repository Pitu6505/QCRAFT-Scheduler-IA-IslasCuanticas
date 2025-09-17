from qiskit_ibm_runtime import QiskitRuntimeService

API_KEY = "ps93hObrV9a1OpKzKEAdyxlbsQF_jA-uPAzB1isr_lH-"
INSTANCE_CRN = "crn:v1:bluemix:public:quantum-computing:us-east:a/350b4d725caf401ca6c42d2beddead9a:4105e9d7-2463-4330-983e-bcfd53eea99d::"

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
