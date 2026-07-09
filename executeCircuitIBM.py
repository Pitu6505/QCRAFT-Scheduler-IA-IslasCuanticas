#!/usr/bin/env python
# coding: utf-8

# import libraries
from platform import machine

from qiskit import transpile
import qiskit.providers
from qiskit_ibm_runtime import SamplerV2 as Sampler, QiskitRuntimeService
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCXGate
from qiskit_aer import AerSimulator
import qiskit.qasm3
import json
import os
import qiskit
import numpy as np
import re
import threading


class executeCircuitIBM:
    def __init__(self):
        self.transpile_lock = threading.Lock()
        self.condition = threading.Condition()
        self.service = self.load_account_ibm()  # Usar credenciales personalizadas
        all_jobs = self.service.jobs()
        self.queued_jobs = len([job for job in all_jobs if job.status() == qiskit.providers.JobStatus.QUEUED])  # Number of queued jobs de la cola generado


    def load_account_ibm(self) -> QiskitRuntimeService:
        """
        Loads the IBM Quantum account.

        Returns:
            QiskitRuntimeService: The service with the IBM Quantum account loaded.
        """
        # Load your IBM Quantum account
        return QiskitRuntimeService(channel="ibm_cloud",
                                   token="",
                                   instance="")

    def obtain_machine(self, service:QiskitRuntimeService ,machine:str) -> qiskit.providers.BackendV2:
        """
        Obtains the information of the machine.

        Args:
            QiskitRuntimeService: The service to obtain the machine.        
            machine (str): The machine to obtain the information.

        Returns:
            qiskit.providers.BackendV2: The IBM backend.
        """
        # Load your IBM Quantum account
        backend = service.backend(machine)
        return backend


    def code_to_circuit_ibm(self, code_str:str) -> qiskit.QuantumCircuit: 
        """
        Transforms a string representation (OpenQASM 3.0 or Python script) 
        of a circuit into a Qiskit circuit object.
        """
        # 1. Si es código OpenQASM 3.0 nativo
        if "OPENQASM 3.0" in code_str:
            try:
                circuit = qiskit.qasm3.loads(code_str)
                print("✅ Circuito cargado correctamente desde OpenQASM 3.0")
                return circuit
            except Exception as e:
                print(f"❌ Error al cargar OpenQASM 3.0: {e}")
                raise ValueError(f"Invalid QASM3 code: {e}")
                
        # 2. Si es un script de Python concatenado (Descargado de GitHub)
        else:
            try:
                local_vars = {}
                # Eliminamos el "return circuit" que inyecta create_circuit, 
                # ya que exec() explota si ve un return fuera de una función
                clean_code = code_str.replace("return circuit", "")
                
                # Ejecutamos el string de Python en un entorno seguro y capturamos las variables
                exec(clean_code, globals(), local_vars)
                
                # Rescatamos el objeto QuantumCircuit ensamblado
                if 'circuit' in local_vars:
                    return local_vars['circuit']
                else:
                    raise ValueError("No se generó el objeto 'circuit' al compilar el script.")
                    
            except Exception as e:
                print(f"❌ Error al ejecutar el código Python de Qiskit: {e}")
                raise ValueError(f"Invalid Python circuit code: {e}")


    def get_transpiled_circuit_depth_ibm(self, circuit:QuantumCircuit, backend:qiskit.providers.BackendV2) -> int:
        """
        Transpiles a circuit and returns its depth.

        Args:
            circuit (QuantumCircuit): The circuit to transpile.        
            backend (qiskit.providers.BackendV2): The machine to transpile the circuit

        Returns:
            int: The depth of the transpiled circuit.
        """
        # Load your IBM Quantum account
        with self.transpile_lock:
            qc_basis = transpile(circuit, backend=backend, optimization_level=0)

        return qc_basis.depth()


    # Ejecutar el circuito
    def runIBM(self, machine:str, circuit:QuantumCircuit, shots:int) -> dict:
        """
        Executes a circuit in the IBM cloud.

        Args:
            machine (str): The machine to execute the circuit.        
            circuit (QuantumCircuit): The circuit to execute.        
            shots (int): The number of shots to execute the circuit.

        Returns:
            dict: The results of the circuit execution.
        """

        if machine == "local":
            backend = AerSimulator()
            x = int(shots)
            job = backend.run(circuit, shots=x)
            result = job.result()
            counts = result.get_counts()
            return counts
        else:
            # Load your IBM Quantum account

            service = self.service
            backend = service.backend(machine)
            qc_basis = transpile(circuit, backend=backend, optimization_level=0)
            x = int(shots)
            job = backend.run(qc_basis, shots=x) 
            result = job.result()
            counts = result.get_counts()
            return counts

    def retrieve_result_ibm(self, id) -> dict:
        """
        Retrieves the results of a circuit execution in the IBM cloud.

        Args:
            id (str): The id of the job to retrieve the results from.

        Returns:
            dict: The results of the task execution.
        """
        # Load your IBM Quantum account
        service = self.service
        job = service.job(id)
        result = job.result()
        # counts = result[0].data.creg_c.get_counts()
        data_bin = result[0].data
        
        # Buscar todos los nombres de registros clásicos válidos
        creg_names = [k for k in dir(data_bin) if not k.startswith('_')]
        
        # Combinar los diccionarios de resultados
        counts_combinados = {}
        # Iterar sobre las filas de resultados en crudo (bitstrings)
        primer_registro = getattr(data_bin, creg_names[0])
        for i in range(primer_registro.num_shots):
            bitstring_completo = ""
            for name in creg_names:
                # Extraer el valor del bit para este shot específico
                bit_val = getattr(data_bin, name).get_int(i)
                longitud = getattr(data_bin, name).num_bits
                # Formatear a binario rellenando con ceros
                bitstring_completo += format(bit_val, f'0{longitud}b') + " "
            
            bitstring_completo = bitstring_completo.strip()
            if bitstring_completo in counts_combinados:
                counts_combinados[bitstring_completo] += 1
            else:
                counts_combinados[bitstring_completo] = 1
                
        counts = counts_combinados
        return counts

    def runIBM_save(self, machine:str, circuit:QuantumCircuit, shots:int,users:list, qubit_number:list, circuit_names:list, layout_fisico:list=None) -> dict:
        """
        Executes a circuit in the IBM cloud or locally, parsing V2 primitive results.
        """
        x = int(shots)

        if machine == "local":
            from qiskit_aer import AerSimulator
            from qiskit_aer.noise import NoiseModel, depolarizing_error
            from qiskit.primitives import BackendSamplerV2
            
            # 1. CREAR MODELO DE RUIDO (Simulando hardware NISQ)
            noise_model = NoiseModel()
            error_ruido = depolarizing_error(0.10, 1) # 10% de error para forzar a los centinelas
            noise_model.add_all_qubit_quantum_error(error_ruido, ['x', 'h', 'measure', 'delay'])
            
            backend = AerSimulator(noise_model=noise_model)
            
            # Transpilamos sin layout físico para que AerSimulator no se queje
            qc_basis = transpile(circuit, backend=backend, optimization_level=0)
                
            sampler = BackendSamplerV2(backend=backend)
            job = sampler.run([qc_basis], shots=x)
            
        else:
            # Load your IBM Quantum account
            service = self.service
            backend = service.backend(machine)
            sampler = Sampler(mode=backend)
            
            with self.transpile_lock:
                if layout_fisico is not None:
                    qc_basis = transpile(circuit, backend=backend, optimization_level=0, initial_layout=layout_fisico)
                else:
                    qc_basis = transpile(circuit, backend=backend, optimization_level=0)

            while True:
                with self.condition:   
                    if self.queued_jobs < 3:
                        self.queued_jobs += 1
                        job = sampler.run([qc_basis], shots=x)
                        break
                    else:
                        self.condition.wait()

        # ====================================================================
        # BLOQUE UNIFICADO DE PROCESAMIENTO (Para LOCAL e IBM real)
        # ====================================================================
        id = job.job_id() # Get the job id
        provider = 'ibm'
        user_shots = [shots] * len(circuit_names)
        script_dir = os.path.dirname(os.path.realpath(__file__))
        ids_file = os.path.join(script_dir, 'ids.txt')
        
        with open(ids_file, 'a') as file:
            file.write(json.dumps({id:(users,qubit_number, user_shots, provider, circuit_names)}))
            file.write('\n')

        result = job.result()
        data_bin = result[0].data
        
        creg_names = [k for k in dir(data_bin) if not k.startswith('_') and hasattr(getattr(data_bin, k), 'get_bitstrings')]
        
        bitstrings_por_registro = {}
        for name in creg_names:
            bitstrings_por_registro[name] = getattr(data_bin, name).get_bitstrings()
        
        counts_combinados = {}
        
        if creg_names:
            primer_nombre = creg_names[0]
            num_shots = len(bitstrings_por_registro[primer_nombre])
            
            registros_datos = [name for name in creg_names if name != 'c_flag']
            
            for i in range(num_shots):
                # FILTRO FTQC
                if 'c_flag' in creg_names and '1' in bitstrings_por_registro['c_flag'][i]:
                    continue
                    
                bitstring_completo = "".join([bitstrings_por_registro[name][i] for name in registros_datos])
                
                if bitstring_completo in counts_combinados:
                    counts_combinados[bitstring_completo] += 1
                else:
                    counts_combinados[bitstring_completo] = 1
                    
        counts = counts_combinados

        # Liberar la cola solo si estamos en hardware real
        if machine != "local":
            with self.condition:
                self.queued_jobs -= 1
                self.condition.notify()

        # Limpiar el ID del archivo
        with open(ids_file, 'r') as file:
            lines = file.readlines()
        with open(ids_file, 'w') as file:
            for line in lines:
                line_dict = json.loads(line.strip())
                if list(line_dict.keys())[0] != id:
                    file.write(line)

        return counts