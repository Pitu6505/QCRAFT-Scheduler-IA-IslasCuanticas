# Tests de Circuitos Quirk - Documentación

## 💰 IMPORTANTE: Control de Costos

**TODOS los tests fuerzan 1000 shots por circuito**, independientemente del valor en `mutants_formatted.json` (que contiene 10000).

- ✅ **testQuirkRandomIBM.py**: 10 circuitos × 1000 shots = **10,000 shots totales**
- 🚀 **testQuirkRandomIBM_Async.py**: 10 circuitos × 1000 shots = **10,000 shots totales** (más rápido)
- ⚠️ **testQuirkRandomAWS.py**: 5 circuitos × 1000 shots = **5,000 shots totales**
- ⚡ **testQuirkRandomAWS_Async.py**: 5 circuitos × 1000 shots = **5,000 shots totales** (más rápido)

Esto reduce los costos en un 90% comparado con usar los 10000 shots del JSON.

## 📋 Archivos Creados

### 1. `testQuirkFormatValidation.py`
**Propósito**: Validación rápida con 1 circuito
- Verifica el formato de las URLs de Quirk
- Compara formatos entre testBellState.py y mutants_formatted.json
- Prueba la conectividad con el servidor

**Uso**:
```bash
python Test/testQuirkFormatValidation.py
```

---

### 2. `testQuirkRandomIBM.py` (SÍNCRONO)
**Propósito**: Test con IBM (mejor compatibilidad)
- Envía 10 circuitos aleatorios a IBM con **1000 shots cada uno**
- IBM soporta más compuertas que AWS (cx, cy, cz, cu, crx, cry, crz)
- Menor tasa de errores de ValidationException
- **Costo controlado: 10,000 shots totales**
- **Modo**: Síncrono (un circuito a la vez, más lento)

**Uso**:
```bash
python Test/testQuirkRandomIBM.py
```

### 3. `testQuirkRandomIBM_Async.py` 🚀 RECOMENDADO
**Propósito**: Test con IBM (versión asíncrona, MUCHO más rápido)
- Envía 10 circuitos **en paralelo** usando `aiohttp` y `asyncio`
- **Hasta 10x más rápido** que la versión síncrona
- Misma funcionalidad que testQuirkRandomIBM.py pero con mejor rendimiento
- **Costo controlado: 10,000 shots totales**
- **Modo**: Asíncrono (máximo 10 conexiones simultáneas)

**Uso**:
```bash
python Test/testQuirkRandomIBM_Async.py
```

**Ventajas de la versión async**:
- ⚡ Envío paralelo de todos los circuitos
- ⚡ Recuperación paralela de resultados
- 📊 Métricas de tiempo detalladas por fase
- 💾 Resultados guardados con timestamp

---

### 4. `testQuirkRandomAWS.py` (SÍNCRONO)
**Propósito**: Test con AWS (compatibilidad limitada)
- Envía 5 circuitos a AWS con **1000 shots cada uno** (por defecto)
- Muchos circuitos fallarán por compuertas no soportadas
- AWS solo soporta: x, y, z, h, s, t, rx, ry, rz, cnot, swap
- **Flujo correcto**: Envía → obtiene ID → recupera resultados

**Uso**:
```bash
python Test/testQuirkRandomAWS.py
```

### 5. `testQuirkRandomAWS_Async.py` ⚡
**Propósito**: Test con AWS (versión asíncrona)
- Envía 5 circuitos **en paralelo** usando `aiohttp` y `asyncio`
- **Más rápido** que la versión síncrona
- Misma compatibilidad limitada de AWS para compuertas
- **Costo controlado: 5,000 shots totales**

**Uso**:
```bash
python Test/testQuirkRandomAWS_Async.py
```

**Nota**: Ajusta `num_circuits` en el código para cambiar la cantidad de circuitos.

---

## 🔄 Flujo del Scheduler

Los tests ahora siguen el **flujo correcto** del scheduler, como en testScheduler.py:

### Versión Síncrona (testQuirkRandomIBM.py / testQuirkRandomAWS.py):

**Fase 1: Envío secuencial 📤**
```python
for circuit in selected_circuits:
    POST /url
    scheduler_ids.append(response_id)
```

**Fase 2: Espera ⏳**
```python
time.sleep(10)  # Dar tiempo al scheduler
```

**Fase 3: Recuperación secuencial 📥**
```python
for scheduler_id in scheduler_ids:
    GET /result?id={scheduler_id}
```

### Versión Asíncrona (testQuirkRandomIBM_Async.py / testQuirkRandomAWS_Async.py):

**Fase 1: Envío paralelo 📤**
```python
tasks = [send_circuit_async(circuit) for circuit in selected_circuits]
results = await asyncio.gather(*tasks)  # Todos en paralelo
```

