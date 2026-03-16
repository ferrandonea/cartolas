# Auditoría de Manejo de Errores - Cartolas

**Fecha:** 2026-03-16
**Alcance:** Todo el codebase Python (`cartolas/`, `comparador/`, `eco/`, `utiles/`, scripts raíz)

---

## Resumen Ejecutivo

El proyecto carece de un framework centralizado de manejo de errores. No existen excepciones custom, no se usa el módulo `logging` de Python, y la mayoría de los errores se capturan con `except Exception as e` genérico + `print()`. Los mecanismos de retry en `utiles/decorators.py` son el punto más robusto, pero tienen limitaciones de configurabilidad y tipado.

---

## 1. Ausencia de Manejador Centralizado de Errores

**Importancia: 7/10**

**Hallazgo:** No existe un manejador global de excepciones, ni una función o módulo centralizado para procesar errores. Cada módulo maneja sus errores de forma independiente e inconsistente.

**Ubicaciones afectadas:** Todo el codebase.

**Remediación:** Crear un módulo `utiles/exceptions.py` con excepciones de dominio:

```python
# utiles/exceptions.py

class CartolasError(Exception):
    """Excepción base del proyecto."""
    pass

class DownloadError(CartolasError):
    """Error en descarga de datos (CMF, Elmer, BCCh)."""
    pass

class TransformError(CartolasError):
    """Error en transformación de datos."""
    pass

class ValidationError(CartolasError):
    """Error de validación de datos o parámetros."""
    pass

class ExternalAPIError(CartolasError):
    """Error en llamada a API externa."""
    pass
```

---

## 2. Uso Exclusivo de `print()` en Lugar de `logging`

**Importancia: 8/10**

**Hallazgo:** El proyecto usa `print()` para todos los mensajes de error, info y debug. No se importa ni configura el módulo `logging` en ningún archivo. Esto impide:
- Filtrar por nivel de severidad
- Rotar logs
- Enviar errores a servicios externos
- Distinguir errores de mensajes informativos

**Ubicaciones afectadas (todos los `print` de error):**
- `utiles/decorators.py:37-38` y `72-74` — errores de retry
- `utiles/file_tools.py:133`, `161`, `187`, `197`, `200` — errores de archivos
- `utiles/fechas.py:144` — error de comparación de fechas
- `cartolas/download.py:117-118` — error de descarga
- `comparador/elmer.py:98-100` — error de API
- `eco/bcentral.py:214` — archivo no encontrado

**Remediación:** Configurar logging a nivel de proyecto:

```python
# utiles/logging_config.py
import logging

def setup_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

# En cada módulo, reemplazar print por:
logger = logging.getLogger(__name__)
logger.error(f"Error en {func.__name__}: {e}")
```

---

## 3. Catch-all `except Exception as e` Genérico

**Importancia: 6/10**

**Hallazgo:** Se encontraron **7 instancias** de `except Exception as e` que capturan todo tipo de excepción indiscriminadamente. Esto enmascara bugs reales (e.g., `KeyboardInterrupt`, `MemoryError`, `SystemExit` en Python < 3 — aunque en Python 3 `Exception` no captura `KeyboardInterrupt`/`SystemExit`, sí captura errores inesperados que deberían propagarse).

| Archivo | Línea | Contexto |
|---------|-------|----------|
| `utiles/decorators.py` | 35 | `retry_function` — captura todo para reintentar |
| `utiles/decorators.py` | 70 | `exp_retry_function` — captura todo para reintentar |
| `utiles/file_tools.py` | 132 | `obtener_archivo_mas_reciente` — retorna `None` |
| `utiles/file_tools.py` | 160 | `obtener_fecha_creacion` — retorna `None` |
| `utiles/file_tools.py` | 199 | `leer_json` fallback — retorna `None` |
| `utiles/fechas.py` | 143 | `es_mismo_mes` — retorna `False` |
| `cartolas/download.py` | 116 | `fetch_cartola_data` — re-raise |

**Remediación (ejemplo para `file_tools.py:132`):**

```python
# Antes:
except Exception as e:
    print(f"Error al buscar archivo más reciente: {e}")
    return None

# Después:
except (OSError, PermissionError) as e:
    logger.warning(f"Error al buscar archivo más reciente en {directorio}: {e}")
    return None
```

