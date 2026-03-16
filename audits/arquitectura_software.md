# Auditoría de Arquitectura de Software

**Proyecto:** Cartolas - Análisis de Fondos Mutuos Chilenos
**Fecha:** 2026-03-16
**Alcance:** Análisis de separación de responsabilidades, patrones arquitectónicos, anti-patrones, flujo de dependencias y modularidad.

---

## 1. Patrón Arquitectónico

El proyecto sigue una **arquitectura por capas (Layered Architecture)** orientada a pipeline de datos:

```
┌─────────────────────────────────────────────────────────┐
│  ENTRY POINTS (scripts top-level)                       │
│  cla_mensual.py, actualiza_parquet.py, soyfocus.py ...  │
├─────────────────────────────────────────────────────────┤
│  ANÁLISIS (comparador/)                                 │
│  cla_monthly.py, merge.py, tablas.py, elmer.py          │
├─────────────────────────────────────────────────────────┤
│  CORE (cartolas/)                                       │
│  download → transform → save → read → update            │
├─────────────────────────────────────────────────────────┤
│  INTEGRACIONES EXTERNAS (eco/)                          │
│  bcentral.py                                            │
├─────────────────────────────────────────────────────────┤
│  UTILIDADES (utiles/)                                   │
│  decorators.py, fechas.py, file_tools.py, listas.py     │
├─────────────────────────────────────────────────────────┤
│  ALMACENAMIENTO                                         │
│  Parquet, JSON (Elmer), TXT (CMF)                       │
└─────────────────────────────────────────────────────────┘
```

### Diagrama de dependencias entre módulos

```
cla_mensual.py ──┬──> comparador.cla_monthly ──> comparador.merge ──┬──> cartolas.read
                 │                                                   ├──> comparador.elmer ──> utiles.file_tools
                 │                                                   ├──> eco.bcentral
                 │                                                   └──> utiles.listas
                 ├──> cartolas.update_by_year ──> cartolas.download ──> utiles.decorators
                 │                               cartolas.transform    utiles.fechas
                 │                               cartolas.save
                 │                               cartolas.read
                 └──> eco.bcentral

cartolas.config <──── (casi todos los módulos)
utiles/*        <──── (casi todos los módulos)
```

### Flujo de datos

```
CMF (web) ──[Playwright]──> TXT ──[transform]──> LazyFrame ──[save]──> Parquet
                                                                          │
BCCh (API) ──[bcchapi]──> Pandas ──> Polars ──> Parquet                  │
                                                                          │
El Mercurio (HTTP) ──[requests]──> JSON (cache local)                    │
                                                                          │
                 ┌────────────────────────────────────────────────────────┘
                 v
         read (scan_parquet) ──> merge (join cartolas + elmer + bcch)
                                    │
                                    v
                            cla_monthly (análisis) ──> Excel (xlsxwriter)
```

---

## 2. Evaluación de Separación de Responsabilidades

| Aspecto | Estado | Nota |
|---------|--------|------|
| Download vs Transform vs Save | Bien separado | Cada fase es un módulo independiente |
| Configuración centralizada | Bien | `config.py` concentra rutas, esquemas, constantes |
| Análisis vs Pipeline | Bien | `comparador/` separado de `cartolas/` |
| Integraciones externas | Parcial | BCCh está en `eco/`, pero Elmer está en `comparador/` |
| Utilidades | Bien | Decoradores, fechas y archivos separados |

**Calificación de modularidad: 7/10**

**Justificación:** La separación del pipeline core (download → transform → save → read) es limpia y funcional. La capa de análisis (`comparador/`) encapsula correctamente la lógica de negocio CLA. Sin embargo, hay acoplamiento innecesario en algunos puntos (ver hallazgos), el módulo `cla_monthly.py` hace demasiado (650 líneas), y hay dependencias circulares parciales entre `config.py` y `file_tools.py`.

---

## 3. Hallazgos

### 3.1 Dependencia circular entre `config.py` y `file_tools.py`
**Importancia: 7/10**

`cartolas/config.py:55` importa `generate_hash_image_name` desde `utiles/file_tools.py`, y `utiles/file_tools.py:53` importa `CARTOLAS_FOLDER` desde `cartolas/config.py`. Ambos usan `# noqa: E402` para silenciar el linter.

```python
# cartolas/config.py:54-55
# El import es acá para evitar importaciones circulares con file_tools.py
from utiles.file_tools import generate_hash_image_name  # noqa: E402
```

```python
# utiles/file_tools.py:51-53
# Este import debe estar acá sino hay un error de importación circular
from cartolas.config import CARTOLAS_FOLDER  # noqa: E402
```

