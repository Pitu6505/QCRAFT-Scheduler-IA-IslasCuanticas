import aiohttp
import asyncio
import random

url = 'http://localhost:8082/'
pathCircuit = 'circuit'

urls = {
    "grover-noancilla_indep_qiskit_5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/grover-noancilla_indep_qiskit_5.qasm",
    "qaoa_indep_qiskit_5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/qaoa_indep_qiskit_5.qasm",
    "qft_nativegates_ibm_qiskit_opt3_5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/qft_nativegates_ibm_qiskit_opt3_5.qasm",
    "vqe_indep_qiskit_5": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/QCRAFT-ML/circuits-code/IBM/QASM2/vqe_indep_qiskit_5.qasm",
}

async def post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.text()

async def main(iteraciones=50):
    data_template = {
        "url": "", 
        "shots": 10000,
        "provider": ['ibm'],
        "policy": "Islas_Cuanticas_Edges", 
        "sentinel_mode": "crosstalk_perimetro"
    }
    
    async with aiohttp.ClientSession() as session:
        circuitos_disponibles = list(urls.items())
        
        for i in range(iteraciones):
            print(f"\n{'='*45}")
            print(f"🔄 ITERACIÓN {i+1} DE {iteraciones}")
            print(f"{'='*45}")
            
            # Enviamos siempre los cuatro circuitos, cambiando aleatoriamente su orden.
            num_circuitos_a_enviar = len(circuitos_disponibles)
            lote_aleatorio = random.sample(circuitos_disponibles, num_circuitos_a_enviar)
            
            print(f"🎲 Lote aleatorio: Se enviarán {num_circuitos_a_enviar} circuitos al enjambre.")
            
            tasks = []
            for name, url_value in lote_aleatorio:
                data = data_template.copy()
                data["url"] = url_value
                data["policy"] = "Islas_Cuanticas_Edges"
                data["sentinel_mode"] = "crosstalk_perimetro"
                
                print(f" 🚀 Encolando: {name}")
                task = post_request(session, url + pathCircuit, data)
                tasks.append(task)
                
            # Disparamos el lote completo de forma concurrente
            await asyncio.gather(*tasks)
            print("✅ Resultados enviados al planificador.")
            
            # Espera de seguridad si no es la última iteración
            if i < iteraciones - 1:
                print("⏱️ Esperando 30 segundos para procesar el trabajo y aislar los lotes...")
                await asyncio.sleep(30)  # Espera de 30 segundos para permitir que el planificador procese los trabajos
                
        print("\n🎉 Recolección masiva de datos finalizada con éxito.")

if __name__ == "__main__":
    # Ajusta el número de iteraciones según cuántos datos necesites generar.
    # Por ejemplo, 50 iteraciones generarán 200 muestras nuevas.
    asyncio.run(main(iteraciones=50))