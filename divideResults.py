from unittest import result
import numpy as np
from logger_metricas import registrar_metrica_csv

def proportionalAllocation(total_shots:int,newCounts:dict,usershots:list) -> dict:
    proportions = {key: value / total_shots for key, value in newCounts.items()}
    allocated_shots = {key: round(proportions[key] * usershots) for key in proportions.keys()} 
    selected_counts = {key: allocated_shots[key] for key in allocated_shots.keys() if allocated_shots[key] > 0}
    return selected_counts

def stratifiedSampling(total_shots:int,newCounts:dict,usershots:list) -> dict:
    keys = list(newCounts.keys())
    probabilities = [value / total_shots for value in newCounts.values()]
    sampled_keys = np.random.choice(keys, size=usershots, replace=True, p=probabilities) 
    selected_counts = {key: np.count_nonzero(sampled_keys == key) for key in keys}
    return selected_counts

def divideResults(id_job:str, counts:dict, shots:list, provider:str, qb:list, users:list, circuit_name:list, layout_fisico:list=None, modo_inferido:str="Desconocido") -> list:
    result = []
    for i in range(len(shots)):
        
        newCounts = {}

        for key, value in counts.items():
            rightRemovedQubits = sum(qb[0:i])  
            leftRemovedQubits = sum(qb[i+1:len(qb)])  
            if provider == 'aws':
                data = key[rightRemovedQubits:]  
                data = data[:(len(data)-leftRemovedQubits)]
                data = data[::-1] 
            else:
                data = key[leftRemovedQubits:] 
                data = data[:(len(data)-rightRemovedQubits)]

            if 'X' in data:
                continue 
            
            if data in newCounts:
                newCounts[data] += value
            else:
                newCounts[data] = value

        total_shots = sum(newCounts.values())
        selected_counts = newCounts

        print(f"🛡️ [{users[i]}] - Circuit: {circuit_name[i]} | Shots válidos: {total_shots}/{shots[i]} ({(total_shots/shots[i])*100:.2f}%)") 
        
        qubits_datos = "N/A"
        qubits_centinelas = "N/A"
        
        if layout_fisico:
            # Si el layout tiene el formato moderno (Diccionarios de Islas + FTQC)
            if isinstance(layout_fisico[0], dict):
                if i < len(layout_fisico):
                    qubits_datos = layout_fisico[i].get('data', "N/A")
                    qubits_centinelas = layout_fisico[i].get('sentinel', "N/A")
            
            # Si el layout tiene el formato clásico (Lista plana de enteros)
            else:
                offset_datos = sum(qb[:i])
                qubits_datos = layout_fisico[offset_datos : offset_datos + qb[i]]
                
                # Si el array tiene más qubits físicos que lógicos, los sobrantes son centinelas globales
                total_datos = sum(qb)
                if len(layout_fisico) > total_datos:
                    qubits_centinelas = layout_fisico[total_datos:]
            
        registrar_metrica_csv(
            job_id=id_job,
            nombre_circuito=circuit_name[i],
            qubits_datos=qubits_datos,
            qubits_centinela=qubits_centinelas,
            modo=modo_inferido,
            shots_totales=shots[i],
            shots_validos=total_shots
        )
        result.append({(users[i],circuit_name[i]):selected_counts})

    return result