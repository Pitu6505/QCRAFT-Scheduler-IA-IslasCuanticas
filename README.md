# QCRAFT QIM:  Quantum Island Mapping

![Python Versions](https://img.shields.io/badge/python-3.9%20|%203.10%20|%203.11%20|%203.12-blue.svg)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/Qcraft-UEx/QCRAFT/blob/main/LICENSE)
[![Qiskit](https://img.shields.io/badge/Qiskit-1.4.4-blueviolet.svg)](https://qiskit.org/)
[![AWS Braket](https://img.shields.io/badge/AWS_Braket-1.101.0-orange.svg)](https://aws.amazon.com/braket/)

## Description

**QCRAFT QIM** is an advanced quantum circuit scheduling and optimization system that implements intelligent placement algorithms for quantum circuit execution on both IBM Quantum and AWS Braket platforms. 

The system's core innovation is the **Quantum Island Mapping** algorithm, which optimizes circuit placement on quantum processors by:
- Analyzing the physical topology and noise characteristics of quantum backends
- Creating "quantum islands" - isolated regions of low-noise, well-connected qubits
- Intelligently mapping multiple quantum circuits to these islands to minimize decoherence and gate errors
- Aggregating multiple user circuits into optimized batches to reduce queue times and costs

This approach significantly improves execution efficiency by minimizing cross-talk, reducing SWAP operations, and maximizing the utilization of high-quality qubits on noisy intermediate-scale quantum (NISQ) devices.

## Key Features

### Quantum Islands Placement
- **Graph-Based Topology Analysis**: Builds connectivity graphs from backend coupling maps with noise metrics
- **Intelligent Island Detection**: Identifies optimal qubit clusters based on connectivity, noise thresholds, and distance constraints
- **One Placement Strategies**:
  - `Islas_Cuanticas_Edges`: Edge-aware placement considering gate fidelities and logical topology

###  Multi-Provider Support
- **IBM Quantum**: Full integration with Qiskit Runtime and IBM Cloud backends
- **AWS Braket**: Support for Rigetti, IonQ, and AWS simulators


### Advanced Scheduling Policies
- **Time-Based**: Periodic batch execution with configurable intervals
- **Shot-Optimized**: Minimize total shots while respecting circuit requirements
- **Depth-Aware**: Group circuits by similar transpilation depth

### Additional Capabilities
- **Circuit Translation**: Quirk URL and GitHub repository circuit import
- **Result Aggregation**: Automatic result division and distribution to users
- **Persistent Storage**: MongoDB integration for circuit tracking and result caching
- **Concurrent Execution**: Thread-safe queue management with resettable timers
- **Transpilation Optimization**: Pre-transpilation depth analysis for better grouping

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Flask API      │─────▶│   Scheduler      │─────▶│   MongoDB       │
│  (Port 8082)    │      │   Policies       │      │   Database      │
└─────────────────┘      └──────────────────┘      └─────────────────┘
         │                        │                            
         ▼                        ├─▶ Islas_Cuanticas_Edges  
┌─────────────────┐               ├─▶ Time/Shots/Depth policies
│   Translator    │               │
│   (Port 8081)   │               ▼
└─────────────────┘      ┌──────────────────┐
         │               │   Circuit Queue  │
         │               └──────────────────┘
         ▼                        │
┌─────────────────┐               ├─▶ executeCircuitIBM
│  Quirk/GitHub   │               │   (Qiskit Runtime)
│  Circuit Import │               │
└─────────────────┘               └─▶ executeCircuitAWS
                                     (AWS Braket)
```

## Installation

### Prerequisites
- Python 3.9, 3.10, 3.11, or 3.12
- Docker and Docker Compose (for MongoDB)
- IBM Quantum account with API token
- AWS account with Braket access (optional)

### Step 1: Clone the Repository
```bash
git clone <your-repository-url>
cd QCRAFT-Scheduler
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure API Credentials
Configure IBM Runtime with a saved Qiskit account or set the environment
variables `IBM_QUANTUM_TOKEN` and `IBM_QUANTUM_INSTANCE`. Do not place API
tokens in source files. Configure AWS credentials separately if using Braket.

### Step 4: Set Up MongoDB Database
```bash
cd db
docker compose up --build -d
```

This will start a MongoDB instance on port 27017.

### Step 5: Configure Environment Variables
Create or modify `db/.env` with your settings:
```env
# Host configuration
HOST=localhost
PORT=8082

# Translator configuration
TRANSLATOR=localhost
TRANSLATOR_PORT=8081

# Database configuration
DB=localhost
DB_PORT=27017
DB_NAME=scheduler_db
DB_COLLECTION=circuits
```

## Quick Start

### Starting the Services

**Terminal 1 - Translator Service:**
```bash
python translator.py
```

**Terminal 2 - Scheduler Service:**
```bash
python scheduler.py
```

### Basic Example - Quirk URL

Send a simple Bell state circuit from Quirk:
```python
import requests
import json

# Define the request
data = {
    "url": "https://algassert.com/quirk#circuit={'cols':[['H'],['•','X'],['Measure','Measure']]}",
    "shots": 1000,
    "provider": "ibm",
    "policy": "Islas_Cuanticas_Edges"
}

# Send the circuit
response = requests.post("http://localhost:8082/url", json=data)
circuit_id = response.text.split("Your id is ")[1].strip()
print(f"Circuit submitted with ID: {circuit_id}")

# Retrieve results
params = {'id': circuit_id}
results = requests.get("http://localhost:8082/result", params=params)
print("Results:", results.json())
```

## Advanced Usage

### Using Quantum Islands Policy

The **Islas_Cuanticas** policy optimizes circuit placement based on physical qubit topology:

```python
import requests

data = {
    "url": "https://raw.githubusercontent.com/user/repo/main/circuit.py",
    "shots": 5000,
    "provider": "ibm",
    "policy": "Islas_Cuanticas_Edges"  # Uses node-based island placement
}

response = requests.post("http://localhost:8082/circuit", json=data)
```

### Using Edge-Aware Islands Policy

The **Islas_Cuanticas_Edges** policy considers both nodes and edges (gate connectivity):

```python
data = {
    "url": "https://algassert.com/quirk#circuit={...}",
    "shots": 10000,
    "provider": "ibm",
    "policy": "Islas_Cuanticas_Edges"  # Uses logical topology mapping
}

response = requests.post("http://localhost:8082/url", json=data)
```

### Multi-Provider Execution

Execute the same circuit on both IBM and AWS simultaneously:

```python
data = {
    "url": "https://algassert.com/quirk#circuit={'cols':[['H'],['•','X'],['Measure','Measure']]}",
    "ibm_shots": 8000,
    "aws_shots": 2000,
    "provider": ["ibm", "aws"],  # Both providers
    "policy": "Islas_Cuanticas_Edges"
}

response = requests.post("http://localhost:8082/url", json=data)
```

### GitHub Circuit Import

Import circuits directly from GitHub repositories:

```
import requests

data = {
    "url": "https://raw.githubusercontent.com/user/repo/branch/file.py",
    "shots": 10000,
    "provider": "ibm",
    "policy": "Islas_Cuanticas_Edges",
}

response = requests.post("http://localhost:8082/circuit", json=data)
```

### Elegir niveles de colocación en los scripts de prueba

En cualquiera de los scripts de prueba de `Test` que use la política
`Islas_Cuanticas_Edges`, elige los niveles cambiando `PLACEMENT_LEVELS`:

```python
PLACEMENT_LEVELS = [3]        # Solo nivel 3
# PLACEMENT_LEVELS = [2, 3]   # Niveles 2 y 3
# PLACEMENT_LEVELS = [1, 2, 3]  # Todos
```

Pasa ese parámetro en el diccionario de la petición:

```python
data_template = {
    "url": "",
    "shots": 10000,
    "provider": ["ibm"],
    "policy": "Islas_Cuanticas_Edges",
    "placement_levels": PLACEMENT_LEVELS,
}
```

El scheduler mantiene una cola separada para cada combinación solicitada, para
que circuitos de configuraciones diferentes no se mezclen. Los valores válidos
son cualquier lista no vacía y sin repetidos de `[1, 2, 3]`. Si se omite
`placement_levels`, el comportamiento existente no cambia. Reinicia el
scheduler después de actualizar su código.

Los scripts `Test/scheduler-async_IslasEdges.py`,
`Test/scheduler-async_IslasEdges_Short.py` y
`Test/scheduler-async_IslasEdges_ShortAWS.py` ya exponen esta variable. Los
scripts asíncronos siguen enviando todos los circuitos en paralelo.
Para ejecutarlos, reinicia el scheduler y usa el script de prueba que ya te
funcionaba; solo cambia `PLACEMENT_LEVELS` y ejecuta ese archivo.

En IBM, una colocación solo se usa como `initial_layout` si tiene exactamente
un índice físico entero, único y dentro del rango del backend por qubit lógico.
Si el algoritmo genera un layout inválido, por ejemplo un objeto no entero, el
scheduler lo informa y transpila sin layout inicial para que el trabajo aún
pueda ejecutarse. El CSV de campaña incluye `placement_layout_applied` para
distinguir esos casos.

La búsqueda VF2 excluye antes del isomorfismo los qubits ocupados, los que
incumplen el umbral de ruido y los que violan la distancia mínima respecto a
circuitos ya colocados. Esto evita enumerar asignaciones que luego se
descartarían.

### Campaña secuencial de niveles de colocación

El lanzador opcional `Test/ejecutar_campana_niveles.py` compara los escenarios
por separado. Primero muestra el plan; para lanzar trabajos reales hay que
usar `--execute` y confirmar. Cada escenario espera sus resultados antes de
enviar el siguiente.

Con el servidor y el traductor ya iniciados, primero revisa el plan sin enviar
trabajos:

```powershell
python QCRAFT-Scheduler\Test\ejecutar_campana_niveles.py
```

Para enviar la campaña real, se requiere `--execute` y escribir `EJECUTAR`
cuando se solicite. Por ejemplo, con 30 circuitos y 10 000 shots en los tres
escenarios, se solicitarán 900 000 muestras lógicas (circuit-shots). Esto no
equivale necesariamente a 900 000 shots de IBM: el scheduler puede componer
varios circuitos en un lote y ejecutar ese lote con 10 000 shots:

```powershell
python QCRAFT-Scheduler\Test\ejecutar_campana_niveles.py --execute
```

Los resultados por circuito y las métricas por lote IBM se guardan en CSV con
una marca de tiempo. Las métricas incluyen profundidad, tiempo de transpilation,
tiempo de ejecución, operaciones de dos qubits y `swap_gate_count` (puertas
`swap` explícitas que permanecen en el circuito transpiled). IBM puede
descomponer SWAP en puertas nativas; en ese caso, ese campo puede ser cero y
`two_qubit_gate_count` junto con `operation_counts` describe las puertas
transpiled sin afirmar una reconstrucción de SWAPs descompuestos.
El scheduler también conserva el detalle de los lotes en
`resultados_metricas_ibm.jsonl`.
Ejecuta la campaña con el scheduler sin otras campañas activas, para que los
lotes y sus métricas no incluyan circuitos ajenos.

Se puede elegir solo un subconjunto o cambiar su orden, por ejemplo:

```powershell
python QCRAFT-Scheduler\Test\ejecutar_campana_niveles.py --scenarios niveles_2_3,niveles_1_2_3
```

Para credenciales, el scheduler admite una cuenta IBM ya guardada con Qiskit
Runtime o las variables de entorno `IBM_QUANTUM_TOKEN` e
`IBM_QUANTUM_INSTANCE`. No pongas tokens en el script.
import requests

data = {
    "url": "https://raw.githubusercontent.com/user/repo/branch/file.py",
    "shots": 10000,
    "policy": "shots"
}

requests.post("http://localhost:8082/circuit", json=data)
```

### Comparing placement levels without execution

The placement-level analysis script is in `Test`, next to the asynchronous
scheduler scripts. By default it reads the `urls` dictionary in
`scheduler-async_IslasEdges_Short.py` (without importing or executing that
submission script), downloads each raw GitHub Python circuit, and compares the
existing placement strategies in this order:

1. Level 3 only: general connected-qubit search.
2. Levels 2 + 3: component-aware placement, then general search.
3. Levels 1 + 2 + 3: exact subgraph isomorphism, then the two fallbacks.

Add as many circuits as needed to that `urls` dictionary (for example, 30),
then run it from `QCRAFT-Scheduler`:

```powershell
python Test\analizar_niveles_colocacion.py --provider ibm --backend ibm_fez --levels 3
```

The results are written to `resultados_niveles_colocacion.csv`. To use a
different dictionary, pass `--urls-file ruta\al\fichero.py`; a JSON object
mapping circuit names to raw GitHub URLs is also supported.
For IBM, select the QPU whose topology should be used with `--backend` (the
default is `ibm_fez`). AWS currently uses the Ankaa-3 topology.
`--levels 3` runs only the general search strategy. No extra physical-qubit
separation is reserved between circuits. If the current iteration cannot fit
all remaining circuits, the analyzer starts another iteration with a fresh
placement and retries the unplaced circuits on the same QPU topology. Each
iteration represents a separate execution batch; qubits are reused between
iterations. At the end, the console and CSV include the total estimated SWAP
count for each selected scenario, summing over all iterations.

The provider's backend credentials and configuration must already be set up as
for the scheduler. The tool does not submit or execute circuits. Its SWAP
figure is an estimate that sums `shortest_path_distance - 1` for each distinct
logical interaction pair; it is useful for comparing placements, but it is not
the exact gate count produced by Qiskit's transpiler. Only statically declare
single-`QuantumRegister` sizes and indexed register operands are analyzed.
The report names the strategy that actually placed the circuit: level 1 (VF2
exact isomorphism), level 2 (component-aware placement), or level 3 (general
search). For circuits larger than four qubits, the current placement algorithm
skips VF2.

### Retrieving Results

All requests return a unique circuit ID. Use it to fetch results:

```python
import requests
import json

response = requests.post("http://localhost:8082/url", json=data)
circuit_id = response.text.split("Your id is ")[1]

params = {'id': circuit_id}
response = requests.get("http://localhost:8082/result", params=params).text
results = json.loads(response)
print("Results:", results)
```

## Scheduling Policies

### Available Policies

| Policy | Description | Use Case |
|--------|-------------|----------|
| `time` | Executes circuits after a fixed time interval (10s default) | General purpose, balanced approach |
| `shots` | Groups circuits with minimum total shots | Cost optimization |
| `depth` | Groups circuits with similar transpilation depth | Minimize execution time variance |
| `shots_depth` | Combines shots and depth optimization | Balanced cost and time |
| `shots_optimized` | Advanced shot minimization with depth awareness | Maximum cost efficiency |
| **`Islas_Cuanticas_Edges`** | **Graph-based island placement (edge-aware)** | **Topology-aware optimization** |

### Policy Configuration Parameters

Edit `scheduler_policies.py` to customize:
```python
self.time_limit_seconds = 10      # Time interval for time-based policies
self.max_qubits = 133              # Maximum qubits (IBM Heron: 133)
self.forced_threshold = 12         # ML priority threshold
self.machine_ibm = 'ibm_fez'       # IBM backend name
self.machine_aws = 'arn:aws:...'   # AWS Braket device ARN
```

Edit `config.py` for island placement:
```python
MIN_CIRCUIT_DISTANCE = 0           # Minimum island separation (nodes)
MAX_NOISE_THRESHOLD = 312.15       # Maximum acceptable noise/temperature
Porcentaje_util = 90               # Percentage of qubits to utilize (0-100)
USE_PARTITION = False              # Enable graph partitioning
PARTITIONS = 4                     # Number of partitions
PARTITION_INDEX = 1                # Current partition index (1-based)
```

## Configuration

### Environment Variables (`db/.env`)

The application can be configured by modifying the `.env` file located at the `/db` folder:

```env
# Host configuration
HOST=localhost
PORT=8082

# Translator configuration
TRANSLATOR=localhost
TRANSLATOR_PORT=8081

# Database configuration
DB=localhost
DB_PORT=27017
DB_NAME=scheduler_db
DB_COLLECTION=circuits
```

### Backend Selection

Configure quantum backends in the respective API files:

**IBM Quantum** ([ibm_api.py](ibm_api.py) and [executeCircuitIBM.py](executeCircuitIBM.py)):
```python
# ibm_api.py
API_KEY = "your_ibm_api_key"
INSTANCE_CRN = "crn:v1:bluemix:public:quantum-computing:..."

def get_backend_graph(backend_name="ibm_fez"):
    # Available: ibm_fez, ibm_torino, ibm_brisbane, ibm_kyoto, etc.
```

**AWS Braket** ([executeCircuitAWS.py](executeCircuitAWS.py)):
```python
# Configure AWS credentials via environment or boto3
# Available devices:
# - Rigetti: arn:aws:braket:us-west-1::device/qpu/rigetti/Ankaa-3
# - IonQ: arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1
# - Simulators: arn:aws:braket:::device/quantum-simulator/amazon/sv1
```
