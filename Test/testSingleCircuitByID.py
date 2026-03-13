import requests
import time
import json
import os

# ============================================================================
# CONFIGURACIÓN - CAMBIA AQUÍ EL ID DEL CIRCUITO QUE QUIERES EJECUTAR
# ============================================================================
CIRCUIT_ID = "91236826447900465758395616691890872259"  # Cambia este ID

# Configuración de URLs
url_aws = 'http://54.155.193.167:8082/'
url_local = 'http://localhost:8082/'
url = url_local  # Cambiar según necesites

pathURL = 'url'
pathResult = 'result'

def load_circuit_by_id(json_file, circuit_id):
    """Busca un circuito por su ID en el archivo JSON"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            circuits = json.load(f)
        
        for circuit in circuits:
            if circuit.get('_id') == circuit_id:
                print(f"✓ Circuito encontrado: ID {circuit_id[:20]}...")
                return circuit
        
        print(f"✗ No se encontró el circuito con ID: {circuit_id}")
        return None
    except Exception as e:
        print(f"✗ Error al cargar el archivo: {e}")
        return None

def send_circuit_to_scheduler(circuit_data):
    """Envía un circuito al scheduler"""
    try:
        url_quirk = circuit_data.get('url', '')
        circuit_id = circuit_data.get('_id', 'unknown')
        
        # Forzar 1000 shots para controlar costos
        shots = 1000
        policy = circuit_data.get('policy', 'time')
        
        payload = {
            "url": url_quirk,
            "shots": shots,
            "provider": ['aws'],
            "policy": policy
        }
        
        print(f"\n📤 Enviando circuito al scheduler...")
        print(f"   • ID: {circuit_id}")
        print(f"   • Shots: {shots}")
        print(f"   • Policy: {policy}")
        print(f"   • Provider: AWS")
        
        start_time = time.time()
        response = requests.post(url + pathURL, json=payload, timeout=30)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            response_text = response.text
            if "Your id is " in response_text:
                scheduler_id = int(response_text.split("Your id is ")[1].strip())
                print(f"\n✓ Circuito enviado en {elapsed_time:.2f}s")
                print(f"   • Scheduler ID: {scheduler_id}")
                return scheduler_id
            else:
                print(f"\n✗ Respuesta inesperada: {response_text}")
                return None
        else:
            print(f"\n✗ Error HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"\n✗ Excepción al enviar: {str(e)}")
        return None

def get_circuit_results(scheduler_id, max_retries=15, retry_delay=5):
    """Recupera los resultados de un circuito"""
    print(f"\n📥 Esperando resultados...")
    print(f"   • Intentos máximos: {max_retries}")
    print(f"   • Delay entre intentos: {retry_delay}s")
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n   [{attempt}/{max_retries}] Consultando resultados...")
            response = requests.get(f"{url}{pathResult}?id={scheduler_id}", timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result and len(result) > 0:
                    print(f"\n✓ Resultados obtenidos!")
                    return result
                else:
                    print(f"      ⏳ Aún no disponible, esperando {retry_delay}s...")
                    time.sleep(retry_delay)
            else:
                print(f"      ⚠ HTTP {response.status_code}, esperando {retry_delay}s...")
                time.sleep(retry_delay)
                
        except Exception as e:
            print(f"      ⚠ Error: {str(e)[:50]}, esperando {retry_delay}s...")
            time.sleep(retry_delay)
    
    print(f"\n✗ No se obtuvieron resultados después de {max_retries} intentos")
    return None

def analyze_results(result):
    """Analiza y muestra estadísticas de los resultados"""
    print("\n" + "=" * 80)
    print("📊 ANÁLISIS DE RESULTADOS")
    print("=" * 80)
    
    if not result or len(result) == 0:
        print("✗ Sin resultados para analizar")
        return
    
    circuit_result = result[0]
    
    print(f"\n📌 Circuito:")
    print(f"   • ID: {circuit_result.get('_id', 'N/A')}")
    print(f"   • URL: {circuit_result.get('circuit', 'N/A')[:80]}...")
    
    values = circuit_result.get('value', {})
    
    if not values:
        print("\n✗ Sin valores de medición")
        return
    
    # Calcular estadísticas
    total_shots = sum(values.values())
    num_states = len(values)
    most_common = max(values.items(), key=lambda x: x[1])
    least_common = min(values.items(), key=lambda x: x[1])
    
    # Ordenar por frecuencia
    sorted_values = sorted(values.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n📈 Estadísticas:")
    print(f"   • Total shots ejecutados: {total_shots}")
    print(f"   • Estados únicos observados: {num_states}")
    print(f"   • Estado más común: |{most_common[0]}⟩ → {most_common[1]} veces ({most_common[1]/total_shots*100:.2f}%)")
    print(f"   • Estado menos común: |{least_common[0]}⟩ → {least_common[1]} veces ({least_common[1]/total_shots*100:.2f}%)")
    
    print(f"\n🔝 Top 10 estados más frecuentes:")
    for i, (state, count) in enumerate(sorted_values[:10], 1):
        percentage = count / total_shots * 100
        bar = '█' * int(percentage / 2)  # Barra visual
        print(f"   {i:2d}. |{state}⟩: {count:4d} shots ({percentage:5.2f}%) {bar}")
    
    if num_states > 10:
        print(f"\n   ... y {num_states - 10} estados más")
    
    # Distribución de probabilidades
    print(f"\n📊 Distribución:")
    ranges = [(0, 1), (1, 10), (10, 50), (50, 100), (100, float('inf'))]
    range_labels = ["<1%", "1-10%", "10-50%", "50-100%", ">100%"]
    
    for (min_pct, max_pct), label in zip(ranges, range_labels):
        count = sum(1 for c in values.values() if min_pct <= (c/total_shots*100) < max_pct)
        if count > 0:
            print(f"   • Estados con frecuencia {label}: {count}")
    
    print("\n" + "=" * 80)

def main():
    """Función principal"""
    print("=" * 80)
    print("TEST: Ejecución de Circuito Individual por ID")
    print("=" * 80)
    print(f"\n🎯 Circuito objetivo: {CIRCUIT_ID}")
    
    # Cargar circuito
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, 'mutants_7_Time.json')
    
    circuit = load_circuit_by_id(json_file, CIRCUIT_ID)
    
    if not circuit:
        print("\n✗ No se pudo cargar el circuito. Abortando.")
        return
    
    # Mostrar info del circuito
    print(f"\n📋 Información del circuito:")
    print(f"   • ID: {circuit.get('_id')}")
    print(f"   • Policy (JSON): {circuit.get('policy')}")
    print(f"   • Shots (JSON): {circuit.get('shots')} → Forzado a 1000")
    print(f"   • URL: {circuit.get('url')[:80]}...")
    
    print(f"\n⚙️  Configuración:")
    print(f"   • Servidor: {url}")
    print(f"   • Provider: AWS")
    print(f"   • Shots: 1000 (control de costos)")
    
    input("\n🚀 Presiona Enter para enviar el circuito o Ctrl+C para cancelar...")
    
    # Enviar circuito
    start_time = time.time()
    scheduler_id = send_circuit_to_scheduler(circuit)
    
    if not scheduler_id:
        print("\n✗ No se pudo enviar el circuito. Abortando.")
        return
    
    # Esperar un poco antes de consultar
    wait_time = 10
    print(f"\n⏳ Esperando {wait_time}s antes de consultar resultados...")
    time.sleep(wait_time)
    
    # Recuperar resultados
    results = get_circuit_results(scheduler_id)
    
    total_time = time.time() - start_time
    
    if not results:
        print("\n✗ No se pudieron obtener resultados.")
        return
    
    # Analizar y mostrar resultados
    analyze_results(results)
    
    # Guardar resultados
    output_file = f'single_circuit_results_{CIRCUIT_ID}_{int(time.time())}.json'
    output_path = os.path.join(script_dir, output_file)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'circuit_id': CIRCUIT_ID,
            'server_url': url,
            'total_time': total_time,
            'scheduler_id': scheduler_id,
            'results': results
        }, f, indent=2)
    
    print(f"\n💾 Resultados guardados en: {output_file}")
    print(f"\n⏱️  Tiempo total de ejecución: {total_time:.2f}s")
    print("\n" + "=" * 80)
    print("✓ Test completado exitosamente")
    print("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Test cancelado por el usuario")
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        import traceback
        traceback.print_exc()
