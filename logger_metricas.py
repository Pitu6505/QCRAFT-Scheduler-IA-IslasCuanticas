import csv
import os
from datetime import datetime

def registrar_metrica_csv(job_id, nombre_circuito, qubits_datos, qubits_centinela, modo, shots_totales, shots_validos):
    """
    Guarda los resultados de supervivencia de una ejecución FTQC en un archivo CSV.
    Crea el archivo y las cabeceras automáticamente si no existe.
    """
    nombre_archivo = "resultados_experimentacion.csv"
    archivo_existe = os.path.isfile(nombre_archivo)
    
    # Calcular el porcentaje de supervivencia
    porcentaje = (shots_validos / shots_totales) * 100 if shots_totales > 0 else 0
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Formatear listas de qubits como texto sin comas para no romper el formato CSV de Excel
    str_datos = str(qubits_datos).replace(',', '-')
    str_centinelas = str(qubits_centinela).replace(',', '-')
    
    with open(nombre_archivo, mode='a', newline='', encoding='utf-8') as archivo:
        # Usamos punto y coma (;) para que Excel lo abra perfectamente tabulado en España/Europa
        writer = csv.writer(archivo, delimiter=';') 
        
        # Si es la primera vez que se ejecuta, escribimos la cabecera
        if not archivo_existe:
            writer.writerow([
                "Fecha_Hora", 
                "Job_ID", 
                "Circuito_Nombre", 
                "Layout_Circuito", 
                "Layout_Centinela", 
                "Modo_Centinela", 
                "Shots_Totales", 
                "Shots_Validos", 
                "Supervivencia_(%)"
            ])
            
        # Escribimos los datos extraídos de esta isla cuántica
        writer.writerow([
            fecha_hora,
            job_id,
            nombre_circuito,
            str_datos,
            str_centinelas,
            modo,
            shots_totales,
            shots_validos,
            f"{porcentaje:.2f}"
        ])
        
    print(f"📊 Metricas guardadas en CSV -> {nombre_circuito} ({shots_validos}/{shots_totales})")