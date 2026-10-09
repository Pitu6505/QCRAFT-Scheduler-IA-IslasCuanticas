import aiohttp
import asyncio
import random

url_api = 'http://localhost:8082/circuit'

# URL de tu nuevo circuito espía
URL_ESPIA = "URL_RAW_GITHUB_espia_radar_25.qasm" 

# Catálogo de Víctimas (Algoritmos pesados para maximizar área de efecto)
URLS_VICTIMAS = [
    "https://raw.githubusercontent.com/.../grover-noancilla_indep_qiskit_10.qasm",
    "https://raw.githubusercontent.com/.../qaoa_indep_qiskit_10.qasm",
    "https://raw.githubusercontent.com/.../qft_indep_qiskit_10.qasm",
    "https://raw.githubusercontent.com/.../vqe_indep_qiskit_10.qasm"
]

async def post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.text()

async def lanzar_ataque_ciegas(iteraciones=50):
    print(f"🌊 INICIANDO SIMULACIÓN QAAS - {iteraciones} Lotes de Ejecución")
    
    async with aiohttp.ClientSession() as session:
        for i in range(iteraciones):
            print(f"\n--- Inyectando Lote {i+1} ---")
            tasks = []
            
            # 1. ENVIAR EL ESPÍA (Alta Prioridad - Fija la topología)
            data_espia = {
                "url": URL_ESPIA, 
                "shots": 10000,
                "provider": ['ibm'],
                "policy": "Islas_Cuanticas_Edges", 
                "sentinel_mode": "radar_distribuido"  # <--- Activa el bloqueo 25D en el backend
            }
            tasks.append(post_request(session, url_api, data_espia))
            
            # 2. ENVIAR LAS VÍCTIMAS (Saturación de la máquina)
            # Lanzamos entre 4 y 6 circuitos pesados aleatorios para llenar la IBM Fez
            num_victimas = random.randint(4, 6) 
            for _ in range(num_victimas):
                data_victima = {
                    "url": random.choice(URLS_VICTIMAS), 
                    "shots": 10000,
                    "provider": ['ibm'],
                    "policy": "Islas_Cuanticas_Edges",
                    # Las víctimas no llevan sentinel_mode, usan el flujo clásico
                }
                tasks.append(post_request(session, url_api, data_victima))
                
            # Disparamos el lote completo de forma concurrente
            await asyncio.gather(*tasks)
            print(f"✅ Lote {i+1} enviado. Espía + {num_victimas} víctimas encoladas.")
            
            # Damos tiempo al planificador para procesar el lote y enviarlo a IBM
            # antes de inundar con el siguiente lote
            await asyncio.sleep(8) 

if __name__ == "__main__":
    asyncio.run(lanzar_ataque_ciegas(iteraciones=50))