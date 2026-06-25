#!/usr/bin/env python
# coding: utf-8

# import libraries
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


    def code_to_circuit_ibm(self, code_str:str) -> qiskit.QuantumCircuit: #Inverse parser to get the circuit object from the string
        """
        Transforms a string representation (OpenQASM 3.0) of a circuit into a Qiskit circuit
        utilizando el parser nativo de Qiskit.
        """
        try:
            # Cargamos directamente el string en formato OpenQASM 3.0
            circuit = qiskit.qasm3.loads(code_str)
            print(f"✅ Circuito cargado correctamente desde OpenQASM 3.0: {circuit}")
            return circuit
            
        except Exception as e:
            print(f"❌ Error al cargar OpenQASM 3.0: {e}")
            raise ValueError(f"Invalid circuit code (OpenQASM 3 expected): {e}")


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
            qc_basis = transpile(circuit, backend=backend)

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
            qc_basis = transpile(circuit, backend=backend)
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
        counts = result[0].data.creg_c.get_counts()
        return counts

    def runIBM_save(self, machine:str, circuit:QuantumCircuit, shots:int,users:list, qubit_number:list, circuit_names:list) -> dict:
        """
        Executes a circuit in the IBM cloud and saves the task id if the machine crashes.

        Args:
            machine (str): The machine to execute the circuit.        
            circuit (QuantumCircuit): The circuit to execute.        
            shots (int): The number of shots to execute the circuit.        
            users (list): The users that executed the circuit.        
            qubit_number (list): The number of qubits of the circuit per user.        
            circuit_names (list): The name of the circuit that was executed per user.

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
            sampler = Sampler(mode=backend)
            #sampler.options.execution.rep_delay = 0.5 # set it to the maximum of the machine instead -> config.rep_delay_range[1]
            with self.transpile_lock:
                qc_basis = transpile(circuit, backend=backend)
            x = int(shots)

            while True:
                with self.condition:   
                    if self.queued_jobs < 3:
                        self.queued_jobs += 1
                        job = sampler.run([qc_basis], shots=x)
                        break
                    else:
                        self.condition.wait()


            # -----------------------------------------------------#
            id = job.job_id() # Get the job id
            provider = 'ibm'
            user_shots = [shots] * len(circuit_names)
            script_dir = os.path.dirname(os.path.realpath(__file__))
            ids_file = os.path.join(script_dir, 'ids.txt')  # create the path to the results file in the script's directory
            with open(ids_file, 'a') as file:
                file.write(json.dumps({id:(users,qubit_number, user_shots, provider, circuit_names)}))
                file.write('\n')
            # Write the id in a file, along with the users, and their qubit numbers
            # -----------------------------------------------------#

            result = job.result()
            counts = result[0].data.creg_c.get_counts()

            with self.condition:
                self.queued_jobs -= 1
                self.condition.notify()

            # -----------------------------------------------------#

            #Seach for the id in the file and delete the line
            with open(ids_file, 'r') as file:
                lines = file.readlines()
            with open(ids_file, 'w') as file:
                for line in lines:
                    line_dict = json.loads(line.strip())
                    if list(line_dict.keys())[0] != id:
                        file.write(line)

            # -----------------------------------------------------#

            return counts