---

## 4. Decoradores de Retry Lanzan `Exception` Genérica

**Importancia: 5/10**

**Hallazgo:** Ambos decoradores (`retry_function` y `exp_retry_function`) lanzan `Exception` genérica cuando se agotan los reintentos (líneas 40-42 y 77-79). Esto dificulta que el código llamador distinga entre un fallo de retry y otro error.

**Ubicación:** `utiles/decorators.py:40-42` y `77-79`

**Remediación:**

```python
# Antes (línea 40):
raise Exception(
    f"No se pudo ejecutar {func.__name__} después de {max_attempts} intentos"
)

# Después:
raise MaxRetriesExceededError(
    f"No se pudo ejecutar {func.__name__} después de {max_attempts} intentos",
    last_exception=e  # preservar la última excepción
) from e
```

Además, los decoradores no preservan metadata de la función decorada (`@wraps` falta en `retry_function` y `exp_retry_function`, pero sí está en `timer`):

```python
from functools import wraps

def retry_function(func, max_attempts=10, delay=10):
    @wraps(func)  # <-- falta esto
    def wrapper(*args, **kwargs):
        ...
```

---

## 5. Credenciales BCCh Sin Manejo de Error en Carga

**Importancia: 9/10**

**Hallazgo:** En `eco/bcentral.py:24-25`, las credenciales se acceden directamente del diccionario sin validar su existencia. Si `.env` no existe o no tiene las claves, se produce un `KeyError` críptico a nivel de módulo (al importar).

**Ubicación:** `eco/bcentral.py:18-25`

```python
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]  # KeyError si no existe
BCCH_USER = env_variables["BCCH_USER"]  # KeyError si no existe
```

Además, `BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)` se ejecuta al importar el módulo (línea 32), lo que significa que **cualquier import de `eco.bcentral` falla si las credenciales no están**.

**Remediación:**

```python
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables.get("BCCH_PASS")
BCCH_USER = env_variables.get("BCCH_USER")

if not BCCH_PASS or not BCCH_USER:
    raise EnvironmentError(
        "Faltan credenciales BCCH_USER y/o BCCH_PASS en el archivo .env"
    )
```

---

## 6. Llamada HTTP sin Manejo de Errores de Red

**Importancia: 8/10**

**Hallazgo:** En `comparador/elmer.py:89`, `requests.get(url)` se ejecuta sin timeout, sin manejo de `ConnectionError`, `Timeout`, ni verificación de status code. Si El Mercurio está caído, el proceso se cuelga indefinidamente.

**Ubicación:** `comparador/elmer.py:87-101`

```python
response = requests.get(url)  # Sin timeout, sin manejo de errores HTTP
try:
    datos = response.json()
```

**Remediación:**

```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    datos = response.json()
    datos["num_categoria"] = category_id
except (requests.ConnectionError, requests.Timeout) as e:
    logger.warning(f"Error de red al consultar categoría {category_id}: {e}")
    return None
except requests.HTTPError as e:
    logger.warning(f"HTTP {response.status_code} para categoría {category_id}")
    return None
except JSONDecodeError:
    logger.warning(f"JSON inválido para categoría {category_id}")
    return None
```

---

## 7. Variable No Definida en `update_bcch_parquet` (Bug)

**Importancia: 9/10**

**Hallazgo:** En `eco/bcentral.py:206-227`, si `FileNotFoundError` es capturada en línea 211, la variable `df` nunca se asigna. Sin embargo, en la línea 220, se retorna `df` si `last_date >= LAST_DATE.date()`. Si el archivo no existe Y la fecha cumple la condición (imposible en la práctica con 1970, pero es un bug latente), se produciría un `UnboundLocalError`.

Más grave: si `last_date` de 1970 no cumple la condición (lo normal), se ejecuta el `else` y funciona. Pero si la API del BCCh falla en la línea 225 (`baja_bcch_as_polars`), no hay manejo de ese error.

**Ubicación:** `eco/bcentral.py:206-227`

**Remediación:**