**Fase 2: Espera asíncrona ⏳**
```python
await asyncio.sleep(15)
```

**Fase 3: Recuperación paralela 📥**
```python
tasks = [get_results_async(id) for id in scheduler_ids]
results = await asyncio.gather(*tasks)  # Todos en paralelo
```

### Formato del Payload:
```python
POST /url
{
  "url": "https://algassert.com/quirk#circuit={...}",
  "shots": 1000,
  "provider": ['ibm'],  # o ['aws']
  "policy": "time"
}
```
**Respuesta**: `"Your id is <scheduler_id>"`

### Recuperación de Resultados:
```python
GET /result?id=<scheduler_id>
```
- Reintenta hasta 10 veces con pausas de 5s
- Devuelve los resultados cuando estén disponibles

---

## ⚠️ Problema: Compuertas No Soportadas

### Error Común
```
ValidationException: uses a gate: cy which is not supported by the device
```

### Causa
Los circuitos de Quirk usan compuertas que no todos los proveedores soportan:

| Compuerta | IBM | AWS |
|-----------|-----|-----|
| cx (CNOT) | ✅  | ✅  |
| cy        | ✅  | ❌  |
| cz        | ✅  | ❌  |
| cu        | ✅  | ❌  |
| h, x, y, z| ✅  | ✅  |
| rx, ry, rz| ✅  | ✅  |
| crx, cry, crz | ✅  | ❌  |
| swap      | ✅  | ✅  |

### Soluciones

#### Opción 1: Usar IBM (Recomendado) ✅
```python
payload = {
    "url": url_quirk,
    "shots": 1000,
    "provider": ['ibm'],  # Mejor soporte
    "policy": "time"
}
```

#### Opción 2: Filtrar Circuitos
Crear un script que analice los circuitos y filtre los incompatibles con AWS.

#### Opción 3: Transpilación Avanzada
Mejorar el translator para descomponer compuertas no soportadas:
- `cy` → combinación de `rx`, `ry`, `cnot`
- `cz` → combinación de `h`, `cnot`

#### Opción 4: Usar Simuladores
En lugar de hardware real, usar simuladores que soportan todas las compuertas.

---

## 🔧 Bugs Corregidos

### 1. scheduler_policies.py - Argumento 'machine' faltante

**Problema**: Faltaba el argumento `machine` en llamadas a `executeCircuit`

**Líneas corregidas**:
- Línea 911: `send_shots_depth`
- Línea 987: `send_shots`
- Línea 1036: `send` (time policy)

**Antes**:
```python
executeCircuit(json.dumps(data), qb, shotsUsr, provider, urls)  # ❌ Falta machine
```

**Después**:
```python
executeCircuit(json.dumps(data), qb, shotsUsr, provider, urls, machine)  # ✅ Correcto
```

### 2. ResettableTimer.py - Error "threads can only be started once"

**Problema**: El método `start()` intentaba reiniciar un Thread ya ejecutado

**Línea corregida**: 51-59

**Antes**:
```python
def start(self) -> None:
    with self.lock:
        if not self.timer.is_alive():
            self.timer.start()  # ❌ Falla si el thread ya fue ejecutado
```

**Después**:
```python
def start(self) -> None:
    with self.lock:
        if not self.timer.is_alive():
            # Si el timer ya fue ejecutado, crear uno nuevo
            # Un Thread solo puede ser iniciado una vez
            if self.timer.ident is not None:
                self.timer = Timer(self.timeout, self.callback_wrapper)
            self.timer.start()  # ✅ Ahora funciona correctamente
```

**Explicación**: En Python, un objeto `Thread` solo puede ser iniciado una vez. Si intentas llamar `.start()` en un thread que ya terminó, obtienes el error "threads can only be started once". La solución es verificar si el thread ya fue ejecutado (usando `thread.ident is not None`) y crear un nuevo objeto Timer antes de iniciarlo.

---

## 📊 Formato de Datos

### mutants_formatted.json
```json
{
  "_id": "327816601333825286454701882607470697509",
  "url": "https://algassert.com/quirk#circuit={\"cols\":[[\"X\",\"H\"],[\"•\",\"X\"]]}",
  "shots": 10000,  // ⚠️ Este valor es IGNORADO por los tests
  "policy": "time"
}
```

### Payload para el Scheduler (usado por los tests)
```python
{
  "url": "https://algassert.com/quirk#circuit={...}",
  "shots": 1000,  # ✅ FORZADO a 1000 para control de costos
  "provider": ['ibm'],  # o ['aws'] o ['ibm', 'aws']
  "policy": "time"      # o "Islas_Cuanticas", "Optimizacion_ML", etc.
}
```

