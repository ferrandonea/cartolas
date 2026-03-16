# Auditoría de Resiliencia del Sistema — Cartolas

**Fecha:** 2026-03-16
**Alcance:** Timeout handling, retry logic, circuit breaker, bulkhead, degradación graceful, rate limiting, error handling.
**Resiliencia general:** **4/10**

---

## 1. Timeout Handling

**Resiliencia: 3/10 · Importancia: 8/10**

### Hallazgos

| Ubicación | Estado | Detalle |
|-----------|--------|---------|
| `cartolas/config.py:17` | `TIMEOUT = 500_000` (500s) | Único timeout global, usado para Playwright |
| `cartolas/download.py:25` | `page.goto(url, timeout=timeout)` | Navegación CMF con timeout |
| `cartolas/download.py:108` | `.click(timeout=TIMEOUT)` | Submit del formulario con timeout |
| `comparador/elmer.py:89` | `requests.get(url)` | **SIN TIMEOUT** — puede colgar indefinidamente |
| `eco/bcentral.py:78,106,225` | `BCCh.cuadro(...)` | **SIN TIMEOUT** — depende de bcchapi |
| Operaciones Polars (transform/save) | — | **SIN TIMEOUT** en operaciones de datos |

### Remediación

**elmer.py — Agregar timeout a requests.get (crítico):**

```python
# comparador/elmer.py:89
# Antes:
response = requests.get(url)

# Después:
response = requests.get(url, timeout=30)
```

**bcentral.py — Envolver llamadas bcchapi con timeout:**

```python
# eco/bcentral.py — agregar al inicio
import signal

class TimeoutError(Exception):
    pass

def with_timeout(func, timeout_seconds=60):
    def handler(signum, frame):
        raise TimeoutError(f"Operación excedió {timeout_seconds}s")
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout_seconds)
    try:
        result = func()
    finally:
        signal.alarm(0)
    return result
```

---

## 2. Retry Logic

**Resiliencia: 5/10 · Importancia: 7/10**

### Hallazgos

| Ubicación | Patrón | Problema |
|-----------|--------|----------|
| `utiles/decorators.py:12-44` | `@retry_function` — delay fijo 10s, max 10 intentos | Captura `Exception` genérica, no distingue errores transitorios de permanentes |
| `utiles/decorators.py:47-81` | `@exp_retry_function` — backoff 2^n, max 12 intentos | Max delay = 2^12 = 4096s (68 min) sin cap |
| `cartolas/download.py:29-30` | **Decoradores apilados**: `@exp_retry_function` + `@retry_function` | Hasta 10 × 12 = **120 intentos** posibles |
| `comparador/elmer.py:89` | `requests.get(url)` | **SIN RETRY** |
| `eco/bcentral.py:78,106,225` | Llamadas a BCCh API | **SIN RETRY** |

### Remediación

**decorators.py — Distinguir errores transitorios (crítico):**

```python
# utiles/decorators.py — definir excepciones retriable
TRANSIENT_ERRORS = (
    ConnectionError,
    TimeoutError,
    OSError,
)

def retry_function(func, max_attempts=10, delay=10):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except TRANSIENT_ERRORS as e:
                if attempt == max_attempts:
                    raise
                print(f"Intento {attempt}/{max_attempts} falló: {e}")
                sleep(delay)
            # Errores no transitorios se propagan inmediatamente
    return wrapper
```

**decorators.py — Agregar cap al backoff exponencial:**

```python
# utiles/decorators.py:66 — dentro de exp_retry_function
delay = min(2 ** attempt, 120)  # Cap en 2 minutos
```

**download.py — Eliminar doble decorador:**

```python
# cartolas/download.py:29-30
# Antes:
@exp_retry_function
@retry_function
def get_cartola_from_cmf(...):

# Después (un solo decorador con backoff):
@exp_retry_function
def get_cartola_from_cmf(...):
```

---

## 3. Circuit Breaker Pattern

**Resiliencia: 0/10 · Importancia: 6/10**

### Hallazgos

No existe implementación de circuit breaker en ningún módulo. El sistema reintenta indefinidamente (dentro de los límites de retry) sin detectar fallas sistémicas.

**Escenario de riesgo:** Si la CMF está caída, el sistema puede gastar ~68 minutos en reintentos antes de fallar. Si El Mercurio devuelve 429, no hay forma de pausar y reintentar más tarde.

