import requests
import time
import json 
import random
import os

# Configuración de URLs
# Cambiar a la URL de AWS cuando esté listo
url_aws = 'http://54.155.193.167:8082/'
url_local = 'http://localhost:8082/'
url = url_local  # Usar AWS por defecto

pathURL = 'url'
pathResult = 'result'
pathCircuit = 'circuit'

def load_quirk_circuits(json_file):
    """Carga los circuitos del archivo JSON"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            circuits = json.load(f)
        print(f"✓ Se cargaron {len(circuits)} circuitos del archivo")
        return circuits
    except Exception as e:
        print(f"✗ Error al cargar el archivo: {e}")
        return []

def select_random_circuits(circuits, n=1):
    """Selecciona n circuitos de forma aleatoria"""
    if len(circuits) < n:
        print(f"⚠ Solo hay {len(circuits)} circuitos disponibles, seleccionando todos")
        return circuits
    
    selected = random.sample(circuits, n)
    print(f"✓ Seleccionados {len(selected)} circuitos aleatorios")
    return selected

def check_url_format(url_string):
    """
    Verifica y corrige el formato de la URL de Quirk si es necesario.
    En el JSON las URLs ya vienen correctamente formateadas con comillas dobles
    y caracteres especiales URL-encoded.
    """
    # Verificar que es una URL de Quirk válida
    if not url_string.startswith("https://algassert.com/quirk#circuit="):
        print(f"⚠ URL no válida: {url_string[:50]}...")
        return None
    
    # El formato ya está correcto en el JSON (comillas dobles, URL encoding)
    return url_string

def send_circuit_to_scheduler(circuit_data, circuit_index):
    """Envía un circuito al scheduler y retorna el ID asignado"""
    try:
        # Verificar y preparar los datos
        url_quirk = check_url_format(circuit_data.get('url', ''))
        if not url_quirk:
            return None
        
        # Forzar 1000 shots para controlar costos (ignorar valor del JSON)
        shots = 1000
        circuit_id = circuit_data.get('_id', 'unknown')
        policy = circuit_data.get('policy', 'time')
        
        # Preparar el payload con provider y policy
        payload = {
            "url": url_quirk,
            "shots": shots,
            "provider": ['aws'],  # Especificar AWS como provider
            "policy": policy       # Usar la policy del JSON (generalmente 'time')
        }
        
        print(f"\n[{circuit_index}] Enviando circuito ID: {circuit_id}")
        print(f"    Shots: {shots}")
        print(f"    Policy: {policy}")
        print(f"    Provider: AWS")
        print(f"    URL: {url_quirk[:80]}...")
        
        # Enviar petición POST al scheduler
        start_time = time.time()
        response = requests.post(url + pathURL, json=payload, timeout=30)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            # Extraer el scheduler_id de la respuesta
            response_text = response.text
            if "Your id is " in response_text:
                scheduler_id = int(response_text.split("Your id is ")[1].strip())
                print(f"    ✓ Circuito enviado en {elapsed_time:.2f}s - Scheduler ID: {scheduler_id}")
                return {
                    'circuit_id': circuit_id,
                    'scheduler_id': scheduler_id,
                    'status': 'submitted',
                    'shots': shots,
                    'submit_time': elapsed_time
                }
            else:
                print(f"    ✗ Respuesta inesperada: {response_text}")
                return {
                    'circuit_id': circuit_id,
                    'status': 'error',
                    'error': 'Unexpected response format',
                    'response': response_text
                }
        else:
            print(f"    ✗ Error {response.status_code}: {response.text}")
            return {
                'circuit_id': circuit_id,
                'status': 'error',
                'error': f"HTTP {response.status_code}",
                'response': response.text
            }
            
    except requests.exceptions.Timeout:
        print(f"    ✗ Timeout después de 30s")
        return {
            'circuit_id': circuit_data.get('_id', 'unknown'),
            'status': 'timeout',
            'error': 'Request timeout'
        }
    except Exception as e:
        print(f"    ✗ Excepción: {str(e)}")
        return {
            'circuit_id': circuit_data.get('_id', 'unknown'),
            'status': 'exception',
            'error': str(e)
        }

def get_circuit_results(scheduler_id, circuit_index, max_retries=10, retry_delay=5):
    """Recupera los resultados de un circuito usando su scheduler_id"""
    print(f"\n[{circuit_index}] Recuperando resultados para Scheduler ID: {scheduler_id}")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(f"{url}{pathResult}?id={scheduler_id}", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                # Verificar si hay resultados disponibles
                if result and len(result) > 0:
                    print(f"    ✓ Resultados obtenidos (intento {attempt + 1}/{max_retries})")
                    return {
                        'status': 'success',
                        'results': result
                    }
                else:
                    print(f"    ⏳ Esperando resultados (intento {attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
            else:
                print(f"    ⚠ HTTP {response.status_code} (intento {attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                
        except Exception as e:
            print(f"    ✗ Error en intento {attempt + 1}: {str(e)}")
            time.sleep(retry_delay)
    
    print(f"    ✗ No se obtuvieron resultados después de {max_retries} intentos")
    return {
        'status': 'timeout',
        'error': f'No results after {max_retries} retries'
    }

def main():
    """Función principal del test"""
    print("=" * 80)
    print("TEST: Circuitos Quirk Aleatorios a AWS")
    print("=" * 80)
    print("\n⚠️  ADVERTENCIA IMPORTANTE:")
    print("Algunos circuitos de Quirk pueden usar compuertas no soportadas por AWS.")
    print("Compuertas problemáticas: cy, cz, cu, crx, cry, crz, etc.")
    print("AWS soporta solo: x, y, z, h, s, t, rx, ry, rz, cnot, swap, etc.")
    print("Los circuitos incompatibles fallarán con ValidationException.\n")
    print("💰 CONTROL DE COSTOS:")
    print("Todos los circuitos se enviarán con 1000 shots (ignorando valor del JSON)")
    print("Esto reduce costos significativamente.\n")
    
    # Cargar circuitos del JSON (mismo directorio que el script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, 'mutants_formatted.json')
    circuits = load_quirk_circuits(json_file)
    
    if not circuits:
        print("✗ No se pudieron cargar circuitos. Abortando.")
        return
    
    # Seleccionar 100 circuitos aleatorios
    num_circuits = 5 
    selected_circuits = select_random_circuits(circuits, num_circuits)
    
    # Calcular shots totales
    total_shots = num_circuits * 1000
    
    # Confirmar antes de enviar
    print(f"\n¿ Enviar {len(selected_circuits)} circuitos a {url}?")
    print(f"📊 Total de shots: {total_shots:,} (1000 shots × {len(selected_circuits)} circuitos)")
    print("🔄 El scheduler traducirá los circuitos y aplicará la política seleccionada")
    print("Presiona Enter para continuar o Ctrl+C para cancelar...")
    input()
    
    # Inicializar contadores y listas
    results = []
    success_count = 0
    error_count = 0
    
    # Enviar circuitos y recopilar IDs del scheduler
    submitted_circuits = []
    
    print(f"\n📤 FASE 1: Enviando circuitos al scheduler...")
    print("-" * 80)
    
    for i, circuit in enumerate(selected_circuits, 1):
        result = send_circuit_to_scheduler(circuit, i)
        
        if result and result['status'] == 'submitted':
            submitted_circuits.append(result)
        elif result:
            # Error al enviar
            result['phase'] = 'submission'
            results.append(result)
            error_count += 1
        
        # Pausa breve para no saturar el servidor
        if i < len(selected_circuits):
            time.sleep(0.5)
    
    print(f"\n✓ {len(submitted_circuits)} circuitos enviados correctamente")
    print(f"✗ {error_count} errores en el envío")
    
    if len(submitted_circuits) == 0:
        print("\n✗ No se enviaron circuitos exitosamente. Abortando.")
        return
    
    # Esperar un poco antes de empezar a recuperar resultados
    wait_time = 10
    print(f"\n⏳ Esperando {wait_time}s antes de recuperar resultados...")
    time.sleep(wait_time)
    
    # Recuperar resultados
    print(f"\n📥 FASE 2: Recuperando resultados del scheduler...")
    print("-" * 80)
    
    for i, circuit_info in enumerate(submitted_circuits, 1):
        scheduler_id = circuit_info['scheduler_id']
        circuit_id = circuit_info['circuit_id']
        
        result_data = get_circuit_results(scheduler_id, i)
        
        final_result = {
            'circuit_id': circuit_id,
            'scheduler_id': scheduler_id,
            'shots': circuit_info['shots'],
            'submit_time': circuit_info['submit_time'],
            **result_data
        }
        
        results.append(final_result)
        
        if result_data['status'] == 'success':
            success_count += 1
        else:
            error_count += 1
        
        # Pausa entre consultas
        if i < len(submitted_circuits):
            time.sleep(1)
    
    # Resumen de resultados
    print("\n" + "=" * 80)
    print("RESUMEN DE RESULTADOS")
    print("=" * 80)
    print(f"Total de circuitos procesados: {len(results)}")
    print(f"✓ Exitosos (con resultados): {success_count}")
    print(f"✗ Errores/Timeouts: {error_count}")
    
    if error_count > 0:
        print("\nCircuitos con errores:")
        for result in results:
            if result.get('status') != 'success':
                error_msg = result.get('error', 'Unknown error')
                phase = result.get('phase', 'execution')
                print(f"  - Circuit ID {result.get('circuit_id', 'unknown')} [{phase}]: {error_msg}")
    
    # Guardar resultados en archivo
    output_file = f'test_quirk_aws_results_{int(time.time())}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'server_url': url,
            'total_circuits': len(results),
            'success_count': success_count,
            'error_count': error_count,
            'results': results
        }, f, indent=2)
    
    print(f"\n✓ Resultados guardados en: {output_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Test cancelado por el usuario")
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        import traceback
        traceback.print_exc()
