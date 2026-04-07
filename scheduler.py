from urllib.parse import urlparse, urlunparse
import json
import ast
from urllib.parse import unquote
from flask import Flask, request
import socket
import requests
from divideResults import divideResults
import logging
import uuid
import re
from scheduler_policies import SchedulerPolicies
from executeCircuitIBM import executeCircuitIBM
from executeCircuitAWS import retrieve_result_aws, code_to_circuit_aws
import os
from threading import Thread, Lock
from flask import jsonify
from pymongo import MongoClient
from bson.json_util import dumps
from dotenv import load_dotenv

class Scheduler:
    """
    Class to manage the petitions of quantum circuit scheduling.
    """
    def __init__(self):
        """
        Initialize the scheduler

        Attributes:
            app (Flask): The Flask app
            ports (dict): The ports used by the scheduler
            max_qubits (int): The maximum number of qubits            
            client (MongoClient): The MongoDB client            
            db (MongoClient): The MongoDB database            
            collection (MongoClient): The MongoDB collection            
            translator (str): The URL of the translator            
            policy_service (str): The URL of the policy service            
            scheduler_policies (SchedulerPolicies): The scheduler policies            
            result_lock (Lock): The lock for the results
        """
        self.app = Flask(__name__)
        self.ports = {}

        dotenv_path = os.path.join(os.path.dirname(__file__), 'db', '.env')
        load_dotenv(dotenv_path)

        self.app.config['HOST'] = os.getenv('HOST')
        self.app.config['PORT'] = os.getenv('PORT')
        self.app.config['TRANSLATOR'] = os.getenv('TRANSLATOR')
        self.app.config['TRANSLATOR_PORT'] = os.getenv('TRANSLATOR_PORT')
        self.app.config['DB'] = os.getenv('DB')
        self.app.config['DB_PORT'] = os.getenv('DB_PORT')
        self.app.config['LOCAL_RESULT_ENDPOINT'] = os.getenv('LOCAL_RESULT_ENDPOINT', 'http://localhost:5000')
        
        self.max_qubits =156 
        
        mongo_uri = f"mongodb://{self.app.config['DB']}:{self.app.config['DB_PORT']}/{os.getenv('DB_NAME')}"
        self.client = MongoClient(mongo_uri)
        self.db = self.client[os.getenv('DB_NAME')]
        self.collection = self.db[os.getenv('DB_COLLECTION')]

        self.translator = f"http://{self.app.config['TRANSLATOR']}:{self.app.config['TRANSLATOR_PORT']}/code/"
        self.policy_service = f"http://{self.app.config['HOST']}:{self.app.config['PORT']}/service/"
        self.local_result_endpoint = self.app.config['LOCAL_RESULT_ENDPOINT']

        self.scheduler_policies = SchedulerPolicies(self.app)

        self.executeCircuitIBM = self.scheduler_policies.get_ibm()

        self.transpilation_machine = self.scheduler_policies.get_ibm_machine()
        self.service = self.executeCircuitIBM.load_account_ibm()

        if self.transpilation_machine != 'local': self.transpilation_backend = self.executeCircuitIBM.obtain_machine(self.service, self.transpilation_machine)

        self.app.route('/url', methods=['POST'])(self.store_url)
        self.app.route('/circuit', methods=['POST'])(self.store_url_circuit)
        self.app.route('/unscheduler', methods=['POST'])(self.unschedule_route)
        self.app.route('/result', methods=['GET'])(self.sendResults)

        self.result_lock = Lock()   

        # Check if the file with the jobs is not empty, go to each job id and search the data (execute the unscheduler to each one to retrieve the divided results), then delete the job id from the file (do this on a different thread to do job.result() in the case the job has not finished yet)
        Thread(target=self.check_ids).start()

        @self.app.errorhandler(404)
        def not_found_error(error):
            return 'This route does not exist', 404

        @self.app.errorhandler(500)
        def internal_error(error):
            return 'Internal server error', 500

    def run(self) -> None:
        """
        Run the scheduler
        """
        self.updatePorts()
        print('hecho')
        self.app.run(host='0.0.0.0', port=self.app.config['PORT'], debug=False)

    def handle_line(self, line:str,ids_file:str,lock:Lock) -> None:
        """
        Handle the line of the file with the ids to retrieve the result of pending tasks

        Args:
            line (str): The line of the file            
            ids_file (str): The file with the ids            
            lock (Lock): The lock for the file
        """
        fdata = json.loads(line)
        id = list(fdata.keys())[0]
        users = fdata[id][0]
        qubit_number = fdata[id][1]
        shots = fdata[id][2]
        provider = fdata[id][3]
        if provider == 'ibm':
            counts = self.executeCircuitIBM.retrieve_result_ibm(id) 
        elif provider == 'aws':
            counts = retrieve_result_aws(id)
        circuit_names = fdata[id][4]
        self.unscheduler(counts,shots,provider,qubit_number,users,circuit_names)
        # Delete that element from the file
        with lock:
            #ids.append(id) # TODO if the file is not edited here and the machine crashes before all threads finish, it could potentially lead to data duplication. However, editing the file only once (after thread.join) is more efficient
            with open(ids_file, 'r') as file:
                lines = file.readlines()
            with open(ids_file, 'w') as file:
                for line in lines:
                    line_dict = json.loads(line.strip())
                    if list(line_dict.keys())[0] != id:
                        file.write(line)

    def check_ids(self) -> None:
        """
        Check the ids in the file
        """
        script_dir = os.path.dirname(os.path.realpath(__file__))
        ids_file = os.path.join(script_dir, 'ids.txt')# Probar con {"crwxm1gy7jt00080brsg": [[138858145774110440281622187370607091923, 29911186310521936172191454839193631165], [2, 2], [10000, 10000], "ibm", ["qaoa.py", "qaoa.py"]]}
        with open(ids_file, 'r') as file:
            lines = file.readlines()
        
        lock = Lock()

        #ids = []

        threads = []
        for line in lines:
            t = Thread(target=self.handle_line, args=(line,ids_file,lock))
            t.start()
            threads.append(t)

        #for thread in threads:
        #   thread.join()

        #with open(ids_file, 'w') as file:
        #    for line in lines:
        #        line_dict = json.loads(line.strip())
        #        if list(line_dict.keys())[0] not in ids:
        #            file.write(line)        

    def select_policy(self, url:str, num_qubits:int, shots:int, user:int, circuit_name:str, maxDepth:int, provider:str, policy:str) -> None:
        """
        Select the policy to execute the circuit and send a post request to the policy service

        Args:
            url (str): The URL of the circuit            
            num_qubits (int): The number of qubits of the circuit
            shots (int): The number of shots to execute the circuit            
            user (int): The user that executed the circuit    
            circuit_name (str): The name of the circuit            
            maxDepth (int): The maximum depth of the circuit            
            provider (str): The provider to execute the circuit            
            policy (str): The policy to execute the circuit
        """
        data = {"circuit": url, "num_qubits": num_qubits, "shots": shots, "user": user, "circuit_name": circuit_name, "maxDepth": maxDepth, "provider": provider , "Iteracion": 1} # Modificaco aqui la cola para la prioridad 
        requests.post(self.policy_service+policy, json=data)
        

    def unschedule_route(self) -> tuple:
        """
        Route to unschedule a circuit

        Returns:
            tuple: The response of the unscheduler
        """
        data = request.get_json()
        self.unscheduler(data['counts'], data['shots'], data['provider'], data['qb'], data['users'], data['circuit_names'])
        return jsonify({'status': 'success'}), 200

    def unscheduler(self, counts:dict, shots:int, provider:str, qb:list, users:list, circuit_names:list) -> tuple:
        """
        Unschedule a circuit

        Args:
            counts (dict): The results of the circuit execution            
            shots (int): The number of shots that the circuit was executed            
            provider (str): The provider of the circuit execution            
            qb (list): The number of qubits of the circuit            
            users (list): The users that executed the circuit            
            circuit_names (list): The name of the circuit that was executed

        Returns:
            tuple: The response of the unscheduler
        """

        results = divideResults(counts,shots,provider,qb,users,circuit_names)

        # Forward execution results to a local consumer service.
        self.forward_results_local(counts, shots, provider, qb, users, circuit_names, results)

        #Save the content of results in a file   
        for dividedResult in results:
            for key, value in dividedResult.items():
                # Split the key into the id and the circuit name
                id, circuit_name = key
                sanitized_value = {}
                for result_key, result_count in value.items():
                    safe_key = str(result_key)
                    if safe_key == '':
                        safe_key = '_empty'
                    # MongoDB field names cannot start with '$' and cannot contain '.'
                    if safe_key.startswith('$'):
                        safe_key = '_' + safe_key[1:]
                    safe_key = safe_key.replace('.', '_')
                    sanitized_value[safe_key] = result_count
                # Create the update document
                update = {'$inc': {'value.' + k: v for k, v in sanitized_value.items()}}
                # Upsert the document, Quitar esto
                with self.result_lock: #In the case provider is both so the data retrieval is done after the first update finishes
                    self.collection.update_one({'_id': str(id), 'circuit': circuit_name}, update, upsert=True)

        return "Results stored successfully", 200  # Return a response

    def schedule_from_code(self, circuit:str, provider:str, shots:int, user:int, circuit_name:str, policy:str) -> tuple:
        """
        Schedule a circuit execution from Python source code.

        Args:
            circuit (str): Python source code of the circuit.
            provider (str): Provider to execute the circuit ('ibm' or 'aws').
            shots (int): Number of shots.
            user (int): User id associated with the request.
            circuit_name (str): Name to identify the circuit.
            policy (str): Scheduling policy.

        Returns:
            tuple: Response with scheduler task identification.
        """
        lines = circuit.split('\n')
        importAWS = next((line for line in lines if 'braket.circuits' in line), None)
        importIBM = next((line for line in lines if 'qiskit' in line), None)

        if isinstance(provider, list):
            provider = provider[0] if provider else 'ibm'
        provider = provider.lower()

        if provider not in ['ibm', 'aws']:
            return "Invalid provider", 400

        if provider == 'ibm':
            if not importIBM:
                return "Provider and circuit code do not match (IBM code expected)", 400

            try:
                circ = self.executeCircuitIBM.code_to_circuit_ibm(circuit)
            except (ValueError, Exception) as e:
                return f"Invalid circuit code: {e}", 400
            if circ is None:
                return "Invalid circuit code", 400
            num_qubits = circ.num_qubits

            if num_qubits > self.max_qubits:
                return "Circuit too large", 400

            if self.transpilation_machine == 'local':
                maxDepth = circ.depth()
            else:
                maxDepth = self.executeCircuitIBM.get_transpiled_circuit_depth_ibm(circ, self.transpilation_backend)

            circuit_for_queue = self.serialize_ibm_circuit_for_queue(circ)

        else:
            if not importAWS:
                return "Provider and circuit code do not match (AWS code expected)", 400
            try:
                aws_circuit = code_to_circuit_aws(circuit)
            except (ValueError, Exception) as e:
                return f"Invalid AWS circuit code: {e}", 400

            num_qubits = getattr(aws_circuit, 'qubit_count', 0)
            if num_qubits is None or num_qubits <= 0:
                return "Invalid AWS circuit code", 400
            if num_qubits > self.max_qubits:
                return "Circuit too large", 400

            # Braket has no direct depth method here; use instruction count as proxy.
            maxDepth = len(getattr(aws_circuit, 'instructions', []))
            circuit_for_queue = self.serialize_aws_circuit_for_queue(aws_circuit)
            if circuit_for_queue.strip() == '':
                return "Invalid AWS circuit code", 400

        self.select_policy(circuit_for_queue, num_qubits, shots, user, circuit_name, maxDepth, provider, policy)
        return str(user), 200

    def serialize_ibm_circuit_for_queue(self, circ) -> str:
        """
        Convert a Qiskit circuit into a canonical line-based format expected by create_circuit.

        The resulting code uses qreg_q/creg_c placeholders so batch composition can
        safely offset qubit indices when multiple circuits are merged.
        """
        lines = []
        for inst in circ.data:
            op = inst.operation
            gate_name = op.name
            q_indices = [circ.find_bit(q).index for q in inst.qubits]
            c_indices = [circ.find_bit(c).index for c in inst.clbits]

            if gate_name == 'measure':
                if len(q_indices) == 1 and len(c_indices) == 1:
                    lines.append(f"circuit.measure(qreg_q[{q_indices[0]}], creg_c[{c_indices[0]}])")
                continue

            params = []
            for p in op.params:
                try:
                    params.append(str(float(p)))
                except Exception:
                    params.append(str(p))

            args = []
            args.extend(params)
            args.extend([f"qreg_q[{idx}]" for idx in q_indices])
            lines.append(f"circuit.{gate_name}({', '.join(args)})")

        return '\n'.join(lines)

    def serialize_aws_circuit_for_queue(self, circ) -> str:
        """
        Convert a Braket circuit into canonical line-based format expected by create_circuit.

        The resulting code uses `circuit.<gate>(...)` so batch composition can safely
        offset qubit indices when multiple circuits are merged.
        """
        lines = []
        for ins in getattr(circ, 'instructions', []):
            op = ins.operator
            gate_name = getattr(op, 'name', type(op).__name__).lower()
            q_indices = [int(q) for q in ins.target]

            params = []
            for p in getattr(op, 'parameters', []) or []:
                try:
                    params.append(str(float(p)))
                except Exception:
                    params.append(str(p))

            args = []
            args.extend([str(idx) for idx in q_indices])
            args.extend(params)

            lines.append(f"circuit.{gate_name}({', '.join(args)})")

        return '\n'.join(lines)

    def forward_results_local(self, counts:dict, shots:int, provider:str, qb:list, users:list, circuit_names:list, divided_results:list) -> None:
        """
        Forward results to a local endpoint (default: http://localhost:5000).

        Args:
            counts (dict): Raw execution counts returned by provider.
            shots (int): Number of shots executed.
            provider (str): Provider that executed the circuit.
            qb (list): Number of qubits used by each subcircuit.
            users (list): User ids associated with the execution.
            circuit_names (list): Circuit names associated with the execution.
            divided_results (list): Results after applying divideResults.
        """
        parsed_endpoint = urlparse(self.local_result_endpoint)
        endpoints = [self.local_result_endpoint]
        if parsed_endpoint.path in ('', '/'):
            scheme = parsed_endpoint.scheme or 'http'
            for fallback_path in ('/callback', '/results', '/result'):
                fallback_endpoint = urlunparse((scheme, parsed_endpoint.netloc, fallback_path, '', '', ''))
                if fallback_endpoint not in endpoints:
                    endpoints.append(fallback_endpoint)

        # Send one callback per circuit to match receivers that expect a single
        # circuit_name + results payload per request.
        for divided_result in divided_results:
            for key, value in divided_result.items():
                if isinstance(key, tuple) and len(key) >= 2:
                    user_id, circuit_name = key[0], key[1]
                else:
                    user_id, circuit_name = None, str(key)

                safe_results = {}
                for result_key, result_count in value.items():
                    safe_results[str(result_key)] = int(result_count)

                payload = {
                    'provider': provider,
                    'shots': shots,
                    'user': str(user_id) if user_id is not None else None,
                    'circuit_name': str(circuit_name),
                    'results': safe_results,
                    'counts': counts,
                    'qb': qb,
                    'users': users,
                    'circuit_names': circuit_names
                }

                delivered = False
                for endpoint in endpoints:
                    try:
                        response = requests.post(endpoint, json=payload, timeout=5)
                        if response.status_code < 400:
                            delivered = True
                            break

                        # If the route does not exist, try fallback endpoints.
                        if response.status_code == 404 and endpoint != endpoints[-1]:
                            continue

                        logging.warning(
                            "Failed to forward results to %s. Status code: %s",
                            endpoint,
                            response.status_code
                        )
                        break
                    except (requests.RequestException, TypeError, ValueError) as exc:
                        if endpoint == endpoints[-1]:
                            logging.warning(
                                "Could not forward results to %s: %s",
                                endpoint,
                                exc
                            )
                if not delivered:
                    logging.warning(
                        "Result callback not delivered for circuit %s",
                        str(circuit_name)
                    )

    def store_url(self) -> tuple: # TODO instead of "both", use a list of providers as an input
        """
        Sends the Quirk URL of the circuit to the policy service.
        It checks if its a correct URL and gets information about the qubits and depth of it.

        Request Parameters:
            url (str): The Quirk URL of the circuit
            provider (str | list): The provider to execute the circuit. The available values are 'ibm' and 'aws'. If multiple providers are specified, the format of this parameter should be a list of strings. Default is 'ibm'
            policy (str): The policy to execute the circuit. Default is 'time'            
            shots (int, optional): The number of shots to execute the circuit. Not needed if ibm_shots and aws_shots are specified and both providers are described in `provider`            
            ibm_shots (int, optional): The number of shots to execute the circuit in IBM. Not needed if shots is specified            
            aws_shots (int, optional): The number of shots to execute the circuit in AWS. Not needed if shots is specified

        Returns:
            tuple: The response of the policy service with the scheduler task identification
        """

        if request.json.get('url') is None:
            return "URL must be specified", 400
        if request.json.get('provider') is None:
            provider = 'ibm'
            #return "Provider must be specified", 400
        else:
            provider = request.json['provider']
        if request.json.get('policy') is None:
            policy = 'time'
            #return "Policy must be specified", 400
        else:
            policy = request.json['policy']     

        url =  request.json['url']

        # Non-Quirk payloads can send circuit code directly or expose it on any reachable URL.
        parsed_url = urlparse(url)
        is_quirk_url = parsed_url.netloc == "algassert.com" and 'quirk' in parsed_url.path
        if not is_quirk_url:
            if request.json.get('shots') is None:
                return "Shots must be specified", 400

            shots = request.json['shots']
            if not isinstance(shots, int) or shots <= 0 or shots > 20000:
                return "Invalid shots value", 400

            if isinstance(provider, list):
                return "Non-Quirk URL payload supports a single provider", 400

            if provider not in ['ibm', 'aws']:
                return "Invalid provider", 400

            circuit_code = request.json.get('code')
            if circuit_code is None:
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    circuit_code = response.text
                except requests.exceptions.RequestException:
                    return "Invalid URL", 400

            user = uuid.uuid4().int
            circuit_name = request.json.get('circuit_name', url.split('/')[-1] if '/' in url else 'circuit.py')
            return self.schedule_from_code(circuit_code, provider, shots, user, circuit_name, policy)
        
        # To handle provider if its a string
        if isinstance(provider, str):
            provider = [provider]
        shots = None
        # TODO if the policy is time, the user "should" not specify shots
        if request.json.get('ibm_shots') is not None and request.json.get('aws_shots') is not None and ('ibm' in provider and 'aws' in provider): # If the provider is both and the shots of each provider are specified, use the ibm and aws shots
            ibmShots = request.json['ibm_shots']
            awsShots = request.json['aws_shots']
            if not isinstance(ibmShots, int) or ibmShots <= 0 or ibmShots > 20000 or not isinstance(awsShots, int) or awsShots <= 0 or awsShots > 20000:
                return "Invalid shots value", 400          
        else:
            if request.json.get('shots') is None: # If the shots are not specified or the provider is not both, use the basic shot value
                return "Shots must be specified", 400
            shots = request.json['shots']
            if not isinstance(shots, int) or shots <= 0 or shots > 20000:
                return "Invalid shots value", 400
            ibmShots = shots // 2
            awsShots = shots - ibmShots

    
        user = uuid.uuid4().int
        #user = request.headers.get('X-Forwarded-For', request.remote_addr) quitar esto

        document = {
            '_id': str(user),
            'circuit': url
        }
        # self.collection.insert_one(document)

        # Parse the URL and extract the fragment
        try:
            fragment = urlparse(url).fragment
        except Exception as e:
            print(f"Error parsing URL: {e}")
            return "Invalid URL", 400
        
        parsed_url = urlparse(url)
        if parsed_url.netloc != "algassert.com" or 'quirk' not in parsed_url.path:
                return "URL must come from quirk", 400

        # The fragment is a string like "circuit={...}". We need to remove the "circuit=" part and parse the rest as JSON.
        if not fragment.startswith('circuit='):
            print(f"No 'circuit' fragment in URL: {url}")
            return "Invalid URL", 400  # Return an error response

        else:
            # Remove the "circuit=" part and parse the rest as a Python literal
            circuit_str = fragment[len('circuit='):]
            circuit = ast.literal_eval(unquote(circuit_str))

            providers = {} # Dictionary because an execution can be executed on multiple providers

            # Count the number of qubits in the circuit
            for provider_name in provider:
                if provider_name == 'ibm':
                    num_qubits = max(len(col) for col in circuit['cols'])
                    if shots is None:
                        shots = ibmShots
                    providers['ibm'] = shots
                elif provider_name == 'aws': #In AWS Measure instruction does not exist, if the Measure instruction is in the url, that number of measure qubits are removed
                    num_qubits = max(len(col) for col in circuit['cols'] if 'Measure' not in col)
                    if shots is None:
                        shots = awsShots
                    providers['aws'] = shots
            
            if num_qubits > self.max_qubits:
                return "Circuit too large", 400  # Return a response

            for provider in providers: #Iterate through the providers to add the elements to the specific provider queue in case the circuit needs to be executed on multiple providers
                shots = providers[provider]
                if self.transpilation_machine == 'local':
                    maxDepth = max(sum(1 for j in circuit['cols'] if i < len(j) and j[i] not in {1, 'Measure'}) for i in range(num_qubits))
                else:
                    try:
                        x = requests.post(self.translator+provider, json = {'url':url})
                        data = json.loads(x.text)                        
                        code = ""
                        for elem in data['code']:
                            code += elem + '\n'
                        if provider == 'ibm':
                            circ = self.executeCircuitIBM.code_to_circuit_ibm(code) #check this method because if a lot of circuits enter at the same time, it fails
                            maxDepth = self.executeCircuitIBM.get_transpiled_circuit_depth_ibm(circ, self.transpilation_backend)
                        elif provider == 'aws':
                            #TODO
                            maxDepth = max(sum(1 for j in circuit['cols'] if i < len(j) and j[i] not in {1, 'Measure'}) for i in range(num_qubits))
                    except:
                        print("Error in the request to the translator")
                    # TODO instead, parse it into a circuit and transpile it to get the depth (circuit.depth)
                self.select_policy(url, num_qubits, shots, user, url, maxDepth, provider, policy)
    
        return str(user), 200  #return the id
        #return "Your id is "+str(user), 200  # Return a response
    
    def store_url_circuit(self) -> tuple:
        """
        Sends the GitHub URL of the circuit to the policy service.
        It first needs to get the content of the file, check if its a quantum circuit and parse it to a standard way.

        Request Parameters:
            url (str): The GitHub URL of the circuit
            shots (int): The number of shots to execute the circuit
            policy (str): The policy to execute the circuit. Default is 'time'

        Returns:
            tuple: The response of the policy service with the scheduler task identification
        """
        if request.json.get('url') is None:
            return "URL must be specified", 400
        if request.json.get('shots') is None: # TODO if the policy is time, the user "should" not specify shots
            return "Shots must be specified", 400
        if request.json.get('policy') is None:
            policy = 'time'
            #return "Policy must be specified", 400
        else:
            policy = request.json['policy']
        url = request.json['url']
        shots = request.json['shots']

        if not isinstance(shots, int) or shots <= 0 or shots > 20000:
            return "Invalid shots value", 400

        user = uuid.uuid4().int
        #user = request.headers.get('X-Forwarded-For', request.remote_addr)
        document = {
        '_id': str(user),
        'circuit': url
        }
        # with self.result_lock:
        #     self.collection.insert_one(document)

        # If code is provided inline, or the URL is not from GitHub, use schedule_from_code directly.
        parsed_url_check = urlparse(url)
        is_github_url = parsed_url_check.netloc == "raw.githubusercontent.com"
        circuit_code_inline = request.json.get('code')
        provider_field = request.json.get('provider', 'ibm')

        if circuit_code_inline is not None or not is_github_url:
            circuit_code = circuit_code_inline
            if circuit_code is None:
                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    circuit_code = response.text
                except requests.exceptions.RequestException:
                    return "Invalid URL", 400
            circuit_name = request.json.get('circuit_name', url.split('/')[-1] if '/' in url else 'circuit.py')
            return self.schedule_from_code(circuit_code, provider_field, shots, user, circuit_name, policy)

        # URL is a raw GitHub url, get its content
        try:
            parsed_url = urlparse(url)
            if parsed_url.netloc != "raw.githubusercontent.com":
                return "URL must come from a raw GitHub file", 400
            response = requests.get(url)
            response.raise_for_status()
            # Get the name of the file
            circuit_name = url.split('/')[-1]
        except requests.exceptions.RequestException as e:
            print(f"Error getting URL content: {e}")
            return "Invalid URL", 400
        
        circuit = response.text
        # Split the circuit string into lines once
        lines = circuit.split('\n')
        importAWS = next((line for line in lines if 'braket.circuits' in line), None)
        importIBM = next((line for line in lines if 'qiskit' in line), None)
        if importIBM:
            return self.schedule_from_code(circuit, 'ibm', shots, user, circuit_name, policy)
        if importAWS:
            return self.schedule_from_code(circuit, 'aws', shots, user, circuit_name, policy)

        return "Invalid circuit code", 400

    
    def sendResults(self) -> tuple:
        """
        Send the results of the circuit execution
        This method extracts the 'id' parameter from the request's query string. The 'id' is expected to be an integer representing the user ID. It then queries the database for documents matching this ID and returns the results in JSON format.

        Request Parameters:
            id (int): The user ID from the request's query string. It must be a positive integer.

        Returns:
            tuple: The results of the circuit execution

        """
        id = request.args.get('id')
        if id is None or id == '':
            return "No id provided", 400
        try:
            user = int(request.args.get('id'))
        except ValueError:
            return "Invalid id value. It must be an integer.", 400
        #user = request.headers.get('X-Forwarded-For', request.remote_addr)
            
        if user <= 0:
            return "Invalid id value. It must be a positive integer.", 400

        cursor = self.collection.find({'_id': str(user)},{'_id': 0})
        documents = list(cursor)
        json_documents = dumps(documents)

        return json.dumps(json_documents), 200

    def updatePorts(self) -> None:
        """
        Update the ports used by the scheduler
        """
        for i in range(8083, 8182):
            a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            location = ("0.0.0.0", i)
            result_of_check = a_socket.connect_ex(location)

            if result_of_check == 0:
                self.ports[i]=1
            else:
                self.ports[i]=0

            a_socket.close()

    
    def getFreePort(self) -> int:
        """
        Return a free port

        Returns:
            int: The free port
        """
        puertos=[k for k, v in self.ports.items() if v == 0]
        self.ports[puertos[0]]=1
        return puertos[0]

if __name__ == '__main__':
    app = Scheduler()
    app.run()