**Remediación:** Extraer la generación de hash a una función pura sin dependencias en un módulo separado (ej. `utiles/hash.py`), o mover `CARTOLAS_FOLDER` como parámetro por defecto en `clean_txt_folder` en vez de importarlo a nivel de módulo. Alternativa mínima:

```python
# utiles/file_tools.py — eliminar el import a nivel de módulo
# En clean_txt_folder, usar import local:
def clean_txt_folder(folder=None, ...):
    if folder is None:
        from cartolas.config import CARTOLAS_FOLDER
        folder = CARTOLAS_FOLDER
    ...
```

---

### 3.2 Módulo `cla_monthly.py` es un "God Module" (650 líneas)
**Importancia: 6/10**

`comparador/cla_monthly.py` concentra:
- Generación de fechas CLA (líneas 74-110)
- Cálculo de rentabilidades acumuladas (113-141)
- Cálculo de rentabilidades por período (194-229)
- Cálculo de rentabilidades SoyFocus (144-191)
- Estadísticas por categoría (232-284)
- Orquestación completa del pipeline CLA (288-463)
- Formato y escritura Excel con xlsxwriter (466-641)
- Constantes y configuración CLA (33-71)

**Remediación:** Extraer `write_hoja_10_salida` y toda la lógica de formato Excel a un módulo `comparador/excel_output.py`. Esto reduce `cla_monthly.py` a ~460 líneas y separa lógica de cálculo de lógica de presentación:

```python
# comparador/excel_output.py
from comparador.cla_monthly import SOYFOCUS_DEFAULTS

def write_hoja_10_salida(writer, df_stats, sheet_name="10 Salida", categorias=None):
    # ... mover las ~175 líneas de formato Excel aquí
```

---

### 3.3 `eco/bcentral.py` ejecuta side effects al importar
**Importancia: 8/10**

Al hacer `import eco.bcentral`, se ejecutan inmediatamente:

```python
# eco/bcentral.py:18
env_variables = dotenv_values(".env")

# eco/bcentral.py:24-25
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]

# eco/bcentral.py:32
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)  # Hace login a la API

# eco/bcentral.py:51
DATOS_JSON = read_bcentral_tickers()  # Lee archivo JSON del disco
```

Esto significa que **solo importar el módulo** hace login a la API del BCCh, lee `.env` y lee un JSON del disco. Si `.env` no tiene las credenciales, el import falla con `KeyError`.

**Remediación:** Diferir la inicialización usando lazy loading o una función factory:

```python
# eco/bcentral.py — inicialización lazy
_bcch_client = None

def get_bcch_client():
    global _bcch_client
    if _bcch_client is None:
        env_variables = dotenv_values(".env")
        _bcch_client = bcchapi.Siete(
            usr=env_variables["BCCH_USER"],
            pwd=env_variables["BCCH_PASS"]
        )
    return _bcch_client
```

---

### 3.4 `comparador/tablas.py` tiene fechas hardcodeadas
**Importancia: 8/10**

```python
# comparador/tablas.py:49-58
selected_dates = {
    "OM": max_date,
    "1M": date(2025, 2, 28),
    "3M": date(2024, 12, 31),
    "6M": date(2024, 9, 30),
    "1Y": date(2024, 3, 31),
    "3Y": date(2022, 3, 31),
    "5Y": date(2020, 3, 31),
    "YTD": date(2024, 12, 31),
}
```

Estas fechas están hardcodeadas en vez de calcularse dinámicamente. El código comentado (líneas 60-68) muestra que hubo intención de hacerlo dinámico.

**Remediación:** Usar las funciones de `utiles/fechas.py` que ya existen:

```python
from utiles.fechas import date_n_months_ago, date_n_years_ago, ultimo_dia_año_anterior

def filter_pivot_by_selected_dates(pivot_df: pl.DataFrame):
    max_date = pivot_df.select("FECHA_INF").max().to_series().to_list()[0]
    selected_dates = {
        "OM": max_date,
        "1M": date_n_months_ago(1, max_date),
        "3M": date_n_months_ago(3, max_date),
        "6M": date_n_months_ago(6, max_date),
        "1Y": date_n_years_ago(1, max_date),
        "3Y": date_n_years_ago(3, max_date),
        "5Y": date_n_years_ago(5, max_date),
        "YTD": ultimo_dia_año_anterior(max_date),
    }
    ...
```

---

### 3.5 Duplicación: `update.py` y `update_by_year.py` comparten ~70% de lógica
**Importancia: 5/10**

