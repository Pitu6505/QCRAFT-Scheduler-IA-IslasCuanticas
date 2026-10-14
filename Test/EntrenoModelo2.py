import aiohttp
import asyncio
import random

url_api = 'http://localhost:8082/circuit'
NUM_TANDAS = 10

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

async def lanzar_ataque_ciegas(num_tandas=NUM_TANDAS):
    print(f"INICIANDO SIMULACIÓN QAAS - {num_tandas} tandas")

    async with aiohttp.ClientSession() as session:
        for numero_tanda in range(1, num_tandas + 1):
            print(f"\n--- Inyectando tanda {numero_tanda}/{num_tandas} ---")
            circuitos = [
                ("centinela radar_distribuido", {
                    "url": URL_ESPIA,
                    "shots": 4096,
                    "provider": ['ibm'],
                    "policy": "Islas_Cuanticas_Edges",
                    "sentinel_mode": "radar_distribuido",
                })
            ]

            for nombre, url_victima in URLS_VICTIMAS.items():
                circuitos.append((nombre, {
                    "url": url_victima,
                    "shots": 4096,
                    "provider": ['ibm'],
                    "policy": "Islas_Cuanticas_Edges",
                }))

            random.shuffle(circuitos)
            tasks = []
            for nombre, datos in circuitos:
                print(f"Encolando: {nombre}")
                tasks.append(post_request(session, url_api, datos))

            await asyncio.gather(*tasks)
            print(
                f"Tanda {numero_tanda} enviada: 1 centinela y "
                f"{len(URLS_VICTIMAS)} víctimas."
            )

            if numero_tanda < num_tandas:
                print("Esperando 1 minuto antes de la siguiente tanda...")
                await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(lanzar_ataque_ciegas())