```python
def update_bcch_parquet(path: str = PARQUET_PATH) -> pl.LazyFrame:
    df = None
    try:
        df = load_bcch_from_parquet()
        last_date = get_last_date_from_parquet(df)
    except FileNotFoundError:
        last_date = datetime(1970, 1, 1).date()
        logger.info("BCCH: No se encontró el archivo, se descargará completo")

    if df is not None and last_date >= LAST_DATE.date():
        logger.info("BCCH: No hay datos nuevos del BCCh")
        return df

    logger.info(f"BCCH: Actualizando datos desde {last_date}")
    df = baja_bcch_as_polars(as_lazy=True)
    df.collect().write_parquet(path)
    return df
```

---

## 8. Ausencia de Bloques `finally` para Limpieza de Recursos

**Importancia: 6/10**

**Hallazgo:** No se encontró ningún bloque `finally` en todo el codebase. Aunque Playwright usa `with sync_playwright()` (context manager) en `download.py:51`, si ocurre un error antes de entrar al `with` o en la función `fetch_cartola_data`, archivos temporales pueden quedar sin limpiar.

**Ubicaciones relevantes:**
- `cartolas/download.py:69-70` — archivo temporal se crea pero si falla antes de `rename`, queda huérfano
- `cartolas/save.py:20` — si `write_parquet` falla a mitad de escritura, archivo parcial queda

**Remediación (para `download.py`):**

```python
def get_cartola_from_cmf(...):
    ...
    try:
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(bytearray(image_data))
        # ... resto del proceso
    finally:
        if temp_file_path.exists():
            temp_file_path.unlink()
```

---

## 9. `transform_cartola_folder` Falla Silenciosamente con Carpeta Vacía

**Importancia: 5/10**

**Hallazgo:** En `cartolas/transform.py:80-91`, si `cartola_folder.glob(wildcard)` no encuentra archivos, `list_txts` es una lista vacía y `pl.concat([])` lanza un error de Polars sin contexto útil.

**Ubicación:** `cartolas/transform.py:80-86`

**Remediación:**

```python
list_txts = [txt_file for txt_file in cartola_folder.glob(wildcard)]
if not list_txts:
    raise FileNotFoundError(
        f"No se encontraron archivos '{wildcard}' en {cartola_folder}"
    )
```

---

## 10. `last_elmer_data` Puede Retornar `None` Sin Señal al Llamador

**Importancia: 6/10**

**Hallazgo:** En `comparador/elmer.py:230-234`, `leer_json(last_archivo)` puede retornar `None` (si el JSON está corrupto). Este `None` se retorna directamente y luego se pasa a `pl.LazyFrame(None)` en `last_elmer_data_as_polars` (línea 244), lo que provocaría un error opaco de Polars.

**Ubicación:** `comparador/elmer.py:234` y `244`

**Remediación:**

```python
# En last_elmer_data, después de leer_json:
datos = leer_json(last_archivo)
if datos is None:
    logger.warning(f"EMOL: Archivo {last_archivo} corrupto, descargando nuevo")
    return get_and_save_elmer_data()
return datos
```

---

## 11. `read_bcentral_tickers` Sin Manejo de Errores

**Importancia: 4/10**

**Hallazgo:** `eco/bcentral.py:46-47` usa `open()` y `json.load()` sin `try/except`. Si el archivo JSON no existe o está corrupto, el error se propaga a nivel de módulo (se ejecuta en línea 51 al importar).

**Ubicación:** `eco/bcentral.py:35-47` (ejecutado en línea 51)

**Remediación:**

```python
def read_bcentral_tickers(path: Path = JSON_PATH):
    if not path.exists():
        raise FileNotFoundError(f"Archivo de tickers BCCh no encontrado: {path}")
    with open(path, "r") as f:
        return json.load(f)
```

---

## 12. Ejecución de Código al Importar Módulos

**Importancia: 7/10**

**Hallazgo:** `eco/bcentral.py` ejecuta código significativo a nivel de módulo al ser importado:
- Línea 18: Carga `.env`
- Línea 24-25: Accede a credenciales
- Línea 32: Hace login a la API del BCCh
- Línea 51: Lee archivo JSON de tickers

Si cualquiera de estos pasos falla, **todo `import` del módulo falla**, lo que impide incluso ejecutar tests o inspeccionar código.