Ambos módulos tienen la misma estructura:
1. Leer parquet existente → obtener fechas únicas
2. Calcular fechas faltantes
3. Descargar cartolas
4. Transformar
5. Concatenar con datos existentes
6. Guardar deduplicado
7. Limpiar TXT

`update_by_year.py` es esencialmente `update.py` con un loop por año.

**Remediación:** Extraer la lógica común a una función reutilizable:

```python
# cartolas/update.py
def _update_single_parquet(parquet_file, missing_dates, sleep_time):
    """Lógica común: descarga, transforma, concatena y guarda."""
    download_cartolas_range(missing_dates, sleep_time)
    lazy_df_newdata = transform_cartola_folder(unique=True)
    if parquet_file.exists():
        existing = read_parquet_cartolas_lazy(parquet_path=parquet_file)
        df = pl.concat([existing, lazy_df_newdata])
    else:
        df = lazy_df_newdata
    save_lazyframe_to_parquet(lazy_df=df, filename=parquet_file)
```

---

### 3.6 Decoradores `retry_function` y `exp_retry_function` no funcionan como decoradores estándar
**Importancia: 6/10**

En `utiles/decorators.py`, `retry_function` y `exp_retry_function` no usan `@wraps(func)` ni aceptan llamadas con `@retry_function(max_attempts=5)`. La firma actual:

```python
# utiles/decorators.py:12-13
def retry_function(func: Callable[..., T], max_attempts: int = 10, delay: int = 10) -> Callable[..., T]:
```

Esto funciona como `@retry_function` (sin paréntesis), pero **no permite parametrización** como `@retry_function(max_attempts=5)`. Además, en `download.py:24` se usa `@retry_function` y en la línea 29-30 se apilan `@exp_retry_function` sobre `@retry_function`, lo que significa doble retry (hasta 10 × 12 = 120 intentos teóricos).

Tampoco preservan `__name__`, `__doc__`, etc. del original (falta `@wraps`).

**Remediación:**

```python
from functools import wraps

def retry_function(func=None, *, max_attempts=10, delay=10):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise
                    print(f"Error en {f.__name__}: {e}")
                    time.sleep(delay)
        return wrapper
    if func is not None:
        return decorator(func)
    return decorator
```

---

### 3.7 `elmer.py` genera constantes con side effects al importar
**Importancia: 5/10**

```python
# comparador/elmer.py:17-21
CURRENT_DATE = datetime.now().strftime("%Y-%m")
UPDATE_DATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
JSON_FILE_NAME = ELMER_FOLDER / f"{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
```

Estas "constantes" se calculan al importar el módulo. Si el módulo se importa a las 23:59 pero se usa a las 00:01, las fechas serán incorrectas. Además, `JSON_FILE_NAME` crea un nombre de archivo único por timestamp al momento de import, no al momento de guardar.

**Remediación:** Convertir a funciones:

```python
def _get_json_filename():
    return ELMER_FOLDER / f"{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
```

Y usarla como default en `save_elmer_data(filename=None)` con `filename = filename or _get_json_filename()`.

---

### 3.8 `merge.py` materializa dos veces sin necesidad
**Importancia: 4/10**

```python
# comparador/merge.py:353-357 (bloque __main__)
df = merge_cartolas_with_categories()
print(df.collect())  # Primera materialización
print(df.collect().columns)  # Segunda materialización (costosa)
df.collect().write_csv("cartolas.csv")  # Tercera materialización
```

Tres `.collect()` sobre el mismo LazyFrame ejecutan el query plan completo tres veces.

**Remediación:**
```python
result = df.collect()
print(result)
print(result.columns)
result.write_csv("cartolas.csv")
```

Nota: esto está solo en el bloque `__main__`, no en código de producción, así que el impacto real es bajo.

---

### 3.9 `config.py` calcula `FECHA_MAXIMA` y `TEMP_FILE_NAME` al importar
**Importancia: 5/10**

```python
# cartolas/config.py:67-68
DIAS_ATRAS = 1 if datetime.now().hour > 10 else 2
FECHA_MAXIMA = datetime.now().date() - timedelta(days=DIAS_ATRAS)

# cartolas/config.py:60-61
TEMP_FILE_NAME = generate_hash_image_name()
TEMP_FILE_PWD = TEMP_FOLDER / TEMP_FILE_NAME
```

- `FECHA_MAXIMA` depende de la hora de importación. Si el módulo se importa temprano y se ejecuta tarde, la fecha será incorrecta.
- `TEMP_FILE_NAME` genera un hash aleatorio al import, no al uso. Si se hacen múltiples descargas en la misma ejecución, comparten el mismo nombre temporal.

**Remediación:** Convertir `FECHA_MAXIMA` a función:

