import aiohttp
import asyncio
url = 'http://localhost:8082/'

pathURL = 'url'
pathResult = 'result'
pathCircuit = 'circuit'

# 45 Circuitos


urls = {
    "Popular-dj-3": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_4_mqt.py",
    "Popular-dj-4": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_5_mqt.py",
    "Popular-dj-5": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_7_mqt.py",
    "Popular-adder-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/adder/adder_n10_vq.py",
    "Popular-adder-4": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/adder/adder_n4_vq.py",
    "Popular-adder-5": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/adder/adder_n7_vq.py",
    "Popular-bv-3": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_2_vq.py",
    "Popular-bv-4": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_3_vq.py",
    "Popular-bv-5": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_4_vq.py",
    "Popular-bv-6": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_5_vq.py",
    "Popular-bv-7": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_9_vq.py",
    "Popular-grover-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-noancilla_3_mqt.py",
    "Popular-grover-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-noancilla_4_mqt.py",
    "Popular-grover-3": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-v-chain_3_mqt.py",
    "Popular-grover-4": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-v-chain_4_mqt.py",
    "Popular-grover-5": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover_3_vq.py",
    "Popular-grover-6": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover_7_vq.py",
    "Popular-grover-7": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover_9_vq.py",
    "Popular-kickback-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/kickback/kickback_7_vq.py",
    "Popular-pe-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_2_vq.py",
    "Popular-pe-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_3_mqt.py",
    "Popular-pe-3": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_4_mqt.py",
    "Popular-pe-4": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_5_mqt.py",
    "Popular-pe-5": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_5_vq.py",
    "Popular-pe-6": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_6_mqt.py",
    "Popular-pe-7": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_6_vq.py",
    "Popular-pe-8": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_7_mqt.py",
    "Popular-qft-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_2_mqt.py",
    "Popular-qft-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_3_mqt.py",
    "Popular-qft-3": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_3_vq.py",
    "Popular-qft-4": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_4_mqt.py",
    "Popular-qft-5": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_6_mqt.py",
    "Popular-qft-6": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_7_vq.py",
    "Popular-shor-1": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/shor/shor_mod15_mqt.py",
    "Popular-shor-2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/shor/shor_mod21_mqt.py",
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
    "Popular-dj-3-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_4_mqt.py",
    "Popular-dj-4-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_5_mqt.py",
    "Popular-dj-5-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_7_mqt.py",
    "Popular-adder-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/adder/adder_n10_vq.py",
    "Popular-adder-4-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/adder/adder_n4_vq.py",
    "Popular-adder-5-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/adder/adder_n7_vq.py",
    "Popular-bv-3-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_2_vq.py",
    "Popular-bv-4-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_3_vq.py",
    "Popular-bv-5-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_4_vq.py",
    "Popular-bv-6-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_5_vq.py",
    "Popular-bv-7-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/bernstein-vazirani/bv_9_vq.py",
    "Popular-grover-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-noancilla_3_mqt.py",
    "Popular-grover-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-noancilla_4_mqt.py",
    "Popular-grover-3-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-v-chain_3_mqt.py",
    "Popular-grover-4-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-v-chain_4_mqt.py",
    "Popular-grover-5-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover_3_vq.py",
    "Popular-grover-6-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover_7_vq.py",
    "Popular-grover-7-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover_9_vq.py",
    "Popular-kickback-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/kickback/kickback_7_vq.py",
    "Popular-pe-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_2_vq.py",
    "Popular-pe-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_3_mqt.py",
    "Popular-pe-3-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_4_mqt.py",
    "Popular-pe-4-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_5_mqt.py",
    "Popular-pe-5-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_5_vq.py",
    "Popular-pe-6-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_6_mqt.py",
    "Popular-pe-7-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_6_vq.py",
    "Popular-pe-8-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_7_mqt.py",
    "Popular-qft-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_2_mqt.py",
    "Popular-qft-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_3_mqt.py",
    "Popular-qft-3-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_3_vq.py",
    "Popular-qft-4-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_4_mqt.py",
    "Popular-qft-5-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_6_mqt.py",
    "Popular-qft-6-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_7_vq.py",
    "Popular-shor-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/shor/shor_mod15_mqt.py",
    "Popular-shor-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/shor/shor_mod21_mqt.py",
    "Popular-simon-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/simon/simon_vq.py",
    "Popular-tsp-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/tsp/tsp_indep_4_mqt.py",
    "Popular-tsp-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/tsp/tsp_indep_5_mqt.py",
    "Reversible-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/reversible/3_17tc_vq.py",
    "qwalk-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//sequential/qwalk/qwalk-noancilla_3_mqt.py",
    "qwalk-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//sequential/qwalk/qwalk-v-chain_3_mqt.py",
    "qwalk-3-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//sequential/qwalk/qwalk-v-chain_5_mqt.py",
    "efficient-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/EfficientSU2/su2_5_vq.py",
    "efficient-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/EfficientSU2/su2random_3_mqt.py",
    "qaoa-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/qaoa/qaoa_indep_3_mqt.py",
    "qaoa-3-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/qaoa/qaoa_indep_4_mqt.py",
    "qaoa-4-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/qaoa/qaoa_indep_5_mqt.py",
    "vqe-1-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/vqe/vqe_indep_3_mqt.py",
    "vqe-2-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/vqe/vqe_indep_4_mqt.py",
    "vqe-3-Part2": "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//variational/vqe/vqe_indep_5_mqt.py",
}

async def post_request(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.text()

async def main():
    data_template = {
        "url": "", 
        "shots": 10000,
        "provider": ['ibm'],
        "policy": "Islas_Cuanticas_Edges", 
        "sentinel_mode": "none"
    }
    async with aiohttp.ClientSession() as session:
        tasks = []
        for name, url_value in urls.items():
            data = data_template.copy()
            data["url"] = url_value
            data["policy"] = "Islas_Cuanticas_Edges"
            data["sentinel_mode"] = "none"
            task = post_request(session, url + pathCircuit, data)
            tasks.append(task)
            
        responses = await asyncio.gather(*tasks)
        for response in responses:
            print(response)

asyncio.run(main())