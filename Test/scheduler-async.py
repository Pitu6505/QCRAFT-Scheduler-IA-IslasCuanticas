import aiohttp
import asyncio
url = 'http://localhost:8082/'

pathURL = 'url'
pathResult = 'result'
pathCircuit = 'circuit'


urls = {
 "Popular-simon-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/simon/simon_vq.py",
    "Popular-tsp-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/tsp/tsp_indep_4_mqt.py",
    "Popular-tsp-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/tsp/tsp_indep_5_mqt.py",
    "Reversible-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/reversible/3_17tc_vq.py",
    "qwalk-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//sequential/qwalk/qwalk-noancilla_3_mqt.py",
    "qwalk-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//sequential/qwalk/qwalk-v-chain_3_mqt.py",
    "qwalk-3": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//sequential/qwalk/qwalk-v-chain_5_mqt.py",
    "efficient-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/EfficientSU2/su2_5_vq.py",
    "efficient-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/EfficientSU2/su2random_3_mqt.py",
    "qaoa-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/qaoa/qaoa_indep_3_mqt.py",
    "qaoa-3": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/qaoa/qaoa_indep_4_mqt.py",
    "qaoa-4": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/qaoa/qaoa_indep_5_mqt.py",
    "vqe-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/vqe/vqe_indep_3_mqt.py",
    "vqe-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/vqe/vqe_indep_4_mqt.py",
    "vqe-3": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/vqe/vqe_indep_5_mqt.py",
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