```python
def get_fecha_maxima():
    dias_atras = 1 if datetime.now().hour > 10 else 2
    return datetime.now().date() - timedelta(days=dias_atras)
```

---

### 3.10 `tablas.py` convierte a numpy cuando Polars puede hacer lo mismo
**Importancia: 3/10**

```python
# comparador/tablas.py:134
numeric_array = numeric_df.to_numpy()
mean_values = np.nanmean(numeric_array, axis=1)
max_values = np.nanmax(numeric_array, axis=1)
```

Esto rompe el paradigma Polars-first del proyecto y agrega una dependencia en numpy para algo que Polars maneja nativamente.

**Remediación:**
```python
# Usando Polars horizontal expressions
result_df = relative_returns.with_columns([
    pl.mean_horizontal(numeric_cols).alias("PROMEDIO_RENTABILIDAD"),
    pl.max_horizontal(numeric_cols).alias("MAX_RENTABILIDAD"),
    pl.min_horizontal(numeric_cols).alias("MIN_RENTABILIDAD"),
])
```

---

### 3.11 `elmer.py` no tiene retry ni timeout en requests
**Importancia: 6/10**

```python
# comparador/elmer.py:89
response = requests.get(url)
```

Sin timeout, sin retry. Si el servidor de El Mercurio no responde, el proceso se cuelga indefinidamente. El proyecto ya tiene decoradores de retry disponibles en `utiles/decorators.py`.

**Remediación:**
```python
response = requests.get(url, timeout=30)
```

Y opcionalmente aplicar `@retry_function` a `get_elmer_data`.

---

### 3.12 `cla_monthly.py` usa `map_elements` (anti-patrón en Polars)
**Importancia: 4/10**

```python
# comparador/cla_monthly.py:429-434
df_stats = df_stats.with_columns([
    pl.col("FECHA_INF")
    .map_elements(
        lambda x: periodo_labels.get(fecha_a_periodo.get(x, None), str(x)),
        return_dtype=pl.Utf8,
    )
    .alias("PERIODO")
])
```

`map_elements` ejecuta Python row-by-row, perdiendo la vectorización de Polars. Es el anti-patrón principal de rendimiento en Polars.

**Remediación:** Usar `replace` con un mapeo directo:

```python
# Crear el mapeo fecha → label
fecha_to_label = {v: periodo_labels.get(k, str(v)) for k, v in cla_dates.items()}
df_stats = df_stats.with_columns(
    pl.col("FECHA_INF").replace(fecha_to_label).alias("PERIODO")
)
```

---

### 3.13 Uso de `print()` en vez de `logging` en todo el proyecto
**Importancia: 4/10**

El proyecto usa `print()` para todos los mensajes de estado, errores y debugging. Ejemplo en `download.py:48`, `update.py:74-76`, `bcentral.py:219-224`, `elmer.py:98-101`. Esto hace imposible:
- Filtrar por nivel (debug, info, warning, error)
- Redirigir output a archivo
- Desactivar mensajes en producción

**Remediación:** Reemplazar `print()` con `logging` progresivamente. No es urgente pero mejora operabilidad.

---

### 3.14 `elmer.py` tiene return type incorrecto
**Importancia: 3/10**

```python
# comparador/elmer.py:241-242
def last_elmer_data_as_polars(
    elmerfolder: Path = ELMER_FOLDER, verbose: bool = True
) -> list[dict]:  # <-- return type dice list[dict] pero retorna pl.LazyFrame
    return pl.LazyFrame(last_elmer_data(elmerfolder=elmerfolder)).with_columns(...)
```

**Remediación:** Cambiar `-> list[dict]` a `-> pl.LazyFrame`.

---

### 3.15 Ruta hardcodeada en `soyfocus.py` bloque main
**Importancia: 2/10**

```python
# cartolas/soyfocus.py:420-421
df = pl.read_parquet(
    "/Users/franciscoerrandonea/code/cartolas/cartolas/data/parquet/soyfocus.parquet"
)
```

Ruta absoluta hardcodeada en el bloque `__main__`. Debería usar `SOYFOCUS_PARQUET_FILE_PATH` de config.

**Remediación:**
```python
df = pl.read_parquet(SOYFOCUS_PARQUET_FILE_PATH)
```

---

### 3.16 Email hardcodeado en `config.py`
**Importancia: 5/10**

```python
# cartolas/config.py:116-120
SENDER_MAIL, SENDER_NAME, TO_EMAILS = (
    "francisco@soyfocus.com",
    "Francisco",
    ["francisco@soyfocus.com"],
)
```

