import aiohttp
import asyncio
url = 'http://localhost:8082/'

pathURL = 'url'
pathResult = 'result'
pathCircuit = 'circuit'


urls = {
    "Sencillo": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/Qbits-Centinelas/Test/CircuitosPruebas/sencillo.py",
    "Complejo": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/CSV/Test/CircuitosPruebas/circuito_estres_10q.py"
#   la composicion 4 es desde Reversible-3 hasta vqe-4 sin las dynamic. La composicion 5 es de todos los dynamic
}

async def post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.text()

async def main():
    data_template = {
        "url": "", 
        "shots": 1000,
        "provider": ['aws'],
        "policy": "Islas_Cuanticas_Edges", 
        "sentinel_mode": "dynamic_local_t1" 
    }
    async with aiohttp.ClientSession() as session:
        tasks = []
        for name, url_value in urls.items():
            data = data_template.copy()
            data["url"] = url_value
            task = post_request(session, url + pathCircuit, data)
            tasks.append(task)
            
        responses = await asyncio.gather(*tasks)
        for response in responses:
            print(response)

asyncio.run(main())