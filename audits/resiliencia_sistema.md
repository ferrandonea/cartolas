# Auditoría de Resiliencia del Sistema

**Fecha:** 2026-03-16
**Alcance:** Timeout handling, retry logic, circuit breaker, bulkhead, degradación graceful, rate limiting

**Calificación global de resiliencia: 4/10**

---

## 1. Timeout Handling

**Importancia: 7/10**

### Hallazgos

| Ubicación | Detalle | Problema |
|-----------|---------|----------|
| `cartolas/config.py:17` | `TIMEOUT = 500_000` (8.33 min) | Timeout excesivamente alto para una sola operación |
| `cartolas/download.py:25-26` | `page.goto(url_str, timeout=timeout)` | Hereda el timeout global sin granularidad |
| `cartolas/download.py:108` | `click(timeout=TIMEOUT)` en botón GENERAR ARCHIVO | Mismo timeout para un click que para navegación |
| `eco/bcentral.py` | Llamadas a `bcchapi` | Sin timeout explícito configurado |
| `comparador/elmer.py:91` | `requests.get(url)` | **Sin timeout** - puede bloquear indefinidamente |

### Remediación

**`comparador/elmer.py:91`** - Agregar timeout a requests (crítico):
```python
# Antes
response = requests.get(url)

# Después
response = requests.get(url, timeout=30)
```

**`cartolas/config.py`** - Timeouts progresivos:
```python
# Antes
TIMEOUT = 500_000

# Después
TIMEOUT_NAVIGATION = 60_000   # 1 min para navegación
TIMEOUT_DOWNLOAD = 300_000    # 5 min para descarga de archivo
TIMEOUT_CLICK = 30_000        # 30s para interacciones UI
```

---

## 2. Retry Logic

**Importancia: 8/10**

### Hallazgos

| Ubicación | Detalle | Problema |
|-----------|---------|----------|
| `utiles/decorators.py:12-44` | `@retry_function` (10 intentos, delay fijo 10s) | Captura `Exception` (demasiado amplio) |
| `utiles/decorators.py:47-81` | `@exp_retry_function` (12 intentos, backoff 2^n) | Puede esperar hasta **4096 segundos** (68 min) en un solo intento |
| `cartolas/download.py:29-30` | `@exp_retry_function` + `@retry_function` apilados | Combinación: hasta **120 reintentos** con espera total de **2+ horas** |
| `utiles/decorators.py:33` | `except Exception as e` | Captura `KeyboardInterrupt`, `SystemExit`, etc. |
| `utiles/decorators.py:42` | `raise Exception(...)` genérico final | Pierde el traceback original y tipo de excepción |

### Remediación

**`utiles/decorators.py`** - Excepciones específicas y presupuesto de tiempo:
```python
# Antes
def retry_function(func, max_attempts: int = 10, delay: int = 10):
    @wraps(func)
    def wrapper(*args, **kwargs):
        attempts = 0
        while attempts < max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                # ...
        raise Exception(f"No se pudo ejecutar {func.__name__}...")

# Después
RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError, requests.RequestException)

def retry_function(func, max_attempts: int = 10, delay: int = 10, max_total_time: int = 300):
    @wraps(func)
    def wrapper(*args, **kwargs):
        attempts = 0
        start = time.monotonic()
        last_exception = None
        while attempts < max_attempts:
            if time.monotonic() - start > max_total_time:
                break
            try:
                return func(*args, **kwargs)
            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                attempts += 1
                print(f"Error en {func.__name__}: {e}")
                print(f"Intento {attempts}/{max_attempts}. Esperando {delay} segundos")
                time.sleep(delay)
        raise last_exception  # Preserva tipo y traceback original
    return wrapper
```

**`cartolas/download.py:29-30`** - No apilar dos decoradores de retry:
```python
# Antes
@exp_retry_function
@retry_function
def get_cartola_from_cmf(...):

# Después - usar solo uno con configuración adecuada
@exp_retry_function  # max_attempts=8, max_total_time=600
def get_cartola_from_cmf(...):
```

### Sin idempotencia verificada

Las descargas de CMF no verifican si el archivo ya fue descargado exitosamente antes de reintentar. Si un reintento ocurre después de una descarga parcial, podría generar archivos corruptos.

---

## 3. Circuit Breaker Pattern

**Importancia: 6/10**

### Hallazgos

**No implementado.** No existe detección de fallos sostenidos ni mecanismo para dejar de intentar cuando un servicio externo está caído.

| Servicio | Impacto sin circuit breaker |
|----------|---------------------------|
| CMF (scraping) | Reintentos infinitos contra sitio caído, consumo de recursos |
| El Mercurio API | Requests sin timeout pueden bloquear el proceso completo |
| BCCh API | Sin fallback si la API está fuera de servicio |

### Remediación

Implementación mínima sin dependencias externas:

```python
# utiles/circuit_breaker.py
import time

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half_open

    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
            else:
                raise ConnectionError(f"Circuit breaker abierto. Reintentar en {self.recovery_timeout}s")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
```

---

## 4. Bulkhead Pattern

**Importancia: 3/10**

### Hallazgos

**No implementado.** El proyecto es un pipeline batch single-threaded, por lo que el impacto es bajo.

| Aspecto | Estado |
|---------|--------|
| Aislamiento de recursos | No aplica (single-thread) |
| Connection pooling | No configurado en requests |
| Thread pools | No usados |
| Playwright browser instances | Una instancia por ejecución (adecuado) |

