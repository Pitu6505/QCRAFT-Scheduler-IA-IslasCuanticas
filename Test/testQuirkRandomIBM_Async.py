import aiohttp
import asyncio
import time
import json 
import random
import os

# Configuración de URLs
url_aws = 'http://54.155.193.167:8082/'
url_local = 'http://localhost:8082/'
url = url_local  # Cambiar según necesites

pathURL = 'url'
pathResult = 'result'

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

def select_random_circuits(circuits, n=10):
    """Selecciona n circuitos de forma aleatoria"""
    if len(circuits) < n:
        print(f"⚠ Solo hay {len(circuits)} circuitos disponibles, seleccionando todos")
        return circuits
    
    selected = random.sample(circuits, n)
    print(f"✓ Seleccionados {len(selected)} circuitos aleatorios")
    return selected

async def send_circuit_async(session, circuit_data, circuit_index):
    """Envía un circuito al scheduler de forma asíncrona"""
    try:
        url_quirk = circuit_data.get('url', '')
        if not url_quirk.startswith("https://algassert.com/quirk#circuit="):
            print(f"[{circuit_index}] ⚠ URL no válida")
            return None
        
        # Forzar 1000 shots para controlar costos
        shots = 1000
        circuit_id = circuit_data.get('_id', 'unknown')
        policy = circuit_data.get('policy', 'time')
        
        payload = {
            "url": url_quirk,
            "shots": shots,
            "provider": ['ibm'],  # IBM tiene mejor soporte de compuertas
            "policy": policy
        }
        
        print(f"[{circuit_index}] 📤 Enviando circuito ID: {circuit_id[:20]}...")
        
        start_time = time.time()
        async with session.post(url + pathURL, json=payload, timeout=30) as response:
            elapsed_time = time.time() - start_time
            response_text = await response.text()
            
            if response.status == 200 and "Your id is " in response_text:
                scheduler_id = int(response_text.split("Your id is ")[1].strip())
                print(f"[{circuit_index}] ✓ Enviado en {elapsed_time:.2f}s → Scheduler ID: {scheduler_id}")
                return {
                    'circuit_id': circuit_id,
                    'scheduler_id': scheduler_id,
                    'status': 'submitted',
                    'shots': shots,
                    'submit_time': elapsed_time,
                    'index': circuit_index
                }
            else:
                print(f"[{circuit_index}] ✗ Error {response.status}")
                return {
                    'circuit_id': circuit_id,
                    'status': 'error',
                    'error': f"HTTP {response.status}",
                    'index': circuit_index
                }
                
    except asyncio.TimeoutError:
        print(f"[{circuit_index}] ✗ Timeout")
        return {
            'circuit_id': circuit_data.get('_id', 'unknown'),
            'status': 'timeout',
            'error': 'Request timeout',
            'index': circuit_index
        }
    except Exception as e:
        print(f"[{circuit_index}] ✗ Excepción: {str(e)}")
        return {
            'circuit_id': circuit_data.get('_id', 'unknown'),
            'status': 'exception',
            'error': str(e),
            'index': circuit_index
        }

