# Auditoría de Manejo de Errores — Cartolas

**Fecha:** 2026-03-16
**Alcance:** Todos los módulos Python del proyecto (`cartolas/`, `comparador/`, `eco/`, `utiles/`)

---

## Resumen ejecutivo

El proyecto tiene un manejo de errores funcional pero informal. Los puntos críticos de scraping CMF tienen reintentos robustos, pero las integraciones con BCCh y El Mercurio carecen de protección ante fallas de red. No se usa el módulo `logging` de Python — todo va a `print()`. Varios handlers genéricos `except Exception` ocultan errores específicos.

---

## Hallazgos

### 1. Sin módulo `logging` — todo usa `print()`

**Importancia: 7/10**

**Ubicaciones:** Todo el proyecto. Ejemplos:
- `utiles/decorators.py:37-38`
- `cartolas/download.py:117-118`
- `eco/bcentral.py:214,219,223-224`
- `comparador/elmer.py:98-100`
- `utiles/file_tools.py:133,161,197,200`
- `utiles/fechas.py:144`
- `cartolas/save.py:22`
- `cartolas/update.py:74-76,91,98`

**Problema:** `print()` no tiene niveles de severidad, no incluye timestamps, no se puede redirigir a archivo, y no permite filtrado. En un pipeline batch esto significa que errores críticos se pierden entre output informativo.

**Remediación:**

```python
# utiles/logging_config.py (nuevo archivo mínimo)
import logging

def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

# Uso en cada módulo:
import logging
logger = logging.getLogger(__name__)

# Reemplazar print() por:
logger.info("Archivo parquet grabado con éxito en %s", filename)
logger.error("Error en la descarga: %s", e)
logger.warning("BCCH: No hay datos nuevos del BCCh")
```

---

### 2. API BCCh sin manejo de errores de red ni reintentos

**Importancia: 8/10**

**Ubicación:** `eco/bcentral.py:78,80` — llamadas a `BCCh.cuadro()` sin try/except.
También: `eco/bcentral.py:106` — `baja_bcch_as_polars()` propaga excepciones sin atraparlas.

**Problema:** Si la API del BCCh tiene timeout, retorna un error HTTP, o las credenciales expiran, el programa entero crashea sin recuperación. Este es un servicio externo sobre el que no tenemos control.

**Qué ve el usuario:** Traceback completo de Python en la terminal.

**Estado del sistema:** Consistente (no se habían escrito datos aún), pero el pipeline se detiene.

**Remediación:**

```python
# eco/bcentral.py — envolver baja_datos_bcch con retry
from utiles.decorators import retry_function

@retry_function
def baja_datos_bcch(
    tickers=TICKERS, nombres=NOMBRES, bfill=True, last_date=LAST_DATE,
):
    if bfill:
        return BCCh.cuadro(series=tickers, nombres=nombres, hasta=last_date).ffill()
    else:
        return BCCh.cuadro(series=tickers, nombres=nombres, hasta=last_date)
```

---

### 3. API El Mercurio sin manejo de errores HTTP

**Importancia: 7/10**

**Ubicación:** `comparador/elmer.py:89` — `requests.get(url)` sin timeout ni manejo de excepciones de red.

**Problema:** Si el servidor no responde, `requests.get()` esperará indefinidamente (timeout por defecto = None). Errores HTTP 5xx no se detectan — se intenta parsear el body como JSON y el `JSONDecodeError` handler enmascara el problema real.

**Qué ve el usuario:** `None` silencioso para esa categoría — datos incompletos sin aviso claro.

**Remediación:**

```python
# comparador/elmer.py — get_elmer_data()
def get_elmer_data(category_id: int, verbose: bool = False) -> dict:
    url = ELMER_URL_BASE + str(category_id)
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()  # Lanza HTTPError si status >= 400
    except requests.RequestException as e:
        if verbose:
            print(f"Error HTTP al obtener categoría {category_id}: {e}")
        return None

    try:
        datos = response.json()
        datos["num_categoria"] = category_id
    except JSONDecodeError:
        if verbose:
            print(f"Error al parsear JSON de categoría {category_id}")
        return None

    return datos
```