**Ubicación:** `eco/bcentral.py:18-55`

**Remediación:** Convertir a inicialización lazy:

```python
_bcch_client = None

def get_bcch_client():
    global _bcch_client
    if _bcch_client is None:
        env_variables = dotenv_values(".env")
        user = env_variables.get("BCCH_USER")
        passwd = env_variables.get("BCCH_PASS")
        if not user or not passwd:
            raise EnvironmentError("Credenciales BCCh no configuradas en .env")
        _bcch_client = bcchapi.Siete(usr=user, pwd=passwd)
    return _bcch_client
```

---

## 13. `download_cartolas_range` Sin Manejo de Errores Parciales

**Importancia: 5/10**

**Hallazgo:** En `cartolas/download.py:123-141`, si un rango de fechas falla durante la descarga, toda la función se interrumpe y los rangos restantes no se procesan. No hay registro de qué rangos se completaron exitosamente.

**Ubicación:** `cartolas/download.py:133-138`

**Remediación:**

```python
errores = []
for i, (start_date, end_date) in enumerate(date_range_set):
    try:
        get_cartola_from_cmf(start_date, end_date, verbose=True)
    except Exception as e:
        logger.error(f"Fallo en rango {start_date}-{end_date}: {e}")
        errores.append((start_date, end_date, str(e)))
    sleep(sleep_time)

if errores:
    logger.warning(f"{len(errores)} rangos fallaron: {errores}")
```

---

## Tabla Resumen

| # | Hallazgo | Importancia | Archivo(s) Principal(es) |
|---|----------|:-----------:|--------------------------|
| 1 | Sin manejador centralizado de errores | 7/10 | Todo el codebase |
| 2 | `print()` en lugar de `logging` | 8/10 | Todo el codebase |
| 3 | Catch-all `except Exception` genérico | 6/10 | `decorators.py`, `file_tools.py`, `fechas.py`, `download.py` |
| 4 | Decoradores lanzan `Exception` genérica | 5/10 | `utiles/decorators.py:40,77` |
| 5 | Credenciales BCCh sin validación | 9/10 | `eco/bcentral.py:24-25` |
| 6 | HTTP sin timeout ni manejo de errores de red | 8/10 | `comparador/elmer.py:89` |
| 7 | Variable `df` potencialmente no definida (bug) | 9/10 | `eco/bcentral.py:206-227` |
| 8 | Sin bloques `finally` para limpieza | 6/10 | `cartolas/download.py`, `cartolas/save.py` |
| 9 | `transform_cartola_folder` falla con carpeta vacía | 5/10 | `cartolas/transform.py:80-86` |
| 10 | `last_elmer_data` puede retornar `None` silenciosamente | 6/10 | `comparador/elmer.py:234,244` |
| 11 | `read_bcentral_tickers` sin manejo de errores | 4/10 | `eco/bcentral.py:46-47` |
| 12 | Ejecución de código al importar módulos | 7/10 | `eco/bcentral.py:18-55` |
| 13 | Sin manejo de errores parciales en descarga | 5/10 | `cartolas/download.py:133-138` |

---

## Estadísticas del Codebase

| Métrica | Valor |
|---------|-------|
| Total bloques `try/except` | 10 |
| Excepciones custom definidas | 0 |
| Sentencias `raise` | 9 |
| Tipos de excepción únicos usados | 3 (`Exception`, `ValueError`, `FileNotFoundError`) |
| Catch-all `except Exception` | 7 |
| Uso de `logging` | 0 |
| Bloques `finally` | 0 |
| Código async | 0 |
| Mecanismos de retry | 2 decoradores (`retry_function`, `exp_retry_function`) |

---

## Prioridades de Remediación

1. **Inmediato (9/10):** Hallazgos #5 y #7 — bugs reales que pueden causar crashes
2. **Alta (8/10):** Hallazgos #2 y #6 — sin logging y sin timeout en HTTP
3. **Media (6-7/10):** Hallazgos #1, #3, #8, #10, #12 — mejoras estructurales
4. **Baja (4-5/10):** Hallazgos #4, #9, #11, #13 — mejoras incrementales