### Remediación

Implementación mínima para servicios externos:

```python
# utiles/circuit_breaker.py (nuevo archivo)
import time
from dataclasses import dataclass, field

@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 5
    reset_timeout: int = 300  # 5 minutos
    _failures: int = field(default=0, init=False)
    _last_failure: float = field(default=0.0, init=False)
    _open: bool = field(default=False, init=False)

    def can_execute(self) -> bool:
        if not self._open:
            return True
        if time.time() - self._last_failure > self.reset_timeout:
            self._open = False
            self._failures = 0
            return True
        return False

    def record_failure(self):
        self._failures += 1
        self._last_failure = time.time()
        if self._failures >= self.failure_threshold:
            self._open = True
            print(f"Circuit breaker '{self.name}' ABIERTO tras {self._failures} fallas")

    def record_success(self):
        self._failures = 0
        self._open = False

# Uso en elmer.py:
# elmer_cb = CircuitBreaker("elmer", failure_threshold=3, reset_timeout=600)
# if not elmer_cb.can_execute():
#     return cached_data_or_empty()
```

---

## 4. Bulkhead Pattern

**Resiliencia: 0/10 · Importancia: 4/10**

### Hallazgos

No hay aislamiento de recursos:

- Sin thread pools ni `concurrent.futures`
- Sin connection pooling explícito en `requests`
- Sin semáforos para limitar operaciones concurrentes
- Sin límites de memoria/CPU en operaciones Polars

**Nota:** Para un pipeline single-user como Cartolas, el impacto es bajo. Se vuelve relevante si se escala a ejecución concurrente o servicio web.

### Remediación (baja prioridad)

```python
# Si se escala a concurrencia, usar requests.Session con pool:
import requests
from requests.adapters import HTTPAdapter

session = requests.Session()
adapter = HTTPAdapter(pool_connections=5, pool_maxsize=10)
session.mount("https://", adapter)
```

---

## 5. Graceful Degradation

**Resiliencia: 5/10 · Importancia: 8/10**

### Hallazgos positivos

| Ubicación | Patrón | Calidad |
|-----------|--------|---------|
| `comparador/elmer.py:222-238` | `last_elmer_data()` usa caché mensual | Bueno — evita descargas innecesarias |
| `eco/bcentral.py:206-227` | `update_bcch_parquet()` retorna datos existentes si están al día | Bueno — fallback a Parquet local |
| `eco/bcentral.py:211-214` | `FileNotFoundError` → fecha antigua para forzar descarga completa | Bueno — recuperación automática |
| `comparador/merge.py:77-78` | `.fill_null(1)` para tipo de cambio faltante | Aceptable — asume 1:1 como default |

### Hallazgos negativos

| Ubicación | Problema |
|-----------|----------|
| `cartolas/transform.py:48` | `strict=False` en `strptime` — fechas inválidas se convierten silenciosamente a null |
| `utiles/file_tools.py:120-134` | `obtener_archivo_mas_reciente()` retorna `None` sin intentar alternativas |
| `eco/bcentral.py:78,106,225` | Sin try/except en llamadas a bcchapi — si falla, el pipeline completo se cae |
| Variables `.env` | Sin validación al arranque — `KeyError` tardío si faltan |

### Remediación

**bcentral.py — Envolver llamadas API con fallback:**

```python
# eco/bcentral.py:225 — dentro de update_bcch_parquet
try:
    new_data = baja_datos_bcch(last_date, LAST_DATE)
except Exception as e:
    print(f"BCCH: Error al descargar datos nuevos: {e}")
    print("BCCH: Usando datos existentes del Parquet")
    return df  # Retorna datos cached en vez de crashear
```

**Validación de .env al arranque:**

```python
# cartolas/config.py o eco/bcentral.py — al inicio del módulo
import os
from dotenv import load_dotenv

load_dotenv()

_REQUIRED_ENV = ["BCCH_USER", "BCCH_PASS"]
_missing = [v for v in _REQUIRED_ENV if not os.getenv(v)]
if _missing:
    raise EnvironmentError(f"Variables de entorno faltantes: {', '.join(_missing)}")
```

---

## 6. Rate Limiting

**Resiliencia: 2/10 · Importancia: 7/10**

### Hallazgos