---

### 4. Decoradores de retry lanzan `Exception` genérica

**Importancia: 6/10**

**Ubicación:** `utiles/decorators.py:40-42` y `utiles/decorators.py:77-79`

**Problema:** Tras agotar reintentos, se lanza `raise Exception(...)` en vez de re-lanzar la excepción original. Esto pierde el tipo de error y el traceback original, dificultando el diagnóstico.

```python
# Actual (decorators.py:40)
raise Exception(f"No se pudo ejecutar {func.__name__} después de {max_attempts} intentos")
```

**Remediación:**

```python
# utiles/decorators.py — retry_function
def wrapper(*args, **kwargs) -> T:
    attempts = 0
    last_exception = None
    while attempts < max_attempts:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            attempts += 1
            print(f"Error en {func.__name__}: {e}")
            print(f"Intento {attempts}/{max_attempts}. Esperando {delay} segundos")
            time.sleep(delay)
    raise last_exception  # Preserva tipo y traceback original

# Aplicar el mismo patrón en exp_retry_function (línea 77)
```

---

### 5. `except Exception` genéricos en utilidades que retornan `None`

**Importancia: 5/10**

**Ubicaciones:**
- `utiles/file_tools.py:132` — `obtener_archivo_mas_reciente()`
- `utiles/file_tools.py:160` — `obtener_fecha_creacion()`
- `utiles/file_tools.py:199` — `leer_json()` (catch-all después del JSONDecodeError)
- `utiles/fechas.py:143` — `es_mismo_mes()`

**Problema:** Estos handlers atrapan **cualquier** excepción (incluyendo `TypeError`, `PermissionError`, `MemoryError`) y retornan `None`/`False`. Los callers no distinguen entre "no hay archivo" y "error de permisos" o cualquier bug real.

**Ejemplo de flujo problemático:**
1. `obtener_archivo_mas_reciente()` falla por `PermissionError` → retorna `None`
2. `last_elmer_data()` interpreta `None` como "no hay archivo" → descarga datos nuevos
3. El error de permisos queda oculto

**Remediación:** Limitar a excepciones esperadas:

```python
# utiles/file_tools.py — obtener_archivo_mas_reciente()
except (OSError, ValueError) as e:
    print(f"Error al buscar archivo más reciente: {e}")
    return None

# utiles/file_tools.py — obtener_fecha_creacion()
except OSError as e:
    print(f"Error al obtener fecha de creación de {archivo.name}: {e}")
    return None

# utiles/fechas.py — es_mismo_mes()
except (ValueError, TypeError) as e:
    print(f"Error al comparar fechas: {e}")
    return False
```

---

### 6. Credenciales BCCh se cargan en tiempo de importación sin protección

**Importancia: 6/10**

**Ubicación:** `eco/bcentral.py:24-25` y `eco/bcentral.py:32`

```python
BCCH_PASS = env_variables["BCCH_PASS"]  # KeyError si no existe
BCCH_USER = env_variables["BCCH_USER"]  # KeyError si no existe
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)  # Crash si credenciales inválidas
```

**Problema:** Si `.env` no existe o no tiene las claves, cualquier `import eco.bcentral` crashea con `KeyError` sin mensaje claro. El login a la API también se ejecuta al importar — un fallo de red aquí mata todo el proceso.

**Qué ve el usuario:** `KeyError: 'BCCH_PASS'` sin contexto.

**Remediación:**

```python
# eco/bcentral.py — carga defensiva
env_variables = dotenv_values(".env")

BCCH_USER = env_variables.get("BCCH_USER")
BCCH_PASS = env_variables.get("BCCH_PASS")

if not BCCH_USER or not BCCH_PASS:
    raise EnvironmentError(
        "Faltan credenciales BCCH_USER y/o BCCH_PASS en el archivo .env"
    )

# Mover el login a una función lazy
_bcch_client = None

def get_bcch_client():
    global _bcch_client
    if _bcch_client is None:
        _bcch_client = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)
    return _bcch_client
```

---

### 7. Escritura de archivo Parquet sin protección

