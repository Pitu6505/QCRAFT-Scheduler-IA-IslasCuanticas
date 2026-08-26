import json
import queue
import requests
from flask import request
import re
import qiskit.qasm3
from braket.ir.openqasm import Program
from executeCircuitIBM import executeCircuitIBM
from executeCircuitAWS import code_to_circuit_aws, runAWS_save
from dinamico_copy import optimizar_espacio_dinamico
from DeepMochilaId_copy import optimizar_espacio_ml, SeleccionadorNN, ColaDataset, train_model
from IslaCuantica import Cola_Formateada
from ResettableTimer import ResettableTimer
from threading import Thread
from collections import deque
import json
import numpy as np
import os
import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data
from qiskit import QuantumCircuit, circuit, circuit
import threading
from typing import Callable, Iterator
from itertools import combinations
import time
from qiskit_ibm_runtime import SamplerV2 as Sampler, QiskitRuntimeService
import qiskit.providers
import networkx as nx
from ibm_api import get_backend_graph
from graph_utils import build_graph
from circuit_queue import CircuitQueue
import config
from IslaCuantica import Cola_Formateada
import ast
from IslasCuanticas_Edges import Cola_Formateada_edges

MODEL_PATH = "modelo_entrenado.pth"
METADATA_PATH = "metadata.txt"


class Policy:
    """
    Class to store the queues and timers of a policy
    """
    def __init__(self, policy, max_qubits, time_limit_seconds, executeCircuit, aws_machine, ibm_machine):
        """
        Attributes:
            queues (dict): The queues of the policy
            timers (dict): The timers of the policy
        """
        self.queues = {'ibm': [], 'aws': []}
        self.timers = {'ibm': ResettableTimer(time_limit_seconds, lambda: policy(self.queues['ibm'], max_qubits, 'ibm', executeCircuit, ibm_machine)),
                       'aws': ResettableTimer(time_limit_seconds, lambda: policy(self.queues['aws'], max_qubits, 'aws', executeCircuit, aws_machine))}
        

