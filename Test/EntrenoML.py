import aiohttp
import asyncio

url = 'http://localhost:8082/'
pathURL = 'url'
pathResult = 'result'
pathCircuit = 'circuit'

# Aquí puedes añadir los circuitos de QFT, VQE, QAOA y Grover para generar el dataset
urls = {
    "Grover-5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Grover/grover-noancilla_indep_qiskit_5.qasm",
"Grover-6": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Grover/grover-noancilla_indep_qiskit_6.qasm",
"Grover-7": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Grover/grover-noancilla_indep_qiskit_7.qasm",
"Grover-8": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Grover/grover-noancilla_indep_qiskit_8.qasm",
# "QFT-5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/QFT/qft_indep_qiskit_5.qasm",
"QFT-6": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/QFT/qft_indep_qiskit_6.qasm",
"QFT-7": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/QFT/qft_indep_qiskit_7.qasm",
"QFT-8": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/QFT/qft_indep_qiskit_8.qasm",
"QFT-9": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/QFT/qft_indep_qiskit_9.qasm",
"QFT-10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/QFT/qft_indep_qiskit_10.qasm",
"QFT-11": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/QFT/qft_indep_qiskit_11.qasm",
"QAOA-5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Qaoa/qaoa_indep_qiskit_5.qasm",
"QAOA-6": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Qaoa/qaoa_indep_qiskit_6.qasm",
"QAOA-7": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Qaoa/qaoa_indep_qiskit_7.qasm",
"QAOA-8": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Qaoa/qaoa_indep_qiskit_8.qasm",
"QAOA-9": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Qaoa/qaoa_indep_qiskit_9.qasm",
"QAOA-10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Qaoa/qaoa_indep_qiskit_10.qasm",
"QAOA-11": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Qaoa/qaoa_indep_qiskit_11.qasm",
"VQE-5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Vqe/vqe_indep_qiskit_5.qasm",
"VQE-6": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Vqe/vqe_indep_qiskit_6.qasm",
"VQE-7": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Vqe/vqe_indep_qiskit_7.qasm",
"VQE-8": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Vqe/vqe_indep_qiskit_8.qasm",
"VQE-9": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Vqe/vqe_indep_qiskit_9.qasm",
"VQE-10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Vqe/vqe_indep_qiskit_10.qasm",
"VQE-11": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/Vqe/vqe_indep_qiskit_11.qasm"
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