Credenciales/datos personales hardcodeados en código fuente en vez de `.env`.

**Remediación:** Mover a `.env`:
```python
SENDER_MAIL = env_variables.get("SENDER_MAIL", "")
```

---

## 4. Resumen de Hallazgos por Importancia

| # | Hallazgo | Importancia | Categoría |
|---|----------|-------------|-----------|
| 3.3 | `bcentral.py` hace login a API al importar | 8/10 | Side effect en import |
| 3.4 | Fechas hardcodeadas en `tablas.py` | 8/10 | Código frágil |
| 3.1 | Dependencia circular `config.py` ↔ `file_tools.py` | 7/10 | Acoplamiento |
| 3.2 | `cla_monthly.py` God Module (650 líneas) | 6/10 | Separación de responsabilidades |
| 3.6 | Decoradores sin `@wraps` ni parametrización | 6/10 | API incorrecta |
| 3.11 | `requests.get` sin timeout en `elmer.py` | 6/10 | Resiliencia |
| 3.5 | Duplicación entre `update.py` y `update_by_year.py` | 5/10 | DRY |
| 3.7 | Constantes con `datetime.now()` al importar en `elmer.py` | 5/10 | Side effect en import |
| 3.9 | `FECHA_MAXIMA` calculada al importar | 5/10 | Side effect en import |
| 3.16 | Email hardcodeado en config.py | 5/10 | Seguridad |
| 3.12 | `map_elements` en vez de operación vectorizada | 4/10 | Rendimiento |
| 3.13 | `print()` en vez de `logging` | 4/10 | Operabilidad |
| 3.8 | Triple `.collect()` en merge.py main | 4/10 | Rendimiento |
| 3.10 | numpy en vez de Polars horizontal ops | 3/10 | Consistencia |
| 3.14 | Return type incorrecto en `last_elmer_data_as_polars` | 3/10 | Type hints |
| 3.15 | Ruta absoluta hardcodeada en soyfocus.py main | 2/10 | Mantenibilidad |

---

## 5. Diagrama de Cuellos de Botella

```
                    ┌─────────────────────┐
                    │   CMF (Playwright)   │ ← Cuello de botella #1:
                    │   30 días máx/req    │   Scraping secuencial con captcha
                    │   + captcha + retry  │   Exponential backoff hasta 2^12 seg
                    └─────────┬───────────┘
                              │
                    ┌─────────v───────────┐
                    │   Transform (CSV)    │ ← OK: Polars lazy, eficiente
                    └─────────┬───────────┘
                              │
                    ┌─────────v───────────┐
                    │   Save (Parquet)     │ ← Cuello de botella #2:
                    │   .unique().collect()│   unique() sobre ~750MB fuerza
                    └─────────┬───────────┘   materialización completa
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                   │
  ┌────────v────────┐ ┌──────v──────┐ ┌──────────v─────────┐
  │  BCCh API       │ │ Elmer HTTP  │ │  Read (scan_parquet)│
  │  (login al      │ │ (sin timeout│ │  OK: lazy scan      │
  │   importar)     │ │  ni retry)  │ │                     │
  └────────┬────────┘ └──────┬──────┘ └──────────┬──────────┘
           │                 │                    │
           └────────┬────────┘                    │
                    │                             │
           ┌────────v─────────────────────────────v──┐
           │          merge (join LazyFrames)         │ ← OK: lazy
           └────────────────────┬─────────────────────┘
                                │
           ┌────────────────────v─────────────────────┐
           │          cla_monthly (.collect() + joins) │ ← Cuello de botella #3:
           │          Paso 4: df_cat.collect()         │   Materialización temprana
           │          Luego joins sobre DataFrames     │   en línea 402
           └────────────────────┬─────────────────────┘
                                │
           ┌────────────────────v─────────────────────┐
           │          Excel output (xlsxwriter)        │ ← OK: escritura secuencial
           └──────────────────────────────────────────┘
```

---

## 6. Fortalezas del Proyecto

1. **Pipeline lazy consistente**: El uso de `pl.LazyFrame` en todo el pipeline core es correcto y eficiente.
2. **Separación download/transform/save/read**: Cada fase es independiente y reutilizable.
3. **Configuración centralizada**: `config.py` evita hardcoding de rutas y esquemas.
4. **Actualizaciones incrementales**: Solo descarga fechas faltantes, no reprocesa todo.
5. **Paradigma funcional**: Funciones puras que reciben y retornan LazyFrames.
6. **Validación de custom_mapping**: `_validate_custom_mapping` en `merge.py` es robusto.
7. **Retry con backoff exponencial**: Manejo correcto de la fragilidad del scraping CMF.