class SchedulerPolicies:
    """
    Class to manage the policies of the scheduler

    Methods:
    --------
    service(service_name) 
        The request handler, adding the circuit to the selected queue
    
    executeCircuit(data,qb,shots,provider,urls)
        Executes the circuit in the selected provider
    
    most_repetitive(array)
        Returns the most repetitive element in an array
    
    create_circuit(urls,code,qb,provider)
        Creates the circuit to execute based on the URLs
    
    send_shots_optimized(queue, max_qubits, provider, executeCircuit, machine)
        Sends the URLs to the server with the minimum number of shots using the shots_optimized policy
    
    send_shots_depth(queue, max_qubits, provider, executeCircuit, machine)
        Sends the URLs to the server with the minimum number of shots and similar depth using the shots_depth policy
    
    send_depth(queue, max_qubits, provider, executeCircuit, machine)
        Sends the URLs to the server with the most similar depth using the depth policy
    
    send_shots(queue, max_qubits, provider, executeCircuit, machine)
        Sends the URLs to the server with the minimum number of shots using the shots policy
    
    send(queue, max_qubits, provider, executeCircuit, machine)
        Sends the URLs to the server using the time policy
    """
    def __init__(self, app):
        """
        Initializes the SchedulerPolicies class

        Attributes:
            app (Flask): The Flask app            
            time_limit_seconds (int): The time limit in seconds            
            max_qubits (int): The maximum number of qubits            
            machine_ibm (str): The IBM machine            
            machine_aws (str): The AWS machine            
            services (dict): The services of the scheduler            
            translator (str): The URL of the translator            
            unscheduler (str): The URL of the unscheduler
        """
        self.app = app
        self.time_limit_seconds = 10
        self.max_qubits = 156
        self.forced_threshold = 12
        self.machine_ibm = 'ibm_fez' #'ibm_torino' #'ibm_fez'  #''local'
        self.machine_aws = 'arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1-108Q' #'local' #'arn:aws:braket:::device/quantum-simulator/amazon/sv1'
        self.executeCircuitIBM = executeCircuitIBM()
        # Cargar modelo de ML si existe, sino entrenarlo
        self.model = SeleccionadorNN(input_dim=2, hidden_dim=16)

        # Lock para evitar concurrencia en Islas Cuánticas
        self.islas_cuanticas_lock = threading.Lock()

        if os.path.exists(MODEL_PATH):
            print("Cargando modelo entrenado...")
            self.model.load_state_dict(torch.load(MODEL_PATH))
            self.model.eval()
        else:
            print("Entrenando el modelo...")
            dataset = ColaDataset(num_samples=1000, max_items=20, capacidad=self.max_qubits, forced_threshold=self.forced_threshold)
            self.model = train_model(self.model, dataset, num_epochs=30, batch_size=32, learning_rate=0.001)
            torch.save(self.model.state_dict(), MODEL_PATH)

        self.services = {'time': Policy(self.send, self.max_qubits, self.time_limit_seconds, self.executeCircuit, self.machine_aws, self.machine_ibm),
                        'shots': Policy(self.send_shots, self.max_qubits, self.time_limit_seconds, self.executeCircuit, self.machine_aws, self.machine_ibm),
                        'depth': Policy(self.send_depth, self.max_qubits, self.time_limit_seconds, self.executeCircuit, self.machine_aws, self.machine_ibm),
                        'shots_depth': Policy(self.send_shots_depth, self.max_qubits, self.time_limit_seconds, self.executeCircuit, self.machine_aws, self.machine_ibm),
                        'shots_optimized': Policy(self.send_shots_optimized, self.max_qubits, self.time_limit_seconds, self.executeCircuit, self.machine_aws, self.machine_ibm),
                        'Optimizacion_ML': Policy(self.send_ML, self.max_qubits, self.time_limit_seconds, self.executeCircuit, self.machine_aws, self.machine_ibm),
                        'Optimizacion_PD': Policy(self.send_PD, self.max_qubits, self.time_limit_seconds , self.executeCircuit, self.machine_aws, self.machine_ibm),
                        'Islas_Cuanticas': Policy(self.send_graph_placement, self.max_qubits, self.time_limit_seconds, self.executeCircuit, self.machine_aws, self.machine_ibm),
                        'Islas_Cuanticas_Edges': Policy(self.send_graph_placement_edges, self.max_qubits, self.time_limit_seconds, self.executeCircuit, self.machine_aws, self.machine_ibm),
                        }

        self.translator = f"http://{self.app.config['TRANSLATOR']}:{self.app.config['TRANSLATOR_PORT']}/code/"
        self.unscheduler = f"http://{self.app.config['HOST']}:{self.app.config['PORT']}/unscheduler"
        self.app.route('/service/<service_name>', methods=['POST'])(self.service)
        

    def service(self, service_name:str) -> tuple:
        """
        The request handler, adding the circuit to the selected queue

        Args:
            service_name (str): The name of the service

        Request Parameters:
            circuit (str): The circuit to execute
            num_qubits (int): The number of qubits of the circuit            
            shots (int): The number of shots of the circuit            
            user (str): The user that executed the circuit
            circuit_name (str): The name of the circuit            
            maxDepth (int): The depth of the circuit            
            provider (str): The provider of the circuit

        Returns:
            tuple: The response of the request
        """
        if service_name not in self.services:
            return 'This service does not exist', 404
        circuit = request.json['circuit']
        num_qubits = request.json['num_qubits']
        shots = request.json['shots']
        user = request.json['user']
        circuit_name = request.json['circuit_name']
        maxDepth = request.json['maxDepth']
        provider = request.json['provider']
        iteracion = request.json['Iteracion']
        sentinel_mode = request.json.get('sentinel_mode', None)
        data = (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion, sentinel_mode)
        self.services[service_name].queues[provider].append(data)
        if not self.services[service_name].timers[provider].is_alive():
            self.services[service_name].timers[provider].start()
        n_qubits = sum(item[1] for item in self.services[service_name].queues[provider])
        if  n_qubits >= self.max_qubits and (service_name != 'Optimizacion_ML' and service_name != 'Optimizacion_PD'):
            self.services[service_name].timers[provider].execute_and_reset()
        return 'Data received', 200
        
    
    def executeCircuit(self, data: dict, qb: list, shots: list, provider: str, urls: list, machine: str, layout_fisico=None) -> None:
        """
        Executes the circuit in the selected provider
        """
        import qiskit.qasm3
        from braket.ir.openqasm import Program
        import re
        import json
        
        circuit = ''
        for d in json.loads(data)['code']:
            circuit = circuit + d + '\n'

        loc = {}
        
        # =====================================================================
        # 1. PARSEO INICIAL Y EXTRACCIÓN DE MEDIDAS (Evita "already measured")
        # =====================================================================
        try:
            qc_original = self.executeCircuitIBM.code_to_circuit_ibm(circuit)
            
            # Extraemos las medidas para ponerlas TODAS al final del circuito
            medidas_originales = []
            datos_sin_medidas = []
            for inst in qc_original.data:
                if inst.operation.name == 'measure':
                    medidas_originales.append(inst)
                else:
                    datos_sin_medidas.append(inst)
            qc_original.data = datos_sin_medidas
            
            if provider == 'aws':
                from qiskit import transpile
                # Forzamos a Qiskit a traducir todo a puertas que Rigetti entienda
                safe_basis = ['cx', 'h', 'x', 'y', 'z', 'rx', 'ry', 'rz', 's', 't', 'sdg', 'tdg', 'barrier', 'delay']
                qc_original = transpile(qc_original, basis_gates=safe_basis, optimization_level=1)
                
            is_qiskit_parsed = True
        except Exception as e:
            print(f"Aviso: No se pudo parsear como Qiskit ({e})")
            qc_original = None
            is_qiskit_parsed = False
            medidas_originales = []

        # =====================================================================
        # 2. ENSAMBLADOR FTQC DINÁMICO (Circuitos con Centinelas)
        # =====================================================================
        if is_qiskit_parsed and layout_fisico is not None and isinstance(layout_fisico[0], dict) and 'sentinel' in layout_fisico[0]:
            from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit
            
            is_dynamic_local = any(mapping.get('mode', 'standard').startswith('dynamic_local') for mapping in layout_fisico)
            is_dynamic_global = any(mapping.get('mode', 'standard').startswith('dynamic') and not mapping.get('mode', 'standard').startswith('dynamic_local') for mapping in layout_fisico)
            is_post_selection_local = any(mapping.get('mode', 'standard').endswith('_local') and not mapping.get('mode', 'standard').startswith('dynamic') for mapping in layout_fisico)
            
            if is_dynamic_local:
                c_flags = []
                total_centinelas = 0
                for i, mapping in enumerate(layout_fisico):
                    sents = mapping['sentinel'] if isinstance(mapping['sentinel'], list) else [mapping['sentinel']]
                    c_flags.append(ClassicalRegister(len(sents), f'c_flag_{i}'))
                    total_centinelas += len(sents)
                    
                q_sentinel = QuantumRegister(total_centinelas, 'q_sentinel')
                new_qc = QuantumCircuit(*qc_original.qregs, q_sentinel, *qc_original.cregs, *c_flags)
                
                idx = 0
                for mapping in layout_fisico:
                    modo = mapping.get('mode', 'standard')
                    for _ in (mapping['sentinel'] if isinstance(mapping['sentinel'], list) else [mapping['sentinel']]):
                        if modo == 'dynamic_local_t1':
                            new_qc.x(q_sentinel[idx])
                        elif modo == 'dynamic_local_ramsey':
                            new_qc.h(q_sentinel[idx])
                        idx += 1
                        
                island_instructions = {i: [] for i in range(len(layout_fisico))}
                island_ranges = {}
                current_offset = 0
                
                for i, m in enumerate(layout_fisico):
                    size = len(m['data'])
                    island_ranges[i] = range(current_offset, current_offset + size)
                    current_offset += size
                    
                for inst in qc_original.data:
                    if inst.qubits:
                        q_idx = qc_original.find_bit(inst.qubits[0]).index
                        for i, r in island_ranges.items():
                            if q_idx in r:
                                island_instructions[i].append(inst)
                                break
                                
                for i in range(len(layout_fisico)):
                    mitad = len(island_instructions[i]) // 2
                    for inst in island_instructions[i][:mitad]:
                        new_qc.append(inst)
                        
                new_qc.barrier()
                
                idx = 0
                for i, mapping in enumerate(layout_fisico):
                    modo = mapping.get('mode', 'standard')
                    for j, _ in enumerate(mapping['sentinel'] if isinstance(mapping['sentinel'], list) else [mapping['sentinel']]):
                        if modo == 'dynamic_local_t1':
                            new_qc.x(q_sentinel[idx])
                        elif modo == 'dynamic_local_ramsey':
                            new_qc.h(q_sentinel[idx])
                        new_qc.measure(q_sentinel[idx], c_flags[i][j])
                        idx += 1
                        
                for i in range(len(layout_fisico)):
                    mitad = len(island_instructions[i]) // 2
                    with new_qc.if_test((c_flags[i], 0)):
                        for inst in island_instructions[i][mitad:]:
                            new_qc.append(inst)
                            
            elif is_dynamic_global:
                total_centinelas = sum(len(m['sentinel'] if isinstance(m['sentinel'], list) else [m['sentinel']]) for m in layout_fisico)
                q_sentinel = QuantumRegister(total_centinelas, 'q_sentinel')
                c_flag = ClassicalRegister(total_centinelas, 'c_flag')
                new_qc = QuantumCircuit(*qc_original.qregs, q_sentinel, *qc_original.cregs, c_flag)
                
                idx = 0
                for m in layout_fisico:
                    modo = m.get('mode', 'standard')
                    for _ in (m['sentinel'] if isinstance(m['sentinel'], list) else [m['sentinel']]):
                        if modo == 'dynamic_t1': new_qc.x(q_sentinel[idx])
                        elif modo == 'dynamic_ramsey': new_qc.h(q_sentinel[idx])
                        idx += 1
                
                new_qc.delay(1000, q_sentinel, unit='ns') 
                new_qc.barrier()
                
                idx = 0
                for m in layout_fisico:
                    modo = m.get('mode', 'standard')
                    for _ in (m['sentinel'] if isinstance(m['sentinel'], list) else [m['sentinel']]):
                        if modo == 'dynamic_t1': new_qc.x(q_sentinel[idx])
                        elif modo == 'dynamic_ramsey': new_qc.h(q_sentinel[idx])
                        new_qc.measure(q_sentinel[idx], c_flag[idx])
                        idx += 1
                        
                with new_qc.if_test((c_flag, 0)):
                    new_qc.compose(qc_original, qubits=range(qc_original.num_qubits), clbits=range(qc_original.num_clbits), inplace=True)
                    
            elif is_post_selection_local:
                c_flags = []
                total_centinelas = 0
                for i, mapping in enumerate(layout_fisico):
                    sents = mapping['sentinel'] if isinstance(mapping['sentinel'], list) else [mapping['sentinel']]
                    c_flags.append(ClassicalRegister(len(sents), f'c_flag_{i}'))
                    total_centinelas += len(sents)
                    
                q_sentinel = QuantumRegister(total_centinelas, 'q_sentinel')
                new_qc = QuantumCircuit(*qc_original.qregs, q_sentinel, *qc_original.cregs, *c_flags)
                
                idx = 0
                for m in layout_fisico:
                    modo = m.get('mode', 'standard')
                    for _ in (m['sentinel'] if isinstance(m['sentinel'], list) else [m['sentinel']]): 
                        if 't1_decay' in modo: 
                            new_qc.x(q_sentinel[idx])
                        else: 
                            new_qc.h(q_sentinel[idx]) 
                        idx += 1
                
                new_qc.barrier()
                new_qc.compose(qc_original, qubits=range(qc_original.num_qubits), clbits=range(qc_original.num_clbits), inplace=True)
                new_qc.barrier()
                
                idx = 0
                for i, m in enumerate(layout_fisico):
                    modo = m.get('mode', 'standard')
                    for j, _ in enumerate(m['sentinel'] if isinstance(m['sentinel'], list) else [m['sentinel']]):
                        if 'dd' in modo:
                            new_qc.x(q_sentinel[idx]); new_qc.barrier(q_sentinel[idx])
                            new_qc.y(q_sentinel[idx]); new_qc.barrier(q_sentinel[idx])
                            new_qc.x(q_sentinel[idx]); new_qc.barrier(q_sentinel[idx])
                            new_qc.y(q_sentinel[idx]); new_qc.h(q_sentinel[idx])
                        elif 'robust' in modo or 'completo' in modo:
                            new_qc.x(q_sentinel[idx]); new_qc.h(q_sentinel[idx])
                        elif 't1_decay' in modo:
                            new_qc.x(q_sentinel[idx])
                        else: 
                            new_qc.h(q_sentinel[idx])
                            
                        new_qc.measure(q_sentinel[idx], c_flags[i][j])
                        idx += 1
            else:
                total_centinelas = sum(len(m['sentinel'] if isinstance(m['sentinel'], list) else [m['sentinel']]) for m in layout_fisico)
                q_sentinel = QuantumRegister(total_centinelas, 'q_sentinel')
                c_flag = ClassicalRegister(total_centinelas, 'c_flag')
                new_qc = QuantumCircuit(*qc_original.qregs, q_sentinel, *qc_original.cregs, c_flag)
                
                idx = 0
                for m in layout_fisico:
                    modo = m.get('mode', 'standard')
                    for _ in (m['sentinel'] if isinstance(m['sentinel'], list) else [m['sentinel']]): 
                        if modo in ['standard', 'robust', 'completo', 'dd']: new_qc.h(q_sentinel[idx])
                        elif modo == 't1_decay': new_qc.x(q_sentinel[idx])
                        idx += 1
                
                new_qc.barrier()
                new_qc.compose(qc_original, qubits=range(qc_original.num_qubits), clbits=range(qc_original.num_clbits), inplace=True)
                new_qc.barrier()
                
                idx = 0
                for m in layout_fisico:
                    modo = m.get('mode', 'standard')
                    for _ in (m['sentinel'] if isinstance(m['sentinel'], list) else [m['sentinel']]):
                        if modo == 'dd':
                            new_qc.x(q_sentinel[idx]); new_qc.barrier(q_sentinel[idx])
                            new_qc.y(q_sentinel[idx]); new_qc.barrier(q_sentinel[idx])
                            new_qc.x(q_sentinel[idx]); new_qc.barrier(q_sentinel[idx])
                            new_qc.y(q_sentinel[idx]); new_qc.h(q_sentinel[idx])
                        elif modo in ['robust', 'completo']:
                            new_qc.x(q_sentinel[idx]); new_qc.h(q_sentinel[idx])
                        elif modo == 't1_decay': new_qc.x(q_sentinel[idx]) 
                        else: new_qc.h(q_sentinel[idx])
                        new_qc.measure(q_sentinel[idx], c_flag[idx])
                        idx += 1
            
            # === Reincorporamos las mediciones de los datos al final protegidas por una barrera ===
            new_qc.barrier()
            for m_inst in medidas_originales:
                new_qc.append(m_inst)
                
            loc['circuit'] = new_qc

            print("\n" + "="*60)
            print(f" ESTRUCTURA DEL CIRCUITO DINÁMICO ({total_centinelas} Sensores)")
            print("="*60)
            print(new_qc.draw(output='text', fold=-1)) 
            print("="*60 + "\n")
            
            layout_fisico_estructurado = layout_fisico.copy()
            
            datos_planos = []
            centinelas_planos = []
            for mapping in layout_fisico:
                datos_planos.extend(mapping['data'])
                sents = mapping['sentinel'] if isinstance(mapping['sentinel'], list) else [mapping['sentinel']]
                centinelas_planos.extend(sents)
            
            layout_fisico_plano = datos_planos + centinelas_planos
            print(f"🛡️ Circuito FTQC generado. Layout final: {layout_fisico_plano}")

            if provider == 'aws':
                print(f"🔄 Traducción Automática: Convirtiendo circuito Qiskit FTQC a OpenQASM 3.0 para Rigetti...")
                
                # ENRUTAMIENTO FÍSICO CON SWAPs BLOQUEANDO PUERTAS U2
                if layout_fisico_plano:
                    try:
                        if not hasattr(self, 'aws_cmap'):
                            from aws_api import get_backend_graph_aws
                            print("🗺️ Descargando mapa de hardware Rigetti para cálculo de rutas...")
                            cmap_edges, _, _ = get_backend_graph_aws("arn:aws:braket:us-west-1::device/qpu/rigetti/Cepheus-1-108Q")
                            if cmap_edges:
                                from qiskit.transpiler import CouplingMap
                                self.aws_cmap = CouplingMap(cmap_edges)
                            else:
                                self.aws_cmap = None
                                
                        if self.aws_cmap:
                            from qiskit import transpile
                            # Aquí está la clave: Obligamos a Qiskit a enrutar usando SOLO primitivas nativas, prohibido usar u2 o u3
                            safe_basis_routing = ['cx', 'h', 'x', 'y', 'z', 'rx', 'ry', 'rz', 's', 't', 'sdg', 'tdg', 'measure', 'barrier', 'delay', 'swap']
                            loc['circuit'] = transpile(loc['circuit'], coupling_map=self.aws_cmap, initial_layout=layout_fisico_plano, basis_gates=safe_basis_routing, optimization_level=1)
                            layout_ya_enrutado = True
                        else:
                            layout_ya_enrutado = False
                    except Exception as e:
                        print(f"⚠️ Error al enrutar con AWS API: {e}")
                        layout_ya_enrutado = False
                else:
                    layout_ya_enrutado = False
                
                qasm_string = qiskit.qasm3.dumps(loc['circuit'])
                qasm_string = qasm_string.replace('include "stdgates.inc";', '')
                
                replacements = {
                    r'\bcx\b': 'cnot', r'\bsdg\b': 'si', r'\btdg\b': 'ti',
                    r'\bid\b': 'i', r'\bcp\b': 'cphaseshift', r'\bp\b': 'phaseshift', r'\bswap\b': 'swap'
                }
                for qiskit_gate, braket_gate in replacements.items():
                    qasm_string = re.sub(qiskit_gate, braket_gate, qasm_string)
                
                bit_decls = re.findall(r'\bbit\[(\d+)\]\s+([a-zA-Z_]\w*);', qasm_string)
                if bit_decls:
                    total_bits = 0
                    reg_map = {}
                    for size_str, name in bit_decls:
                        size = int(size_str)
                        reg_map[name] = (total_bits, size)
                        total_bits += size
                        
                    qasm_string = re.sub(r'\bbit\[\d+\]\s+[a-zA-Z_]\w*;\n?', '', qasm_string)
                    qasm_string = qasm_string.replace("OPENQASM 3.0;", f"OPENQASM 3.0;\nbit[{total_bits}] ro;")
                    
                    sorted_names = sorted(reg_map.keys(), key=len, reverse=True)
                    for name in sorted_names:
                        offset, size = reg_map[name]
                        def repl_idx(match):
                            idx = int(match.group(1))
                            return f"ro[{offset + idx}]"
                        qasm_string = re.sub(rf'\b{name}\s*\[\s*(\d+)\s*\]', repl_idx, qasm_string)
                        
                        if size == 1:
                            qasm_string = re.sub(rf'\b{name}\b', f"ro[{offset}]", qasm_string)
                        else:
                            qasm_string = re.sub(rf'\b{name}\b', f"ro[{offset}:{offset+size-1}]", qasm_string)
                
                if layout_fisico_plano:
                    if layout_ya_enrutado:
                        qubit_decls = re.findall(r'\bqubit\[(\d+)\]\s+([a-zA-Z_]\w*);', qasm_string)
                        for _, q_name in qubit_decls:
                            qasm_string = re.sub(rf'\b{q_name}\[(\d+)\]', r'$\1', qasm_string)
                        qasm_string = re.sub(r'\bqubit\[\d+\]\s+[a-zA-Z_]\w*;\n?', '', qasm_string)
                    else:
                        qubit_decls = re.findall(r'\bqubit\[(\d+)\]\s+([a-zA-Z_]\w*);', qasm_string)
                        q_map = {}
                        current_idx = 0
                        for size_str, name in qubit_decls:
                            size = int(size_str)
                            for i in range(size):
                                if current_idx < len(layout_fisico_plano):
                                    phys_idx = layout_fisico_plano[current_idx]
                                    q_map[f"{name}[{i}]"] = f"${phys_idx}"
                                current_idx += 1
                                
                        qasm_string = re.sub(r'\bqubit\[\d+\]\s+[a-zA-Z_]\w*;\n?', '', qasm_string)
                        
                        for logical, physical in q_map.items():
                            logical_escaped = logical.replace('[', r'\[').replace(']', r'\]')
                            qasm_string = re.sub(rf'\b{logical_escaped}', physical, qasm_string)
                
                print("\n=== OPENQASM 3.0 FINAL ENVIADO A AWS ===")
                print(qasm_string)
                print("========================================\n")
                
                loc['circuit'] = Program(source=qasm_string)

        # =====================================================================
        # 3. MODO SIN CENTINELAS (Circuitos originales o Políticas Básicas)
        # =====================================================================
        else:
            layout_fisico_plano = None
            
            # Devolvemos las medidas si no estábamos usando FTQC
            if is_qiskit_parsed and qc_original:
                qc_original.barrier()
                for m_inst in medidas_originales:
                    qc_original.append(m_inst)
                    
            if provider == 'ibm':
                loc['circuit'] = qc_original if qc_original else self.executeCircuitIBM.code_to_circuit_ibm(circuit)
            else:
                if "OPENQASM 3.0" in circuit:
                    loc['circuit'] = Program(source=circuit)
                elif is_qiskit_parsed:
                    print(f"🔄 Traducción Automática (Sin Centinelas): Convirtiendo Qiskit a OpenQASM 3.0 para Rigetti...")
                    qasm_string = qiskit.qasm3.dumps(qc_original)
                    qasm_string = qasm_string.replace('include "stdgates.inc";', '')
                    
                    replacements = {
                        r'\bcx\b': 'cnot', r'\bsdg\b': 'si', r'\btdg\b': 'ti',
                        r'\bid\b': 'i', r'\bcp\b': 'cphaseshift', r'\bp\b': 'phaseshift'
                    }
                    for qiskit_gate, braket_gate in replacements.items():
                        qasm_string = re.sub(qiskit_gate, braket_gate, qasm_string)
                        
                    bit_decls = re.findall(r'\bbit\[(\d+)\]\s+([a-zA-Z_]\w*);', qasm_string)
                    if bit_decls:
                        total_bits = 0
                        reg_map = {}
                        for size_str, name in bit_decls:
                            size = int(size_str)
                            reg_map[name] = (total_bits, size)
                            total_bits += size
                            
                        qasm_string = re.sub(r'\bbit\[\d+\]\s+[a-zA-Z_]\w*;\n?', '', qasm_string)
                        qasm_string = qasm_string.replace("OPENQASM 3.0;", f"OPENQASM 3.0;\nbit[{total_bits}] ro;")
                        
                        sorted_names = sorted(reg_map.keys(), key=len, reverse=True)
                        for name in sorted_names:
                            offset, size = reg_map[name]
                            def repl_idx(match):
                                idx = int(match.group(1))
                                return f"ro[{offset + idx}]"
                            qasm_string = re.sub(rf'\b{name}\s*\[\s*(\d+)\s*\]', repl_idx, qasm_string)
                            
                            if size == 1:
                                qasm_string = re.sub(rf'\b{name}\b', f"ro[{offset}]", qasm_string)
                            else:
                                qasm_string = re.sub(rf'\b{name}\b', f"ro[{offset}:{offset+size-1}]", qasm_string)
                                
                    print("\n=== OPENQASM 3.0 (SIN CENTINELAS) FINAL ENVIADO A AWS ===")
                    print(qasm_string)
                    print("==========================================================\n")
                    loc['circuit'] = Program(source=qasm_string)
                else:
                    loc['circuit'] = code_to_circuit_aws(circuit)