**Importancia: 5/10**

**Ubicaciones:**
- `cartolas/save.py:20` — `lazy_df.collect().write_parquet(filename)`
- `eco/bcentral.py:164` — `df.collect().write_parquet(path)`
- `eco/bcentral.py:226` — `df.collect().write_parquet(path)`

**Problema:** Si `write_parquet()` falla a mitad de escritura (disco lleno, permisos, interrupción), el archivo queda corrupto y la próxima lectura con `scan_parquet()` también fallará. Para el archivo principal (~750MB) esto es especialmente crítico.

**Remediación:** Escritura atómica con archivo temporal:

```python
# cartolas/save.py
from pathlib import Path
import tempfile

@timer
def save_lazyframe_to_parquet(
    lazy_df: pl.LazyFrame, filename: str | Path, unique: bool = True
) -> None:
    lazy_df = lazy_df.unique() if unique else lazy_df
    filename = Path(filename)

    # Escribir a archivo temporal en el mismo directorio
    with tempfile.NamedTemporaryFile(
        dir=filename.parent, suffix=".parquet.tmp", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        lazy_df.collect().write_parquet(tmp_path)
        tmp_path.rename(filename)  # Rename atómico en mismo filesystem
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    print(f"Archivo parquet grabado con éxito en {filename}")
```

---

### 8. Variable `df` no definida si `FileNotFoundError` en `update_bcch_parquet`

**Importancia: 8/10**

**Ubicación:** `eco/bcentral.py:206-220`

```python
try:
    df = load_bcch_from_parquet()
    last_date = get_last_date_from_parquet(df)
except FileNotFoundError:
    last_date = datetime(1970, 1, 1).date()
    print("BCCH: No se encontró el archivo de datos del BCCh")

if last_date >= LAST_DATE.date():
    print("BCCH: No hay datos nuevos del BCCh")
    return df  # ← NameError si vino del except: df nunca se definió
```

**Problema:** Si el archivo no existe Y `LAST_DATE.date()` resulta <= `1970-01-01` (imposible en la práctica, pero el patrón es un bug latente), se retorna `df` que no existe. Más importante: el flujo depende de un estado implícito — si `df` se definió o no.

**Remediación:**

```python
def update_bcch_parquet(path: str = PARQUET_PATH) -> pl.LazyFrame:
    try:
        df = load_bcch_from_parquet()
        last_date = get_last_date_from_parquet(df)
    except FileNotFoundError:
        last_date = datetime(1970, 1, 1).date()
        df = None
        print("BCCH: No se encontró el archivo de datos del BCCh")

    if last_date >= LAST_DATE.date() and df is not None:
        print("BCCH: No hay datos nuevos del BCCh")
        return df

    print(f"BCCH: Última fecha en el archivo: {last_date}")
    print("BCCH: Actualizando datos del BCCh")
    df = baja_bcch_as_polars(as_lazy=True)
    df.collect().write_parquet(path)
    return df
```

---

### 9. `download.py` — escritura de captcha sin try/except

**Importancia: 3/10**

**Ubicación:** `cartolas/download.py:69-70`

```python
with open(temp_file_path, "wb") as temp_file:
    temp_file.write(bytearray(image_data))
```

**Problema:** Si la escritura falla (permisos, disco), la excepción sube sin contexto al decorator de retry, que la atrapa como `Exception` genérica y reintenta la operación completa. Funciona pero el mensaje de error no indica que fue un problema de I/O local, no de red.

**Remediación:** Bajo riesgo en la práctica. Si se quisiera mejorar:

```python
try:
    with open(temp_file_path, "wb") as temp_file:
        temp_file.write(bytearray(image_data))
except OSError as e:
    raise OSError(f"No se pudo guardar captcha en {temp_file_path}: {e}") from e
```

---

### 10. `@wraps` faltante en decoradores de retry

**Importancia: 3/10**

**Ubicación:** `utiles/decorators.py:30` (`retry_function`) y `utiles/decorators.py:65` (`exp_retry_function`)

