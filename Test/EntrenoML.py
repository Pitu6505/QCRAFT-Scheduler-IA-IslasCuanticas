import aiohttp
import asyncio

url = 'http://localhost:8082/'
pathURL = 'url'
pathResult = 'result'
pathCircuit = 'circuit'

# Aquí puedes añadir los circuitos de QFT, VQE, QAOA y Grover para generar el dataset
urls = {
    # "grover-noancilla_indep_qiskit_10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/grover-noancilla_indep_qiskit_10.qasm",
    "grover-noancilla_indep_qiskit_5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/grover-noancilla_indep_qiskit_5.qasm",
    # "qaoa_indep_qiskit_10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/qaoa_indep_qiskit_10.qasm",
    "qaoa_indep_qiskit_5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/qaoa_indep_qiskit_5.qasm",
    # "qft_indep_qiskit_10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/qft_indep_qiskit_10.qasm",
    "qft_nativegates_ibm_qiskit_opt3_5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/qft_nativegates_ibm_qiskit_opt3_5.qasm",
    # "random_indep_qiskit_10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/random_indep_qiskit_10.qasm",
    # "random_indep_qiskit_5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/random_indep_qiskit_5.qasm",
    # "vqe_indep_qiskit_10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/vqe_indep_qiskit_10.qasm",
    "vqe_indep_qiskit_5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/vqe_indep_qiskit_5.qasm",
}

async def post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.text()

async def main():
    # 1. ACTUALIZAMOS EL TEMPLATE BASE
    data_template = {
        "url": "", 
        "shots": 10000,           # 10.000 shots perfectos para generar estadística de error
        "provider": ['ibm'],
        "policy": "Islas_Cuanticas_Edges", 
        "sentinel_mode": "crosstalk_perimetro"  # <--- AQUÍ ACTIVAMOS NUESTRO NUEVO MODO
    }
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for name, url_value in urls.items():
            data = data_template.copy()
            data["url"] = url_value
            # Aseguramos que machaque cualquier valor previo
            data["policy"] = "Islas_Cuanticas_Edges"
            data["sentinel_mode"] = "crosstalk_perimetro" # <--- Y AQUÍ TAMBIÉN
            
            print(f"Lanzando {name} con recolección de crosstalk...")
            task = post_request(session, url + pathCircuit, data)
            tasks.append(task)
            
        responses = await asyncio.gather(*tasks)
        for response in responses:
            print(response)

asyncio.run(main())