# =====================================================================
        # 4. EJECUCIÓN (Envío final al proveedor)
        # =====================================================================
        counts = None

        try:
            if provider == 'ibm':
                if layout_fisico_plano is not None:
                    counts = self.executeCircuitIBM.runIBM_save(
                        machine, loc['circuit'], max(shots), [url[3] for url in urls],
                        qb, [url[4] for url in urls], layout_fisico_plano 
                    )
                else:
                    counts = self.executeCircuitIBM.runIBM_save(
                        machine, loc['circuit'], max(shots), [url[3] for url in urls],
                        qb, [url[4] for url in urls]
                    )
            else:
                s3_bucket = ('amazon-braket-jorgecs', 'test/')
                counts = runAWS_save(
                    machine, loc['circuit'], max(shots), [url[3] for url in urls],
                    qb, [url[4] for url in urls],
                    layout_fisico_plano if 'layout_fisico_plano' in locals() else None,
                    s3_folder=s3_bucket
                )

                # === NUEVO: FILTRO DE POST-SELECCIÓN EXCLUSIVO PARA AWS ===
                if counts is not None and layout_fisico is not None and isinstance(layout_fisico[0], dict) and 'sentinel' in layout_fisico[0]:
                    total_logicos = sum(qb)
                    total_centinelas = sum(len(m['sentinel'] if isinstance(m['sentinel'], list) else [m['sentinel']]) for m in layout_fisico)
                    
                    counts_filtrados = {}
                    for bitstring, freq in counts.items():
                        # Braket agrupa todo de izquierda a derecha. Lógicos primero, centinelas al final.
                        datos = bitstring[:total_logicos]
                        centinelas = bitstring[total_logicos:total_logicos+total_centinelas]
                        
                        # Si NO hay ningún '1' en los centinelas (circuito limpio de ruido)
                        if '1' not in centinelas:
                            if datos in counts_filtrados:
                                counts_filtrados[datos] += freq
                            else:
                                counts_filtrados[datos] = freq
                                
                    counts = counts_filtrados
                    print(f"🧹 AWS Post-selección: Se descartaron {max(shots) - sum(counts.values())} shots corruptos.")

        except Exception as e:
            print(f"❌ Error executing circuit: {e}")

        if counts is not None:
            modo_inferido = "Sin_Centinela"
            if layout_fisico is not None and len(layout_fisico) > 0 and isinstance(layout_fisico[0], dict):
                modo_inferido = layout_fisico[0].get('mode', 'Sin_Centinela')
                
            layout_final = layout_fisico_estructurado if 'layout_fisico_estructurado' in locals() and layout_fisico_estructurado is not None else layout_fisico

            data = {
                "id": "Simulacion", 
                "counts": counts,
                "shots": shots,
                "provider": provider,
                "qb": qb,
                "users": [url[3] for url in urls],
                "circuit_names": [url[4] for url in urls],
                "layout_fisico": layout_final, 
                "modo": modo_inferido 
            }
            requests.post(self.unscheduler, json=data)
        else:
            print("⚠️ No se obtuvieron resultados de ejecución (counts = None)")

    def most_repetitive(self, array:list) -> int: #Check the most repetitive element in an array and if there are more than one, return the smallest
        """
        Returns the most repetitive element in an array

        Args:
            array (list): The array to check
        
        Returns:
            int: The most repetitive element in the array
        """
        count_dict = {}
        for element in array: #Hashing the elements and counting them
            if element in count_dict:
                count_dict[element] += 1
            else:
                count_dict[element] = 1

        max_count = 0
        max_element = None
        for element, count in count_dict.items(): #Simple search for the higher element in the hash. If two elements have the same count, the smallest is returned
            if count > max_count or (count == max_count and element < max_element):
                max_count = count
                max_element = element

        return max_element
    
    def get_ibm_queue_length(self) -> int:
        """
        Obtiene el número de trabajos en espera en la cola de IBM.
        """


        try:
            self.transpile_lock = threading.Lock()
            self.condition = threading.Condition()
            self.service = QiskitRuntimeService()
            all_jobs = self.service.jobs()
            queued_jobs = self.queued_jobs = len([job for job in all_jobs if job.status() == qiskit.providers.JobStatus.QUEUED])
            print(f"🔎 IBM Job Queue: {queued_jobs} trabajos en espera")
            return queued_jobs
        except Exception as e:
            print(f"⚠️ Error obteniendo la cola de IBM: {e}")
            return 0  # Si hay un error, asumimos que no hay trabajos en cola

    def create_circuit(self, urls: list, code: list, qb: list, provider: str) -> None:
        composition_qubits = 0
        es_qasm3 = False 
        
        for entry in urls:
            if len(entry) == 8:
                url, num_qubits, shots, user, circuit_name, depth, iterator, sentinel_mode = entry
            elif len(entry) == 7:
                url, num_qubits, shots, user, circuit_name, depth, iterator = entry
                sentinel_mode = None
            elif len(entry) == 6:
                url, num_qubits, shots, user, circuit_name, depth = entry
                iterator = None
                sentinel_mode = None
            else:
                raise ValueError(f"Cada elemento de 'urls' debe tener 6, 7 o 8 campos; recibido {len(entry)}: {entry}")
            
            if "OPENQASM 3.0" in url:
                es_qasm3 = True
                code.append(url) 
                composition_qubits += int(num_qubits)
                qb.append(int(num_qubits))
                continue

            if 'algassert' in url:
                try:
                    x = requests.post(self.translator + provider + '/individual', json={'url': url, 'd': composition_qubits})
                except Exception as e:
                    print("Error in the request to the translator:", e)
                    continue
                data = json.loads(x.text)
                for elem in data.get('code', []):
                    code.append(elem)
            else:
                lines = url.split('\n')
                for i, line in enumerate(lines):
                    # === SOLUCIÓN: Aplicamos el desplazamiento de qubits de Qiskit para TODOS los proveedores ===
                    line = line.replace('qreg_q[', f'qreg_q[{composition_qubits}+')
                    line = line.replace('creg_c[', f'creg_c[{composition_qubits}+')
                    code.append(line)

            composition_qubits += int(num_qubits)
            qb.append(int(num_qubits))

        # === SOLUCIÓN: Insertamos la cabecera del motor universal (Qiskit) SIEMPRE ===
        if not es_qasm3:  
            code.insert(0,"circuit = QuantumCircuit(qreg_q, creg_c)")
            code.insert(0, f"creg_c = ClassicalRegister({composition_qubits}, 'c')")  
            code.insert(0, f"qreg_q = QuantumRegister({composition_qubits}, 'q')")  
            code.insert(0,"from numpy import pi")
            code.insert(0,"import numpy as np")
            code.insert(0,"from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit")
            code.insert(0,"from qiskit.circuit.library import MCXGate, MCMT, XGate, YGate, ZGate")
            code.append("return circuit")



    def send_shots_optimized(self,queue:list, max_qubits:int, provider:str, executeCircuit:Callable, machine:str) -> None:
        """
        Sends the URLs to the server with the minimum number of shots using the shots_optimized policy

        Args:
            queue (list): The waiting list
            max_qubits (int): The maximum number of qubits            
            provider (str): The provider of the circuit            
            executeCircuit (Callable): The function to execute the circuit            
            machine (str): The machine to execute the circuit
        """
        if len(queue) != 0:
            # Send the URLs to the server
            qb = []
            sumQb = 0
            urls = []
            iterator = queue.copy()
            iterator = sorted(iterator, key=lambda x: x[2]) #Sort the waiting list by shots ascending
            minShots = self.most_repetitive([url[2] for url in iterator]) #Get the most repetitive number of shots in the waiting list
            for url in iterator:
                if url[1]+sumQb <= max_qubits and url[2] >= minShots:
                    sumQb = sumQb + url[1]
                    urls.append(url)
                    index = queue.index(url)
                    #Reduce number of shots of the url in waiting_url instead of removing it
                    if queue[index][2] - minShots <= 0: #If the url has no shots left, remove it from the waiting list
                        queue.remove(url)
                    else:
                        old_tuple = queue[index]
                        new_tuple = old_tuple[:2] + (old_tuple[2] - minShots,) + old_tuple[3:]
                        queue[index] = new_tuple
            print(f"Sending {len(urls)} URLs to the server")
            print(urls)
            # Convert the dictionary to JSON
            code,qb = [],[]
            shotsUsr = [minShots] * len(urls) # The shots for all will be the most repetitive number of shots in the waiting list
            self.create_circuit(urls,code,qb,provider)
            data = {"code":code}
            Thread(target=executeCircuit, args=(json.dumps(data),qb,shotsUsr,provider,urls,machine)).start()
            #executeCircuit(json.dumps(data),qb,shotsUsr,provider,urls)
            self.services['shots_optimized'].timers[provider].reset()


    def send_graph_placement(self, queue, max_qubits, provider, executeCircuit, machine):
        """
        Nueva política: asigna circuitos a qubits físicos usando el grafo de la máquina, minimizando ruido y cumpliendo distancia mínima.
        """
        # Solo un hilo puede ejecutar esta política a la vez
        with self.islas_cuanticas_lock:
            print("Ejecutando política de Islas Cuánticas...")
            start_time = time.process_time()

            if not queue:
                print("⚠️ La cola está vacía, deteniendo temporizador.")
                self.services['Islas_Cuanticas'].timers[provider].stop()
                return
            
            
            # Formateo de la cola usando CircuitQueue correctamente
            formatted_queue = CircuitQueue()
            sentinel_mode = None
            for item in queue:

                circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion = item[:7]
                
                # Si hay un octavo elemento, es el modo centinela
                sentinel_mode = item[7] if len(item) > 7 else None
                if sentinel_mode:
                    sentinel_mode_batch = sentinel_mode # Lo guardamos para la siguiente iteración

                edges = self.extract_edges_from_circuit(circuit)  

                formatted_queue.add_circuit(
                    circuit_id=str(user),
                    required_qubits=num_qubits,
                    edges=edges
                )
            print(f" Cola formateada: {formatted_queue.get_queue()}")

            # Llamada al método Cola_Formateada de IslaCuantica.py
            cola_procesada, layout_fisico = Cola_Formateada(formatted_queue, provider)
            print(f" Cola procesada: {cola_procesada}")
            print(f" Layout físico asignado: {layout_fisico}")

            # Si no hay elementos seleccionados, detenemos la ejecución
            if not cola_procesada:
                print(" No se han seleccionado elementos, deteniendo ejecución.")
                self.services['Islas_Cuanticas'].timers[provider].stop()
                return

            # Obtener los IDs seleccionados
            seleccionados_ids = {str(s['id']) for s in cola_procesada}

            # Filtrar los circuitos completos correspondientes a los IDs seleccionados
            seleccionados_completos = [item for item in queue if str(item[3]) in seleccionados_ids]

            # Formatear los datos para create_circuit
            urls_for_create = [
                (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion, sentinel_mode)
                for (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion) in seleccionados_completos
            ]
            # Actualizar la cola: eliminar elementos procesados y aumentar la prioridad de los que no se procesaron

            queue[:] = [
                item[:6] + (item[6] + 1,) + item[7:]
                for item in queue
                if str(item[3]) not in seleccionados_ids
            ]

            # **Verificar si los elementos realmente se eliminaron**
            elementos_restantes = [item for item in queue if str(item[3]) in seleccionados_ids]
            if elementos_restantes:
                print(f"ERROR: Estos elementos NO se eliminaron correctamente: {elementos_restantes}")

            # **9. Ejecutar los circuitos seleccionados en un solo hilo para evitar concurrencia descontrolada**
                # Mostrar por pantalla la suma de qubits en todos los circuitos a ejecutar
            if urls_for_create:
                total_qbits = sum(item[1] for item in urls_for_create)
                print(f"Suma total de qubits a ejecutar: {total_qbits}")
            # Ejecución con layout físico
           
            if urls_for_create:
                total_qbits = sum(item[1] for item in urls_for_create)
                print(f"Suma total de qubits a ejecutar: {total_qbits}")
                code, qb = [], []
                shotsUsr = [item[2] for item in urls_for_create]
                self.create_circuit(urls_for_create, code, qb, provider)
                data = {"code": code}
                Thread(target=executeCircuit, args=(json.dumps(data), qb, shotsUsr, provider, urls_for_create, machine, layout_fisico)).start()

            end_time = time.process_time()  # Finalizar el timer
            elapsed_time = end_time - start_time  # Calcular el tiempo transcurrido
            print(f"Tiempo de ejecución de send: {elapsed_time:.6f} segundos en Islas Cuánticas")

            with open("./SalidaIslasCuanticas.txt", 'a') as file:
                file.write("Cola Formateada:")
                file.write(str(formatted_queue))
                file.write("\n")
                file.write("Cola Seleccionada:")
                file.write(str(cola_procesada))
                file.write("\n")
                file.write("Layout Físico:")
                file.write(str(layout_fisico))  
                file.write("\n")
                file.write("Suma total de qubits a ejecutar:")
                file.write(str(total_qbits))
                file.write("\n")
                file.write("Tiempo Ejecucion:")
                file.write(str(elapsed_time))
                file.write("\n")

            # **10. Verificar si la cola está vacía antes de reiniciar el temporizador**
            if not queue:
                print(" Cola vacía después de ejecución, deteniendo temporizador.")
                self.services['Islas_Cuanticas'].timers[provider].stop()
            else:
                self.services['Islas_Cuanticas'].timers[provider].reset()

    def send_graph_placement_edges(self, queue, max_qubits, provider, executeCircuit, machine):
        """
        Política que asigna circuitos a qubits físicos usando el grafo + edges de los circuitos.
        """
        with self.islas_cuanticas_lock:
            print("Ejecutando política de Islas Cuánticas (con edges)...")
            start_time = time.process_time()

            if not queue:
                print("⚠️ La cola está vacía, deteniendo temporizador.")
                self.services['Islas_Cuanticas_Edges'].timers[provider].stop()
                return

            # Proveedor que se esta utilizando
            print(f"Proveedor seleccionado: {provider}")

            formatted_queue = CircuitQueue()
            
            # 📝 CAMBIO 1: Inicializamos la variable para guardar el modo del centinela
            sentinel_mode_batch = None 
            
            # 📝 CAMBIO 2: Leemos la tupla de forma segura, tenga 7 u 8 elementos
            for item in queue:
                circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion = item[:7]
                
                # Si hay un octavo elemento, lo guardamos como el modo del centinela
                if len(item) > 7:
                    sentinel_mode_batch = item[7]
                    
                edges = self.extract_edges_from_circuit(circuit) 
                formatted_queue.add_circuit(
                    circuit_id=str(user),
                    required_qubits=num_qubits,
                    edges=edges
                )
            print(f"Cola formateada con edges: {formatted_queue.get_queue()}")

            # 📝 CAMBIO 3: Le pasamos la variable capturada a la función de IslasCuanticas_Edges.py
            cola_procesada, layout_fisico = Cola_Formateada_edges(formatted_queue, provider, sentinel_mode=sentinel_mode_batch)
            
            print(f" Cola procesada: {cola_procesada}")
            print(f" Layout físico asignado: {layout_fisico}")

            if not cola_procesada:
                print(" No se han seleccionado elementos, deteniendo ejecución.")
                self.services['Islas_Cuanticas_Edges'].timers[provider].stop()
                return

            seleccionados_ids = {str(s['id']) for s in cola_procesada}
            seleccionados_completos = [item for item in queue if str(item[3]) in seleccionados_ids]

            # 📝 CAMBIO 4: Mantenemos la estructura de la tupla intacta para urls_for_create
            urls_for_create = [item for item in seleccionados_completos]

            # 📝 CAMBIO 5: Sumamos 1 a la iteración (índice 6) respetando si existe el centinela al final
            queue[:] = [
                item[:6] + (item[6] + 1,) + item[7:]
                for item in queue
                if str(item[3]) not in seleccionados_ids
            ]

            if urls_for_create:
                total_qbits = sum(item[1] for item in urls_for_create)
                print(f"Suma total de qubits a ejecutar: {total_qbits}")
                code, qb = [], []
                shotsUsr = [item[2] for item in urls_for_create]
                self.create_circuit(urls_for_create, code, qb, provider)
                data = {"code": code}
                Thread(target=executeCircuit, args=(json.dumps(data), qb, shotsUsr, provider, urls_for_create, machine, layout_fisico)).start()

            end_time = time.process_time()
            elapsed_time = end_time - start_time
            print(f"Tiempo de ejecución de send_edges: {elapsed_time:.6f} segundos")

            with open("./SalidaIslasCuanticasEdges.txt", 'a') as file:               
                file.write("Cola Formateada con edges:")
                file.write(str(formatted_queue))
                file.write("\n")
                file.write("Cola Seleccionada:")
                file.write(str(cola_procesada))
                file.write("\n")
                file.write("Layout Físico:")
                file.write(str(layout_fisico))
                file.write("\n")
                file.write("Tiempo Ejecucion:")
                file.write(str(elapsed_time))
                file.write("\n")

            if not queue:
                print(" Cola vacía después de ejecución, deteniendo temporizador.")
                self.services['Islas_Cuanticas_Edges'].timers[provider].stop()
            else:
                self.services['Islas_Cuanticas_Edges'].timers[provider].reset()
        

    def extract_edges_from_circuit(self, circuit_code: str):
        """
        Extrae las 'edges' (conexiones lógicas entre qubits) de un código Qiskit
        en formato de texto como los que tienes en la cola:
          circuit.cx(qreg_q[0], qreg_q[1])
          circuit.ccx(qreg_q[0], qreg_q[1], qreg_q[2])
          circuit.swap(qreg_q[3], qreg_q[4])
        Devuelve una lista de tuplas (q_phys_a, q_phys_b) con q_phys_a < q_phys_b.
        NO ejecuta el código del circuito.
        """
        if not circuit_code:
            return []

        edges = set()
        # Recorremos línea a línea
        for line in circuit_code.splitlines():
            line = line.strip()
            if not line:
                continue

            # Queremos sólo las llamadas tipo 'circuit.<gate>(...)'
            m = re.match(r'circuit\.(\w+)\s*\((.*)\)\s*', line)
            if not m:
                continue

            gate = m.group(1).lower()
            args = m.group(2)

            # Extraer todas las ocurrencias qreg_q[...]
            bracket_contents = re.findall(r'qreg_q\[\s*([^\]]+)\s*\]', args)
            qubits = []
            for inner in bracket_contents:
                # Extraemos todos los números dentro del interior del corchete
                nums = re.findall(r'(\d+)', inner)
                if not nums:
                    # Si no hay números, no podemos resolver el índice -> lo ignoramos
                    # (por ejemplo si aparece 'composition_qubits+X' sin valores numéricos)
                    continue
                # Sumamos los números que aparezcan en el interior (maneja '4+2' -> 6)
                idx = sum(int(n) for n in nums)
                qubits.append(idx)

            # Si hay >=2 qubits en la instrucción, agregamos las aristas (pares)
            if len(qubits) >= 2:
                for a, b in combinations(qubits, 2):
                    edges.add(tuple(sorted((a, b))))

            # Puertas de 1 qubit no generan edges (medida, h, x, y, z, t, ...)
            # Si deseas soportar puertas específicas que implican conectividad distinta,
            # añádelas aquí.

        # devolver como lista ordenada para estabilidad
        return sorted(edges)
            
            

        

    def send_ML(self, queue: list, max_qubits: int, provider: str, executeCircuit: Callable, machine: str) -> None:
        """
        Ejecuta la política de optimización basada en Machine Learning,
        asegurando que no se envíen circuitos si la cola de IBM ya tiene 3 o más trabajos en espera.
        """
        print("Ejecutando política ML...")
        start_time = time.process_time()  # Iniciar el timer


        if not queue:
            print(" La cola está vacía, deteniendo temporizador.")
            self.services['Optimizacion_ML'].timers[provider].stop()
            return

        if provider == 'ibm':
            # 1. Verificar la cola de IBM antes de ejecutar cualquier circuito
            while self.get_ibm_queue_length() >= 3:
                print(" La cola de IBM tiene 3 o más trabajos en espera. Esperando para enviar circuitos...")
                time.sleep(10)  # Esperamos 10 segundos antes de volver a verificar

            ibm_queue_length = self.get_ibm_queue_length()
            ##print(f" La cola de IBM tiene {ibm_queue_length} trabajos en espera. Continuando con la ejecución.")
        # 2. Formatear la cola para ML
        formatted_queue = [(str(user), num_qubits, iteracion) for (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion) in queue]
        print(f" Cola formateada para ML: {formatted_queue}")

        # 3. Selección de circuitos usando ML o incluyendo todos si caben
        total_qb = sum(item[1] for item in formatted_queue)
        seleccionados, _, nueva_cola = optimizar_espacio_ml(self.model, formatted_queue, max_qubits, self.forced_threshold)

        max_qbits = sum(item[1] for item in seleccionados)
        ##print(f" Elementos seleccionados en ML: {seleccionados}")
        ##print(f" Suma total de qubits seleccionados: {max_qbits}")

        # 4. Si no hay elementos seleccionados, detenemos la ejecución
        if not seleccionados:
            print(" No se han seleccionado elementos, deteniendo ejecución.")
            self.services['Optimizacion_ML'].timers[provider].stop()
            return

        # 5. Obtener los IDs seleccionados
        seleccionados_ids = {str(s['user']) for s in seleccionados}

        # 6. Filtrar los circuitos completos correspondientes a los IDs seleccionados
        seleccionados_completos = [item for item in queue if str(item[3]) in seleccionados_ids]

        # 7. Formatear los datos para create_circuit
        urls_for_create = [(circuit, num_qubits, shots, user, circuit_name, maxDepth) for (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion) in seleccionados_completos]

      # 8. Actualizar la cola: eliminar elementos procesados y aumentar la prioridad de los que no se procesaron
        queue[:] = [
            (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion + 1)
            for (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion) in queue
                if str(user) not in seleccionados_ids

]

        # **Verificar si los elementos realmente se eliminaron**
        elementos_restantes = [item for item in queue if str(item[3]) in seleccionados_ids]
        if elementos_restantes:
            print(f" ERROR: Estos elementos NO se eliminaron correctamente: {elementos_restantes}")

        # **9. Ejecutar los circuitos seleccionados en un solo hilo para evitar concurrencia descontrolada**
        if urls_for_create:
            code, qb = [], []
            shotsUsr = [item[2] for item in urls_for_create]
            self.create_circuit(urls_for_create, code, qb, provider)
            data = {"code": code}

            Thread(target=executeCircuit, args=(json.dumps(data), qb, shotsUsr, provider, urls_for_create, machine)).start()
        
        end_time = time.process_time()  # Finalizar el timer
        elapsed_time = end_time - start_time  # Calcular el tiempo transcurrido
        print(f"Tiempo de ejecución de send: {elapsed_time:.6f} segundos en ML")

        with open("./SalidaML.txt", 'a') as file:
            file.write("Cola Formateada:")
            file.write(str(formatted_queue))
            file.write("\n")
            file.write("Cola Seleccionada:")
            file.write(str(seleccionados))
            file.write("\n")
            file.write("Qbits alcanzados: ")
            file.write(str(max_qbits))  
            file.write("\n")
            file.write("Tiempo Ejecucion:")
            file.write(str(elapsed_time))
            file.write("\n")



        # **10. Verificar si la cola está vacía antes de reiniciar el temporizador**
        if not queue:
            print(" Cola vacía después de ejecución, deteniendo temporizador.")
            self.services['Optimizacion_ML'].timers[provider].stop()
        else:
            self.services['Optimizacion_ML'].timers[provider].reset()

    def send_PD(self, queue: list, max_qubits: int, provider: str, executeCircuit: Callable, machine: str) -> None:
        """
        Ejecuta la política de optimización basada en Programacion Dinamica.
        """
        print("Ejecutando política Programación Dinamica...")
        start_time = time.process_time()  # Iniciar el timer


        if not queue:
            print(" La cola está vacía, deteniendo temporizador.")
            self.services['Optimizacion_PD'].timers[provider].stop()
            return
        
                # 1. Verificar la cola de IBM antes de ejecutar cualquier circuito
        while self.get_ibm_queue_length() >= 3:
            print(" La cola de IBM tiene 3 o más trabajos en espera. Esperando para enviar circuitos...")
            time.sleep(10)  # Esperamos 10 segundos antes de volver a verificar

        ibm_queue_length = self.get_ibm_queue_length()
        ##print(f" La cola de IBM tiene {ibm_queue_length} trabajos en espera. Continuando con la ejecución.")

        # 1. Formatear la cola para ML
        formatted_queue = [(str(user), num_qubits, iteracion) for (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion) in queue]
        print(f" Cola formateada para PD: {formatted_queue}")


        # 2. Selección de circuitos usando ML o incluyendo todos si caben
        total_qb = sum(item[1] for item in formatted_queue)

        seleccionados, _, nueva_cola = optimizar_espacio_dinamico( formatted_queue, max_qubits, self.forced_threshold)
        
        max_qbits = sum(item[1] for item in seleccionados)

        # 3. Si no hay elementos seleccionados, detenemos la ejecución
        if not seleccionados:
            print("⚠️ No se han seleccionado elementos, deteniendo ejecución.")
            self.services['Optimizacion_PD'].timers[provider].stop()
            return

        # 4. Obtener los IDs seleccionados
        seleccionados_ids = {str(s[0]) for s in seleccionados}

        # 5. Filtrar los circuitos completos correspondientes a los IDs seleccionados
        seleccionados_completos = [item for item in queue if str(item[3]) in seleccionados_ids]

        # 6. Formatear los datos para create_circuit
        urls_for_create = [(circuit, num_qubits, shots, user, circuit_name, maxDepth) for (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion) in seleccionados_completos]

        # **7. Eliminar de la cola ANTES de ejecutar `executeCircuit`**
        queue[:] = [
            (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion + 1)
            for (circuit, num_qubits, shots, user, circuit_name, maxDepth, iteracion) in queue
                if str(user) not in seleccionados_ids]
        #queue[:] = [item for item in queue if str(item[3]) not in seleccionados_ids]

        # **Verificar si los elementos realmente se eliminaron**
        elementos_restantes = [item for item in queue if str(item[3]) in seleccionados_ids]
        if elementos_restantes:
            print(f" ERROR: Estos elementos NO se eliminaron correctamente: {elementos_restantes}")

        # **8. Ejecutar los circuitos seleccionados en un solo hilo para evitar concurrencia descontrolada**
        if urls_for_create:
            code, qb = [], []
            shotsUsr = [item[2] for item in urls_for_create]
            self.create_circuit(urls_for_create, code, qb, provider)
            data = {"code": code}


            Thread(target=executeCircuit, args=(json.dumps(data), qb, shotsUsr, provider, urls_for_create, machine)).start()


        end_time = time.process_time()  # Finalizar el timer
        elapsed_time = end_time - start_time  # Calcular el tiempo transcurrido
        ##print(f"Tiempo de ejecución de send: {elapsed_time:.6f} segundos")

        with open("./SalidaPD.txt", 'a') as file:
            file.write("Cola Formateada:")
            file.write(str(formatted_queue))
            file.write("\n")
            file.write("Cola Seleccionada:")
            file.write(str(seleccionados))
            file.write("\n")
            file.write("Qbits alcanzados: ")
            file.write(str(max_qbits))  
            file.write("\n")
            file.write("Tiempo Ejecucion:")
            file.write(str(elapsed_time))
            file.write("\n")

        # **9. Verificar si la cola está vacía antes de reiniciar el temporizador**
        if not queue:
            ##print("✅ Cola vacía después de ejecución, deteniendo temporizador.")
            self.services['Optimizacion_PD'].timers[provider].stop()
        else:
            ##print("🔁 La cola aún tiene elementos, reiniciando temporizador.")
            self.services['Optimizacion_PD'].timers[provider].reset()     








    def send_shots_depth(self,queue:list, max_qubits:int, provider:str, executeCircuit:Callable, machine:str) -> None:
        """
        Sends the URLs to the server with the minimum number of shots and similar depth using the shots_depth policy

        Args:
            queue (list): The waiting list            
            max_qubits (int): The maximum number of qubits            
            provider (str): The provider of the circuit            
            executeCircuit (Callable): The function to execute the circuit            
            machine (str): The machine to execute the circuit
        """
        # Send the URLs to the server
        if len(queue) != 0:
            qb = []
            sumQb = 0
            urls = []
            iterator = queue.copy()
            iterator = sorted(iterator, key=lambda x: x[2]) #Sort the waiting list by shots ascending
            minShots = iterator[0][2] #Get the minimum number of shots in the waiting list
            depth = iterator[0][5] #Get the depth of the first url in the waiting list
            for url in iterator:
                if url[1]+sumQb <= max_qubits and url[5] <= depth * 1.1 and url[5] >= depth * 0.9:
                    sumQb = sumQb + url[1]
                    urls.append(url)
                    index = queue.index(url)
                    #Reduce number of shots of the url in waiting_url instead of removing it
                    if queue[index][2] - minShots <= 0: #If the url has no shots left, remove it from the waiting list
                        queue.remove(url)
                    else:
                        old_tuple = queue[index]
                        new_tuple = old_tuple[:2] + (old_tuple[2] - minShots,) + old_tuple[3:]
                        queue[index] = new_tuple
            print(f"Sending {len(urls)} URLs to the server")
            print(urls)
            code,qb = [],[]
            shotsUsr = [minShots] * len(urls) # The shots for all will be the minimum number of shots in the waiting list
            self.create_circuit(urls,code,qb,provider)
            data = {"code":code}
            Thread(target=executeCircuit, args=(json.dumps(data),qb,shotsUsr,provider,urls,machine)).start()
            executeCircuit(json.dumps(data),qb,shotsUsr,provider,urls)
            self.services['shots_depth'].timers[provider].reset()

    def send_depth(self,queue:list, max_qubits:int, provider:str, executeCircuit:Callable, machine:str) -> None:
        """
        Sends the URLs to the server with the most similar depth using the depth policy

        Args:
            queue (list): The waiting list
            max_qubits (int): The maximum number of qubits            
            provider (str): The provider of the circuit            
            executeCircuit (Callable): The function to execute the circuit            
            machine (str): The machine to execute the circuit
        """
        # Send the URLs to the server
        if len(queue) != 0:
            print('Sent')
            qb = []
            # Convert the dictionary to JSON
            urls = []
            sumQb = 0
            depth = queue[0][5] #Get the depth of the first url in the waiting list
            iterator = queue.copy()
            iterator = iterator[:1] + sorted(iterator[1:], key=lambda x: abs(x[5] - depth)) #Sort the waiting list by difference in depth by the first circuit in the waiting list so it picks the most similar circuit (dont sort the first element because is the reference for the calculation)
            for url in iterator: #Add them to the valid_url only if they fit and are similar to the first circuit in the waiting list
                if url[1]+ sumQb <= max_qubits and url[5] <= depth * 1.1 and url[5] >= depth * 0.9:
                    urls.append(url)
                    sumQb += url[1]
                    queue.remove(url)
            print(f"Sending {len(urls)} URLs to the server")
            print(urls)
            code,qb = [],[]
            shotsUsr = [url[2] for url in urls] #Each one will have its own number of shots, a statistic will be used to get the results after
            self.create_circuit(urls,code,qb,provider)
            data = {"code":code}
            Thread(target=executeCircuit, args=(json.dumps(data),qb,shotsUsr,provider,urls,machine)).start()
            #executeCircuit(json.dumps(data),qb,shotsUsr,provider,urls)
            self.services['depth'].timers[provider].reset()

    def send_shots(self,queue:list, max_qubits:int, provider:str, executeCircuit:Callable, machine:str) -> None:
        """
        Sends the URLs to the server with the minimum number of shots using the shots policy

        Args:
            queue (list): The waiting list            
            max_qubits (int): The maximum number of qubits            
            provider (str): The provider of the circuit            
            executeCircuit (Callable): The function to execute the circuit            
            machine (str): The machine to execute the circuit
        """
        # Send the URLs to the server
        if len(queue) != 0:
            print('Sent')
            qb = []
            sumQb = 0
            urls = []
            iterator = queue.copy()
            iterator = sorted(iterator, key=lambda x: x[2]) #Sort the waiting list by shots ascending
            minShots = iterator[0][2] #Get the minimum number of shots in the waiting list
            for url in iterator:
                if url[1]+sumQb <= max_qubits:
                    sumQb = sumQb + url[1]
                    urls.append(url)
                    index = queue.index(url)
                    #Reduce number of shots of the url in waiting_url instead of removing it
                    if queue[index][2] - minShots <= 0: #If the url has no shots left, remove it from the waiting list
                        queue.remove(url)
                    else:
                        old_tuple = queue[index]
                        new_tuple = old_tuple[:2] + (old_tuple[2] - minShots,) + old_tuple[3:]
                        queue[index] = new_tuple
            code,qb = [],[]
            shotsUsr = [minShots] * len(urls) # All the urls will have the minimum number of shots in the waiting list
            self.create_circuit(urls,code,qb,provider)
            data = {"code":code}
            Thread(target=executeCircuit, args=(json.dumps(data),qb,shotsUsr,provider,urls,machine)).start() #Parece que sin esto no se resetea el timer cuando termina de componer
            executeCircuit(json.dumps(data),qb,shotsUsr,provider,urls)
            self.services['shots'].timers[provider].reset()

    def send(self,queue:list, max_qubits:int, provider:str, executeCircuit:Callable, machine:str) -> None:
        """
        Sends the URLs to the server using the time policy

        Args:
            queue (list): The waiting list            
            max_qubits (int): The maximum number of qubits            
            provider (str): The provider of the circuit            
            executeCircuit (Callable): The function to execute the circuit            
            machine (str): The machine to execute the circuit
        """
        start_time = time.process_time()  # Iniciar el timer


        if len(queue) != 0:
            print('Sent')
            urls = []
            iterator = queue.copy() #Make a copy to not delete on search
            sumQb = 0
            for url in iterator:
                if url[1] + sumQb <= max_qubits: #Shots of current url + shots of all the urls on urls
                    urls.append(url)
                    sumQb += url[1]
                    queue.remove(url)
            code,qb = [],[]
            print("sumQb", sumQb)
            shotsUsr = [url[2] for url in urls] # Each url will have its own number of shots, a statistic will be used to get the results after
            self.create_circuit(urls,code,qb,provider)
            data = {"code":code}

            
            Thread(target=executeCircuit, args=(json.dumps(data),qb,shotsUsr,provider,urls,machine)).start()

            end_time = time.process_time()  # Finalizar el timer
            elapsed_time = end_time - start_time  # Calcular el tiempo transcurrido
            print(f"Tiempo de ejecución de send: {elapsed_time:.6f} segundos en Tiempo")

            with open("./SalidaTime.txt", 'a') as file:
                file.write("Suma de qBits:")
                file.write(str(sumQb))
                file.write("\n")
                file.write("Tiempo Ejecucion:")
                file.write(str(elapsed_time))
                file.write("\n")


            self.services['time'].timers[provider].reset()

    

    def get_ibm_machine(self) -> str:
        """
        Returns the IBM machine of the scheduler

        Returns:
            str: The IBM machine of the scheduler
        """
        return self.machine_ibm
    
    def get_ibm(self):
        return self.executeCircuitIBM