**Nota importante**: Los tests **ignoran** el valor de `shots` del JSON y siempre usan **1000 shots** para reducir costos en un 90%.

---

## 🚀 Flujo de Trabajo Recomendado

### Para desarrollo/pruebas rápidas:

1. **Validar formato** (1 circuito, 1000 shots):
   ```bash
   python Test/testQuirkFormatValidation.py
   ```
   💰 Costo: ~1,000 shots

2. **Prueba pequeña con IBM ASÍNCRONO** (10 circuitos, 1000 shots cada uno):
   ```bash
   python Test/testQuirkRandomIBM_Async.py
   ```
   💰 Costo: ~10,000 shots
   ⚡ Tiempo: ~30-60 segundos

### Para pruebas a gran escala:

3. **Aumentar cantidad** en el archivo:
   ```python
   num_circuits = 100  # Cambiar de 10 a 100
   ```
   ```bash
   python Test/testQuirkRandomIBM_Async.py
   ```
   💰 Costo: ~100,000 shots
   ⚡ Tiempo: ~5-10 minutos (vs ~30-50 minutos en versión síncrona)

4. **Para AWS**: Solo si sabes que los circuitos son compatibles
   ```bash
   python Test/testQuirkRandomAWS_Async.py
   ```
   ⚠️ Costo: ~5,000 shots (muchos fallarán por compuertas no soportadas)

---

## 💰 Estimación de Costos

### Con 1000 shots (configuración actual):
- **Validación**: 1 circuito = 1,000 shots
- **Test IBM pequeño**: 10 circuitos = 10,000 shots
- **Test IBM grande**: 100 circuitos = 100,000 shots
- **Test AWS**: 5 circuitos = 5,000 shots (pero ~60-80% fallarán)

### Comparación con 10000 shots (valor del JSON):
- **10 circuitos**: 100,000 shots (vs 10,000 actual) → **10x más caro** ❌
- **100 circuitos**: 1,000,000 shots (vs 100,000 actual) → **10x más caro** ❌

**Ahorro total: 90% en costos** ✅

---

## ⚡ Comparación de Rendimiento: Síncrono vs Asíncrono

### Tiempo estimado para 10 circuitos:

| Fase | Síncrono | Asíncrono | Mejora |
|------|----------|-----------|--------|
| Envío | 50s (5s×10) | 10s (paralelo) | **5x más rápido** |
| Espera | 10s | 15s | - |
| Recuperación | 100s (10s×10) | 15s (paralelo) | **6.6x más rápido** |
| **TOTAL** | **~160s** | **~40s** | **4x más rápido** |

### Con 100 circuitos:

| Operación | Síncrono | Asíncrono | Mejora |
|-----------|----------|-----------|--------|
| Tiempo total | ~1500s (25 min) | ~300s (5 min) | **5x más rápido** |

**Conclusión**: La versión asíncrona es **4-5x más rápida**, especialmente con muchos circuitos.

---

## 🎯 Estadísticas Esperadas

### Con IBM:
- ✅ Tasa de éxito: ~80-90%
- ⚠️ Algunos circuitos pueden fallar por límites de qubits o depth
- 🚀 Versión async recomendada para mejor rendimiento

### Con AWS:
- ⚠️ Tasa de éxito: ~20-40%
- ❌ Muchos fallos por compuertas no soportadas (cy, cz, cu, crx, cry, crz)
- 💡 Usar solo para circuitos simples o compatibles

---

## 📝 Notas Adicionales

### Archivos de salida:
- Los resultados se guardan automáticamente en archivos JSON con timestamp:
  - `test_quirk_ibm_async_results_<timestamp>.json`
  - `test_quirk_aws_async_results_<timestamp>.json`

### Características de las versiones asíncronas:
- Máximo 10 conexiones HTTP simultáneas (configurable en `TCPConnector`)
- Timeout total de 5 minutos por sesión
- Manejo de errores individual por circuito
- Métricas detalladas de tiempo por fase

### Configuración de servidor:
- Por defecto: `url_local = 'http://localhost:8082/'`
- Producción: `url_aws = 'http://54.155.193.167:8082/'`
- Cambiar en el código: `url = url_local` o `url = url_aws`

### Dependencias:
- **Síncronos**: `requests`, `json`, `random`, `os`, `time`
- **Asíncronos**: `aiohttp`, `asyncio`, `json`, `random`, `os`, `time`

### Instalación de dependencias:
```bash
pip install aiohttp requests
```

---

## 🔗 Referencias

- **Formato Quirk**: https://algassert.com/quirk
- **Archivo de datos**: `Test/mutants_formatted.json` (8066 circuitos)
- **Scheduler**: `scheduler.py`
- **Políticas**: `scheduler_policies.py`
- **Traducción**: `translator.py`
- **Test de referencia**: `testScheduler.py`
