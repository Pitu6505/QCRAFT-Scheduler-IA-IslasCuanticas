import requests
import json
import os

"""
Script de validación rápida para probar el formato de los circuitos Quirk
antes de lanzar el test completo con 100 circuitos.
"""

# URLs de configuración
url_aws = 'http://54.155.193.167:8082/'
url_local = 'http://localhost:8082/'
url = url_local  # Cambiar a url_aws cuando esté listo

pathURL = 'url'

def test_single_circuit():
    """Prueba con un solo circuito del JSON para validar el formato"""
    
    print("=" * 80)
    print("VALIDACIÓN DE FORMATO - Circuito Quirk")
    print("=" * 80)
    
    # Cargar el JSON (mismo directorio que el script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, 'mutants_formatted.json')
    with open(json_file, 'r', encoding='utf-8') as f:
        circuits = json.load(f)
    
    print(f"✓ Cargados {len(circuits)} circuitos del JSON\n")
    
    # Tomar el primer circuito como ejemplo
    test_circuit = circuits[0]
    
    print("Circuito de prueba:")
    print(f"  ID: {test_circuit['_id']}")
    print(f"  Shots originales en JSON: {test_circuit['shots']} → Forzando a 1000 shots")
    print(f"  Policy: {test_circuit['policy']}")
    print(f"  URL: {test_circuit['url'][:100]}...\n")
    
    # Preparar payload con provider y policy (FORZAR 1000 shots)
    payload = {
        "url": test_circuit['url'],
        "shots": 1000,  # FORZAR 1000 shots para controlar costos
        "provider": ['aws'],           # Especificar provider según el servidor
        "policy": test_circuit['policy']  # Usar policy del JSON
    }
    
    print(f"Enviando a: {url + pathURL}")
    print("Payload:")
    print(f"  - shots: {payload['shots']}")
    print(f"  - provider: {payload['provider']}")
    print(f"  - policy: {payload['policy']}")
    print(f"  - url length: {len(payload['url'])} caracteres\n")
    
    # Comparación con formato de testBellState.py
    print("Comparación de formatos:")
    print("\nFormato original (testBellState.py):")
    original_url = "https://algassert.com/quirk#circuit={'cols':[['H'],['•','X'],['Measure','Measure']]}"
    print(f"  URL: {original_url}")
    print(f"  Usa comillas simples en el JSON")
    
    print("\nFormato del JSON (mutants_formatted.json):")
    print(f"  URL: {test_circuit['url'][:120]}...")
    print(f"  Usa comillas dobles y caracteres URL-encoded (%5E, %C2%BC, etc.)")
    
    # Enviar petición
    print("\n" + "-" * 80)
    print("Enviando petición...")
    
    try:
        response = requests.post(url + pathURL, json=payload, timeout=30)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("\n✓ FORMATO VÁLIDO - El circuito fue aceptado correctamente")
        else:
            print("\n✗ POSIBLE PROBLEMA - Revisar el formato o la respuesta del servidor")
            
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        print("\nPosibles causas:")
        print("  1. El servidor no está ejecutándose")
        print("  2. La URL del servidor es incorrecta")
        print("  3. Problema de conectividad")

def compare_formats():
    """Analiza las diferencias entre formatos"""
    print("\n" + "=" * 80)
    print("ANÁLISIS DE DIFERENCIAS DE FORMATO")
    print("=" * 80)
    
    # Formato testBellState.py (comillas simples)
    format1 = "https://algassert.com/quirk#circuit={'cols':[['H'],['•','X'],['Measure','Measure']]}"
    
    # Formato mutants_formatted.json (comillas dobles + URL encoding)
    format2 = "https://algassert.com/quirk#circuit={\"cols\":[[\"H\"],[\"•\",\"X\"],[\"Measure\",\"Measure\"]]}"
    
    print("\nFormato 1 (testBellState.py):")
    print(f"  {format1}")
    
    print("\nFormato 2 (mutants_formatted.json - equivalente):")
    print(f"  {format2}")
    
    print("\nDiferencias clave:")
    print("  1. Comillas: Simples (') vs Dobles (\\\")")
    print("  2. Escaping: Sin escape vs Con escape (\\\\\")")
    print("  3. Caracteres especiales: Directos vs URL-encoded")
    
    print("\n¿Cuál usar?")
    print("  - El formato del JSON (comillas dobles) es más estándar para JSON")
    print("  - Los caracteres están URL-encoded, lo cual es correcto para URLs")
    print("  - El servidor debería aceptar ambos formatos")

if __name__ == "__main__":
    try:
        test_single_circuit()
        compare_formats()
        
        print("\n" + "=" * 80)
        print("SIGUIENTE PASO:")
        print("  Si la validación fue exitosa, ejecutar: testQuirkRandomAWS.py")
        print("=" * 80)
        
    except FileNotFoundError:
        print("✗ Error: No se encontró el archivo 'mutants_formatted.json'")
        print("  Asegúrate de estar en el directorio Test/")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