| Ubicación | Estado | Detalle |
|-----------|--------|---------|
| `cartolas/download.py:133-138` | `sleep(sleep_time)` con `sleep_time=1` | Rate limiting rudimentario — solo 1s entre lotes CMF |
| `comparador/elmer.py:154-159` | Loop sin `sleep()` | **SIN RATE LIMITING** — ráfaga de requests a El Mercurio |
| `eco/bcentral.py` | — | Sin rate limiting visible; depende de bcchapi |

### Remediación

**elmer.py — Agregar sleep entre requests (crítico):**

```python
# comparador/elmer.py:154-159
from time import sleep

for i in range(1, max_number):
    datos = get_elmer_data(i)
    if datos:
        all_data.extend(datos)
    sleep(0.5)  # 500ms entre requests para no saturar
```

**download.py — Incrementar sleep default:**

```python
# cartolas/download.py:123
def download_cartolas_range(input_date_range, sleep_time=3):  # 3s en vez de 1s
```

---

## 7. Error Handling General

**Resiliencia: 4/10 · Importancia: 7/10**

### Hallazgos

| Ubicación | Problema | Severidad |
|-----------|----------|-----------|
| `utiles/decorators.py:35,70` | `except Exception as e:` genérico en retry loops | Alta |
| `cartolas/download.py:106-120` | `except Exception as e:` + `raise e` (pierde stack trace) | Media |
| `utiles/file_tools.py:132-134,160-162` | `except Exception as e:` genérico | Media |
| `comparador/elmer.py:89` | `requests.get()` sin manejo de `ConnectionError`, `Timeout`, `HTTPError` | Alta |
| Todo el proyecto | `print()` en vez de `logging` | Media |

### Remediación

**download.py — Preservar stack trace:**

```python
# cartolas/download.py:120
# Antes:
raise e

# Después:
raise
```

**elmer.py — Manejo específico de errores HTTP:**

```python
# comparador/elmer.py:89-101
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    datos = response.json()
except requests.exceptions.Timeout:
    print(f"Timeout al obtener categoría {category_id}")
    return None
except requests.exceptions.ConnectionError:
    print(f"Error de conexión para categoría {category_id}")
    return None
except requests.exceptions.HTTPError as e:
    print(f"Error HTTP {e.response.status_code} para categoría {category_id}")
    return None
except json.JSONDecodeError:
    print(f"Respuesta JSON inválida para categoría {category_id}")
    return None
```

**Migrar a logging (recomendado):**

```python
# utiles/log.py (nuevo archivo)
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

# Uso:
# from utiles.log import get_logger
# logger = get_logger(__name__)
# logger.info("Descargando cartola...")
# logger.error(f"Fallo en descarga: {e}")
```

---

## Resumen de Hallazgos

| # | Categoría | Resiliencia | Importancia | Estado |
|---|-----------|:-----------:|:-----------:|--------|
| 1 | Timeout Handling | 3/10 | 8/10 | `requests.get()` sin timeout en elmer.py; BCCh sin timeout |
| 2 | Retry Logic | 5/10 | 7/10 | Existe pero con catch genérico y decoradores apilados |
| 3 | Circuit Breaker | 0/10 | 6/10 | Inexistente |
| 4 | Bulkhead Pattern | 0/10 | 4/10 | Inexistente (bajo impacto en pipeline single-user) |
| 5 | Graceful Degradation | 5/10 | 8/10 | Caché de El Mercurio y BCCh bueno; sin fallback en BCCh API |
| 6 | Rate Limiting | 2/10 | 7/10 | Solo 1s sleep en CMF; nada en El Mercurio |
| 7 | Error Handling | 4/10 | 7/10 | Catch genérico, sin logging estructurado, stack traces perdidos |

---

## Top 5 Acciones Prioritarias

1. **Agregar `timeout=30` a `requests.get()` en `comparador/elmer.py:89`** — Previene hang indefinido. 1 línea de cambio.
2. **Agregar `sleep(0.5)` entre requests en `comparador/elmer.py:154-159`** — Previene ban por rate limit. 1 línea.
3. **Eliminar doble decorador en `download.py:29-30`** — Reduce 120 reintentos potenciales a 12. 1 línea.
4. **Envolver llamadas BCCh con try/except + fallback a Parquet** — Previene crash del pipeline completo. ~5 líneas.
5. **Filtrar excepciones transitorias en retry decorators** — Evita reintentar errores permanentes (ValueError, etc). ~10 líneas.