### Remediación

Bajo impacto dado el modelo de ejecución batch. Si el proyecto escala a concurrencia:

```python
# Limitar conexiones simultáneas para requests
import requests
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=5, pool_maxsize=5)
session.mount("https://", adapter)
```

---

## 5. Degradación Graceful

**Importancia: 7/10**

### Hallazgos positivos

| Ubicación | Patrón | Calidad |
|-----------|--------|---------|
| `eco/bcentral.py:206-227` | Si parquet no existe, descarga desde fecha 1970 | Bueno |
| `comparador/elmer.py:205-238` | Cache por mes: reutiliza JSON del mismo mes | Bueno |
| `comparador/merge.py:74-78` | `fill_null(1)` para tipo de cambio faltante | Aceptable |
| `comparador/cla_monthly.py:137-138` | `fill_nan(1).fill_null(1)` para rentabilidad | Aceptable |
| `utiles/file_tools.py:120-134` | Retorna `None` si no encuentra archivo reciente | Bueno |

### Hallazgos negativos

| Ubicación | Problema | Impacto |
|-----------|----------|---------|
| `eco/bcentral.py:18-25` | `.env` se lee sin manejo de errores | Crash si falta `.env` o variables |
| `comparador/elmer.py:91-103` | Retorna `None` silenciosamente en JSONDecodeError | Datos incompletos sin alerta |
| `cartolas/read.py` | Sin fallback si parquet corrupto | Crash total |

### Remediación

**`eco/bcentral.py:18-25`** - Manejo de variables de entorno:
```python
# Antes
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]

# Después
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables.get("BCCH_PASS")
BCCH_USER = env_variables.get("BCCH_USER")

if not BCCH_PASS or not BCCH_USER:
    print("ADVERTENCIA: Credenciales BCCh no configuradas en .env. Funciones BCCh deshabilitadas.")
```

---

## 6. Rate Limiting

**Importancia: 6/10**

### Hallazgos

| Ubicación | Servicio | Rate limit |
|-----------|----------|------------|
| `comparador/elmer.py:154` | El Mercurio API | **Ninguno** - loop sin delay entre requests |
| `cartolas/download.py:138` | CMF | `sleep(1)` entre rangos de fecha (mínimo) |
| `eco/bcentral.py` | BCCh API | Delegado a `bcchapi` (sin verificar) |

### Remediación

**`comparador/elmer.py`** - Agregar delay entre requests:
```python
# En get_all_elmer_data(), dentro del loop
for i in range(1, max_number):
    datos = get_elmer_data(i, verbose=verbose)
    time.sleep(0.5)  # Rate limit: max 2 req/s
    if datos:
        # ...
```

---

## 7. Logging y Observabilidad

**Importancia: 8/10**

### Hallazgos

| Aspecto | Estado |
|---------|--------|
| Librería de logging | No usa `logging` de Python, solo `print()` |
| Niveles de log | No existen |
| Timestamps | No incluidos en prints |
| Formato estructurado | No |
| Flag `verbose` | Inconsistente entre funciones |
| Métricas | Solo `@timer` decorator |

### Remediación

```python
# utiles/logging.py
import logging

def setup_logger(name: str = "cartolas") -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

---

## Resumen de hallazgos

| # | Hallazgo | Importancia | Área |
|---|----------|:-----------:|------|
| 1 | Retry decorators apilados pueden causar esperas de 2+ horas | 8/10 | Retry Logic |
| 2 | `except Exception` captura excepciones de sistema (KeyboardInterrupt) | 8/10 | Retry Logic |
| 3 | Sin logging estructurado (solo `print()`) | 8/10 | Observabilidad |
| 4 | `requests.get()` sin timeout en El Mercurio API | 7/10 | Timeout |
| 5 | Timeout global de 8.33 min sin granularidad | 7/10 | Timeout |
| 6 | Crash si `.env` falta o variables no definidas | 7/10 | Degradación |
| 7 | Sin circuit breaker para servicios externos | 6/10 | Circuit Breaker |
| 8 | Sin rate limiting en llamadas a El Mercurio API | 6/10 | Rate Limiting |
| 9 | Excepción final genérica pierde traceback original | 5/10 | Retry Logic |
| 10 | JSONDecodeError silencioso en elmer.py | 5/10 | Degradación |
| 11 | Sin health checks para servicios externos | 4/10 | Circuit Breaker |
| 12 | Sin connection pooling en requests | 3/10 | Bulkhead |

### Patrones positivos encontrados

- Cache mensual de datos El Mercurio (evita descargas innecesarias)
- Fallback a valores neutros (`fill_null(1)`) para datos financieros faltantes
- Validación de esquema estricta con Polars
- Context managers para Playwright
- Validación de inputs con mensajes claros
- Configuración centralizada en `config.py`

### Prioridad de remediación recomendada

1. **Inmediato**: Agregar timeout a `requests.get()` en `elmer.py`
2. **Inmediato**: Capturar excepciones específicas en decorators (no `Exception`)
3. **Corto plazo**: Eliminar apilamiento de retry decorators
4. **Corto plazo**: Manejo de `.env` faltante en `bcentral.py`
5. **Mediano plazo**: Implementar logging con `logging` module
6. **Mediano plazo**: Agregar rate limiting a APIs externas
7. **Largo plazo**: Circuit breaker para servicios críticos
