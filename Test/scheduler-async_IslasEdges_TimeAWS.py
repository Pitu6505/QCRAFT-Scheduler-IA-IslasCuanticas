import aiohttp
import asyncio
url = 'http://localhost:8082/'

pathURL = 'url'
pathResult = 'result'
pathCircuit = 'circuit'


urls = {
    #  "deutsch-jozsa": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/Deutsch-Jozsa.py",
    #  "bernstein-vazirani": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/bernstein-vazirani.py",
    #  "full_adder": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/full_adder.py",
     "grover": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/grover.py",
    #  "kickback": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/kickback.py",
    #  "phase_estimation": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/phase_estimation.py",
    #  "qaoa": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/qaoa.py",
    #  "qft": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/qft.py",
    #  "qwalk": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/qwalk.py",
    #  "shor": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/shor.py",
    #  "simon": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/simon.py",
    #  "tsp": "https://raw.githubusercontent.com/jorgecs/CompositionCircuits/main/circuits_braket/tsp.py"
}

async def post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.text()

async def main():
    data_template = {
        "url": "",
        "shots": 1000,
        "provider": ['aws'],
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