async def get_circuit_results_async(session, scheduler_id, circuit_index, max_retries=10, retry_delay=5):
    """Recupera los resultados de un circuito de forma asíncrona"""
    for attempt in range(max_retries):
        try:
            async with session.get(f"{url}{pathResult}?id={scheduler_id}", timeout=10) as response:
                if response.status == 200:
                    result = await response.json()
                    if result and len(result) > 0:
                        print(f"[{circuit_index}] ✓ Resultados obtenidos (intento {attempt + 1})")
                        return {
                            'status': 'success',
                            'results': result
                        }
                    else:
                        print(f"[{circuit_index}] ⏳ Esperando... (intento {attempt + 1}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                else:
                    await asyncio.sleep(retry_delay)
                    
        except Exception as e:
            print(f"[{circuit_index}] ⚠ Error: {str(e)[:50]}")
            await asyncio.sleep(retry_delay)
    
    print(f"[{circuit_index}] ✗ No se obtuvieron resultados después de {max_retries} intentos")
    return {
        'status': 'timeout',
        'error': f'No results after {max_retries} retries'
    }

async def main():
    """Función principal asíncrona"""
    print("=" * 80)
    print("TEST ASÍNCRONO: Circuitos Quirk Aleatorios a IBM")
    print("=" * 80)
    print("\n✓ IBM tiene mejor soporte de compuertas quantum (cy, cz, cu, etc.)")
    print("✓ Todos los circuitos usan 1000 shots (control de costos)")
    print("✓ Envío asíncrono para mayor velocidad\n")
    
    # Cargar circuitos
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_file = os.path.join(script_dir, 'mutants_formatted.json')
    circuits = load_quirk_circuits(json_file)
    
    if not circuits:
        print("✗ No se pudieron cargar circuitos. Abortando.")
        return
    
    # Seleccionar circuitos
    num_circuits = 10
    selected_circuits = select_random_circuits(circuits, num_circuits)
    
    total_shots = num_circuits * 1000
    
    print(f"\n📊 Resumen:")
    print(f"  • Circuitos: {num_circuits}")
    print(f"  • Total shots: {total_shots:,}")
    print(f"  • Servidor: {url}")
    print(f"  • Modo: Asíncrono\n")
    
    input("Presiona Enter para continuar o Ctrl+C para cancelar...")
    
    # Crear sesión HTTP asíncrona
    connector = aiohttp.TCPConnector(limit=10)  # Máximo 10 conexiones simultáneas
    timeout = aiohttp.ClientTimeout(total=300)  # Timeout total de 5 minutos
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        
        # FASE 1: Enviar todos los circuitos en paralelo
        print("\n" + "=" * 80)
        print("📤 FASE 1: Enviando circuitos en paralelo...")
        print("=" * 80)
        
        phase1_start = time.time()
        send_tasks = [
            send_circuit_async(session, circuit, i+1) 
            for i, circuit in enumerate(selected_circuits)
        ]
        
        submitted_results = await asyncio.gather(*send_tasks)
        phase1_time = time.time() - phase1_start
        
        # Filtrar los enviados exitosamente
        submitted_circuits = [r for r in submitted_results if r and r['status'] == 'submitted']
        
        print(f"\n✓ Fase 1 completada en {phase1_time:.2f}s")
        print(f"  • Enviados: {len(submitted_circuits)}/{num_circuits}")
        print(f"  • Velocidad promedio: {phase1_time/num_circuits:.2f}s por circuito")
        
        if len(submitted_circuits) == 0:
            print("\n✗ No se enviaron circuitos exitosamente. Abortando.")
            return
        
        # Esperar antes de recuperar resultados
        wait_time = 15
        print(f"\n⏳ Esperando {wait_time}s antes de recuperar resultados...")
        await asyncio.sleep(wait_time)
        
        # FASE 2: Recuperar resultados en paralelo
        print("\n" + "=" * 80)
        print("📥 FASE 2: Recuperando resultados en paralelo...")
        print("=" * 80)
        
        phase2_start = time.time()
        result_tasks = [
            get_circuit_results_async(session, circ['scheduler_id'], circ['index'])
            for circ in submitted_circuits
        ]
        
        results_data = await asyncio.gather(*result_tasks)
        phase2_time = time.time() - phase2_start
        
        # Combinar resultados
        final_results = []
        success_count = 0
        error_count = 0
        
        for i, circ_info in enumerate(submitted_circuits):
            result_data = results_data[i]
            final_result = {
                'circuit_id': circ_info['circuit_id'],
                'scheduler_id': circ_info['scheduler_id'],
                'shots': circ_info['shots'],
                'submit_time': circ_info['submit_time'],
                **result_data
            }
            final_results.append(final_result)
            
            if result_data['status'] == 'success':
                success_count += 1
            else:
                error_count += 1
        
        print(f"\n✓ Fase 2 completada en {phase2_time:.2f}s")
        
        # RESUMEN FINAL
        total_time = phase1_time + wait_time + phase2_time
        print("\n" + "=" * 80)
        print("📊 RESUMEN FINAL")
        print("=" * 80)
        print(f"Tiempo total: {total_time:.2f}s")
        print(f"  • Fase 1 (envío): {phase1_time:.2f}s")
        print(f"  • Espera: {wait_time}s")
        print(f"  • Fase 2 (resultados): {phase2_time:.2f}s")
        print(f"\nResultados:")
        print(f"  ✓ Exitosos: {success_count}")
        print(f"  ✗ Errores/Timeouts: {error_count}")
        
        if error_count > 0:
            print("\nCircuitos con errores:")
            for result in final_results:
                if result.get('status') != 'success':
                    error_msg = result.get('error', 'Unknown error')
                    print(f"  • Circuit ID {result.get('circuit_id', 'unknown')[:20]}...: {error_msg}")
        
        # Guardar resultados
        output_file = f'test_quirk_ibm_async_results_{int(time.time())}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'server_url': url,
                'mode': 'async',
                'total_time': total_time,
                'phase1_time': phase1_time,
                'phase2_time': phase2_time,
                'total_circuits': len(final_results),
                'success_count': success_count,
                'error_count': error_count,
                'results': final_results
            }, f, indent=2)
        
        print(f"\n✓ Resultados guardados en: {output_file}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✗ Test cancelado por el usuario")
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        import traceback
        traceback.print_exc()
