import aiohttp
import asyncio

url = 'http://localhost:8082/'

INTERVALO_ENTRE_CIRCUITOS = 25

pathURL = 'url'
pathResult = 'result'
pathCircuit = 'circuit'



urls = {
    "Popular-dj-4": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_4_mqt.py",



}

async def post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return response.status, await response.text()

async def main():
    data_template = {
        "url": "", 
        "shots": 10000,
        "provider": ['ibm'],
        "policy": "time", 
    }
    async with aiohttp.ClientSession() as session:
        circuitos = list(urls.items())
        for index, (name, url_value) in enumerate(circuitos):
            data = data_template.copy()
            data["url"] = url_value

            print(f"Enviando {index + 1}/{len(circuitos)}: {name}")
            status, response = await post_request(session, url + pathCircuit, data)
            print(f"Respuesta para {name} ({status}): {response}")

            if index < len(circuitos) - 1:
                print(f"Esperando {INTERVALO_ENTRE_CIRCUITOS} segundos...")
                await asyncio.sleep(INTERVALO_ENTRE_CIRCUITOS)

asyncio.run(main())