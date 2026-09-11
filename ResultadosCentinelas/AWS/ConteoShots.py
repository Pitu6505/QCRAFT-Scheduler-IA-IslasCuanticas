import json

def calcular_descartes(json_data_str, shots_enviados=1000):
    """
    Calcula el número de shots descartados tras la post-selección del FTQC.
    
    :param json_data_str: El string con el JSON de los resultados.
    :param shots_enviados: El número total de shots que se pidieron a AWS Braket.
    """
    # Cargar los datos del JSON
    datos = json.loads(json_data_str)
    
    print(f"{'CIRCUITO':<20} | {'ENVIADOS':<10} | {'VÁLIDOS':<10} | {'DESCARTADOS':<12} | {'% RUIDO':<8}")
    print("-" * 70)
    
    estadisticas = []
    
    for experimento in datos:
        nombre_circuito = experimento.get("circuit", "Desconocido")
        resultados = experimento.get("value", {})
        
        # Sumar todos los valores (frecuencias de los bitstrings válidos)
        shots_validos = sum(resultados.values())
        
        # Calcular los descartados
        shots_descartados = shots_enviados - shots_validos
        
        # Calcular el porcentaje de ruido (tasa de descarte)
        porcentaje_ruido = (shots_descartados / shots_enviados) * 100
        
        print(f"{nombre_circuito:<20} | {shots_enviados:<10} | {shots_validos:<10} | {shots_descartados:<12} | {porcentaje_ruido:.2f}%")
        
        estadisticas.append({
            "circuito": nombre_circuito,
            "validos": shots_validos,
            "descartados": shots_descartados,
            "ruido_pct": porcentaje_ruido
        })
        
    return estadisticas

# ==========================================
# EJECUCIÓN DEL SCRIPT
# ==========================================

# Pega aquí el JSON que genera tu orquestador
json_resultados = """
[
  {
    "_id": "308969856189868489301751875887449592243",
    "circuit": "adder_n4_vq.py",
    "value": {
      "100000": 97, "100001": 6, "100010": 2, "100011": 6, "100100": 18, "100101": 28, "100110": 5, "100111": 3,
      "101000": 12, "101001": 4, "101010": 7, "101011": 1, "101100": 3, "101101": 7, "101110": 2, "101111": 5,
      "110000": 101, "110001": 7, "110010": 2, "110011": 2, "110100": 23, "110101": 41, "110110": 8, "110111": 5,
      "111000": 13, "111001": 2, "111010": 4, "111011": 3, "111100": 7, "111101": 13, "111110": 5, "111111": 11,
      "000000": 131, "000001": 8, "000010": 1, "000011": 1, "000100": 15, "000101": 39, "000110": 9, "000111": 7,
      "001000": 15, "001001": 10, "001010": 10, "001011": 6, "001100": 7, "001101": 6, "001110": 4, "001111": 6,
      "010000": 117, "010001": 13, "010010": 10, "010011": 4, "010100": 14, "010101": 36, "010110": 7, "010111": 5,
      "011000": 21, "011001": 7, "011010": 7, "011011": 7, "011100": 4, "011101": 9, "011110": 7, "011111": 4
    }
  },
  {
    "_id": "78632139899598518636747141144062729821",
    "circuit": "grover_3_vq.py",
    "value": {
      "10000": 29, "10001": 23, "10010": 20, "10011": 29, "10100": 28, "10101": 23, "10110": 32, "10111": 24,
      "11000": 5, "11001": 9, "11010": 9, "11011": 9, "11100": 7, "11101": 15, "11110": 12, "11111": 14,
      "00000": 92, "00001": 70, "00010": 37, "00011": 90, "00100": 57, "00101": 79, "00110": 61, "00111": 41,
      "01000": 33, "01001": 30, "01010": 10, "01011": 29, "01100": 24, "01101": 23, "01110": 25, "01111": 11
    }
  }
]
"""

# Si enviaste más de 1000 shots en este experimento, actualiza el parámetro
calcular_descartes(json_resultados, shots_enviados=1000)