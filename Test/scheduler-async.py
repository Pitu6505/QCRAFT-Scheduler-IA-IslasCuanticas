import aiohttp
import asyncio
url = 'http://localhost:8082/'

pathURL = 'url'
pathResult = 'result'
pathCircuit = 'circuit'


urls = {
    "CentinelaInactivo": "https://raw.githubusercontent.com/Pitu6505/QCRAFT-Scheduler-IA-IslasCuanticas/refs/heads/Qbits-Centinelas/Test/CircuitosPruebas/CentinelasBajos.qasm"
#   la composicion 4 es desde Reversible-3 hasta vqe-4 sin las dynamic. La composicion 5 es de todos los dynamic
}

async def post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.text()

async def main():
    data_template = {
        "url": "",
        "shots": 10000,
        "provider": ['ibm'],
        "policy": "time"
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