**Problema:** Las funciones `wrapper` no usan `@wraps(func)`, lo que hace que `func.__name__` y `func.__doc__` se pierdan. Irónicamente, los propios decoradores usan `func.__name__` en sus prints, lo cual funciona porque acceden al closure — pero herramientas de introspección y debugging verán `wrapper` en vez del nombre real.

**Nota:** `timer` sí usa `@wraps` correctamente (línea 108).

**Remediación:**

```python
# utiles/decorators.py
from functools import wraps

def retry_function(func, max_attempts=10, delay=10):
    @wraps(func)  # Agregar esto
    def wrapper(*args, **kwargs) -> T:
        ...
    return wrapper

def exp_retry_function(func, max_attempts=12):
    @wraps(func)  # Agregar esto
    def wrapper(*args, **kwargs) -> T:
        ...
    return wrapper
```

---

### 11. `verbose` inconsistente — errores silenciosos por defecto

**Importancia: 4/10**

**Ubicaciones:**
- `comparador/elmer.py:75` — `get_elmer_data(verbose=False)` — errores JSON silenciosos por defecto
- `cartolas/download.py:36` — `verbose=VERBOSE` (viene de config)

**Problema:** Con `verbose=False`, los errores de la API de El Mercurio se tragan silenciosamente. Si una categoría falla consistentemente, no hay forma de saberlo a menos que se active verbose manualmente.

**Remediación:** Los errores nunca deberían ser silenciosos. Usar `logging` resuelve esto: el nivel WARNING/ERROR siempre se muestra, independiente del flag verbose.

---

## Diagrama de flujo de errores

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  CMF Scrape  │     │  BCCh API     │     │  El Mercurio │
│  (Playwright)│     │  (bcchapi)    │     │  (requests)  │
└──────┬───────┘     └──────┬────────┘     └──────┬───────┘
       │                    │                     │
       ▼                    ▼                     ▼
  ┌─────────┐         Sin handler          JSONDecodeError
  │ except  │         de red/API           handler (solo)
  │Exception│         ────────┐            ──────┐
  │ + raise │                 │                  │
  └────┬────┘                 ▼                  ▼
       │              Crash con              Retorna None
       ▼              traceback              (silencioso)
  ┌──────────┐
  │@retry    │
  │@exp_retry│
  │(10×12    │
  │intentos) │
  └────┬─────┘
       │
       ▼ (si agota reintentos)
  raise Exception genérica
  (pierde tipo original)
       │
       ▼
  Crash del pipeline
  (sin recovery)
```

---

## Tabla resumen

| # | Hallazgo | Importancia | Módulo |
|---|----------|:-----------:|--------|
| 1 | `print()` en vez de `logging` | 7/10 | Todo el proyecto |
| 2 | BCCh API sin handler de red ni retry | 8/10 | `eco/bcentral.py` |
| 3 | El Mercurio sin timeout ni handler HTTP | 7/10 | `comparador/elmer.py` |
| 4 | Retry lanza `Exception` genérica | 6/10 | `utiles/decorators.py` |
| 5 | `except Exception` genéricos retornan `None` | 5/10 | `utiles/file_tools.py`, `utiles/fechas.py` |
| 6 | Credenciales BCCh se cargan al importar | 6/10 | `eco/bcentral.py` |
| 7 | Escritura Parquet no atómica | 5/10 | `cartolas/save.py`, `eco/bcentral.py` |
| 8 | Variable `df` no definida en rama except | 8/10 | `eco/bcentral.py` |
| 9 | Escritura captcha sin try/except | 3/10 | `cartolas/download.py` |
| 10 | `@wraps` faltante en retry decorators | 3/10 | `utiles/decorators.py` |
| 11 | Errores silenciosos con `verbose=False` | 4/10 | `comparador/elmer.py` |

---

## Priorización recomendada

1. **Inmediato** (8/10): Hallazgos #2 y #8 — bug latente en BCCh y falta de protección ante fallas de red
2. **Corto plazo** (6-7/10): Hallazgos #1, #3, #4, #6 — logging, protección HTTP, excepciones tipadas
3. **Cuando se pueda** (3-5/10): Hallazgos #5, #7, #9, #10, #11 — refinamientos de robustez
