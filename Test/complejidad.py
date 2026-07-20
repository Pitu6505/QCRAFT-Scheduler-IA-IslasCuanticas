import requests
import pandas as pd
from qiskit import QuantumCircuit

def analizar_complejidad_github(url_list):
    """
    Descarga circuitos cuánticos desde URLs raw de GitHub, los compila 
    y extrae métricas de complejidad topológica.
    """
    resultados = []
    
    for url in url_list:
        try:
            # 1. Descargar el código crudo
            response = requests.get(url)
            if response.status_code != 200:
                print(f"❌ Error al descargar (HTTP {response.status_code}): {url}")
                continue
                
            codigo = response.text
            
            # 2. Crear un entorno local para ejecutar el script y aislar las variables
            local_vars = {}
            # Limpiamos posibles retornos que rompan la función exec()
            clean_code = codigo.replace("return circuit", "") 
            
            # Instanciar el objeto QuantumCircuit en la variable local_vars['circuit']
            exec(clean_code, globals(), local_vars)
            
            if 'circuit' in local_vars:
                qc = local_vars['circuit']
                nombre_circuito = url.split('/')[-1]
                
                # 3. Extracción de Métricas de Complejidad
                qubits = qc.num_qubits
                profundidad = qc.depth()
                puertas_totales = sum(qc.count_ops().values())
                
                # Las puertas de 2+ qubits (ej. CX) son la fuente principal de crosstalk
                puertas_entrelazadas = qc.num_nonlocal_gates() 
                
                resultados.append({
                    "Circuito_Nombre": nombre_circuito,
                    "Qubits_Logicos": qubits,
                    "Profundidad": profundidad,
                    "Total_Puertas": puertas_totales,
                    "Puertas_CX_Multi": puertas_entrelazadas
                })
                print(f"✅ Analizado correctamente: {nombre_circuito}")
            else:
                print(f"⚠️ Objeto 'circuit' no encontrado en el código de: {url}")
                
        except Exception as e:
            print(f"❌ Error procesando {url}: {e}")
            
    # Devolvemos un DataFrame para facilitar la exportación o el cruce de datos
    return pd.DataFrame(resultados)


# ==========================================
# EJECUCIÓN DEL SCRIPT
# ==========================================
if __name__ == "__main__":
    # Sustituye esto por tu lista real de URLs crudas (raw) de GitHub
    urls_experimento = [
     "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/Deutsch-Jozsa_qcraft.py",
      "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_4_mqt.py",
      "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_5_mqt.py",
      "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/Deutsch-Jozsa/dj_indep_7_mqt.py",
      "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/adder/adder_n10_vq.py",
     "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/adder/adder_n13_vq.py",
      "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/adder/adder_n4_vq.py",
      "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-noancilla_4_mqt.py",
     "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-v-chain_3_mqt.py",
    "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover-v-chain_4_mqt.py",
     "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover_3_vq.py",
     "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover_7_vq.py",
 "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/grover/grover_qcraft.py",
     "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_2_vq.py",
    "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_3_mqt.py",
     "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_4_mqt.py",
    "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_5_mqt.py",
   "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/phase_estimation/pe_5_vq.py",
 "https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/qft/qft_qcraft.py",
"https://raw.githubusercontent.com/Qcraft-UEx/QCRAFT-Scheduler/main/circuits-code//combinational/popularalgorithms/shor/shor_qcraft.py",
    ]
    
    # Ejecutamos el análisis
    df_complejidad = analizar_complejidad_github(urls_experimento)
    
    # Imprimimos los resultados por consola
    print("\n--- RESUMEN DE COMPLEJIDAD ---")
    print(df_complejidad.to_string(index=False))
    
    # Exportamos a CSV usando punto y coma para mantener el mismo formato que el logger principal
    df_complejidad.to_csv("complejidad_circuitos.csv", sep=";", index=False)
    print("\n💾 Archivo 'complejidad_circuitos.csv' generado con éxito.")