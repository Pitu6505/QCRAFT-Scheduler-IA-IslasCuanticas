import aiohttp
import asyncio

url_api = 'http://localhost:8082/circuit'

URL_ESPIA = "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM3/espia_radar_25.qasm" 

URLS_VICTIMAS = {
    "grover-v-chain_indep_qiskit_9": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/2%C2%BAModelo/circuits-code/IBM/QASM2/grover-v-chain_indep_qiskit_9.qasm",
    "qaoa_indep_qiskit_10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/qaoa_indep_qiskit_10.qasm",
    "qft_indep_qiskit_10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/qft_indep_qiskit_10.qasm",
    "vqe_indep_qiskit_10": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/vqe_indep_qiskit_10.qasm",
}

async def post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.text()

async def lanzar_ataque_ciegas():
    print(" INICIANDO SIMULACIÓN QAAS - 1 lote de ejecución")
    
    async with aiohttp.ClientSession() as session:
        print("\n--- Inyectando lote único ---")
        tasks = []

        data_espia = {
            "url": URL_ESPIA,
            "shots": 1000,
            "provider": ['ibm'],
            "policy": "Islas_Cuanticas_Edges",
            "sentinel_mode": "radar_distribuido"
        }
        tasks.append(post_request(session, url_api, data_espia))

        for name, url_victima in URLS_VICTIMAS.items():
            data_victima = {
                "url": url_victima,
                "shots": 1000,
                "provider": ['ibm'],
                "policy": "Islas_Cuanticas_Edges",
                
            }
            print(f" Encolando víctima: {name}")
            tasks.append(post_request(session, url_api, data_victima))

        await asyncio.gather(*tasks)
        print(f" Lote enviado: 1 centinela y {len(URLS_VICTIMAS)} víctimas únicas.")

if __name__ == "__main__":
    asyncio.run(lanzar_ataque_ciegas())