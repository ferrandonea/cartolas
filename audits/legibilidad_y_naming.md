# Auditoría de Legibilidad y Convenciones de Naming

**Fecha**: 2026-03-16
**Archivos analizados**: 31 archivos Python
**Paquetes**: `cartolas/`, `comparador/`, `eco/`, `utiles/`, scripts raíz

---

## 1. Convenciones de Naming

### 1.1 Mezcla español/inglés en nombres de funciones — Importancia: 8/10

El proyecto mezcla español e inglés sin criterio uniforme. Dentro del mismo módulo coexisten funciones en ambos idiomas.

| Archivo | Español | Inglés |
|---------|---------|--------|
| `utiles/fechas.py` | `es_mismo_mes()` :110, `ultimo_dia_año_anterior()` :204, `ultimo_dia_mes_anterior()` :230 | `date_range()` :40, `consecutive_date_ranges()` :64, `from_date_to_datetime()` :8 |
| `utiles/file_tools.py` | `obtener_archivo_mas_reciente()` :104, `obtener_fecha_creacion()` :137, `leer_json()` :165 | `generate_hash_name()` :18, `clean_txt_folder()` :56 |
| `eco/bcentral.py` | `baja_datos_bcch()` :58, `baja_bcch_as_polars()` :83, `baja_dolar_observado_as_polars()` :118 | `save_bcch_as_parquet()` :154, `update_bcch_parquet()` :196, `load_bcch_from_parquet()` :167 |

**Remediación**: Estandarizar a inglés (convención estándar en data science). Ejemplo para `utiles/fechas.py`:

```python
# Antes
def es_mismo_mes(fecha: Union[datetime, str]) -> bool:
def ultimo_dia_año_anterior(base_date: date = None) -> date:
def ultimo_dia_mes_anterior(base_date: date = None) -> date:

# Después
def is_same_month(fecha: Union[datetime, str]) -> bool:
def last_day_previous_year(base_date: date = None) -> date:
def last_day_previous_month(base_date: date = None) -> date:
```

Para `utiles/file_tools.py`:

```python
# Antes
def obtener_archivo_mas_reciente(directorio: Path) -> Optional[Path]:
def obtener_fecha_creacion(archivo: Path) -> Optional[datetime]:
def leer_json(ruta_archivo: Union[str, Path]) -> Optional[dict[str, Any]]:

# Después
def get_most_recent_file(directory: Path) -> Optional[Path]:
def get_creation_date(file_path: Path) -> Optional[datetime]:
def read_json(file_path: Union[str, Path]) -> Optional[dict[str, Any]]:
```

Para `eco/bcentral.py`:

```python
# Antes
def baja_datos_bcch(...)
def baja_bcch_as_polars(...)
def baja_dolar_observado_as_polars(...)

# Después
def download_bcch_data(...)
def download_bcch_as_polars(...)
def download_usd_as_polars(...)
```

---

### 1.2 Mezcla español/inglés en constantes — Importancia: 6/10

| Archivo | Español | Inglés |
|---------|---------|--------|
| `cartolas/config.py` | `COLUMNAS_BOOLEAN` :72, `COLUMNAS_NULL` :73, `FECHA_MINIMA` :64, `FECHA_MAXIMA` :68 | `DEFAULT_HEADLESS` :12, `SORTING_ORDER` :74, `TIMEOUT` :17 |
| `comparador/merge.py` | `COLUMNAS_RELEVANTES` :13, `COLUMNAS_GASTOS` :33, `COLUMNAS_COMISIONES` :34, `SUMA_GASTOS` :38 | `MAX_YEARS` :11, `MIN_DATE` :12 |

**Remediación**: Para constantes, el español es más aceptable porque los nombres de columnas vienen de la CMF en español. Sin embargo, las constantes de configuración (no-columnas) deberían ser inglés:

```python
# config.py — solo las de configuración
FECHA_MINIMA → MIN_DATE  # (ya existe MIN_DATE en merge.py)
FECHA_MAXIMA → MAX_DATE
DIAS_ATRAS → DAYS_BACK
```

---

### 1.3 Parámetro `sorted` sombrea built-in de Python — Importancia: 7/10

**Ubicación**: `cartolas/read.py:8`, `cartolas/soyfocus.py:28`

```python
# Antes (read.py:8)
def read_parquet_cartolas_lazy(
    parquet_path: str | Path, sorted: bool = True
) -> pl.LazyFrame:

# Después
def read_parquet_cartolas_lazy(
    parquet_path: str | Path, pre_sorted: bool = True
) -> pl.LazyFrame:
```

```python
# Antes (soyfocus.py:28)
def create_soyfocus_parquet(
    ..., sorted: bool = True, ...

# Después
def create_soyfocus_parquet(
    ..., pre_sorted: bool = True, ...
```

---

### 1.4 Funciones duplicadas con nombres inconsistentes — Importancia: 7/10

**Ubicación**: `cartolas/fund_identifica.py`

`cmf_to_pl()` (:31) y `cmf_text_to_df()` (:65) hacen esencialmente lo mismo: convertir texto CSV de la CMF a un DataFrame de Polars. Además, `cmf_to_pl()` no retorna nada (solo hace `print(df.schema)`).

```python
# cmf_to_pl() no retorna nada — es dead code efectivo
def cmf_to_pl(cmf_text: str):  # :31 — sin return type, sin return statement útil
    ...
    print(df.schema)  # :62 — solo imprime, no retorna

def cmf_text_to_df(text: str) -> pl.DataFrame:  # :65 — la versión completa
```

**Remediación**: Eliminar `cmf_to_pl()` y conservar solo `cmf_text_to_df()`.

---

### 1.5 Docstring del módulo con typo — Importancia: 3/10

**Ubicación**: `cartolas/fund_identifica.py:1`

```python
# Antes
"""Baja la identifiación de fondos mutuos desde la CMF"""

# Después
"""Descarga la identificación de fondos mutuos desde la CMF"""
```

---

## 2. Consistencia de Naming

### 2.1 Patrón inconsistente en nombres de parámetros — Importancia: 5/10

`eco/bcentral.py:58-63`: Los type hints de `tickers` y `nombres` dicen `str` pero reciben `list`:

```python
# Antes
def baja_datos_bcch(
    tickers: str = TICKERS,   # TICKERS es list
    nombres: str = NOMBRES,   # NOMBRES es list
    ...

# Después
def baja_datos_bcch(
    tickers: list[str] = TICKERS,
    nombres: list[str] = NOMBRES,
    ...
```

Lo mismo en `baja_bcch_as_polars()` (:83-89).

---

### 2.2 Terminología de dominio inconsistente — Importancia: 4/10

El verbo "bajar/baja" (descargar) se usa en español en `eco/bcentral.py` pero en inglés (`download`) en `cartolas/download.py`. Los docstrings también mezclan:

- `fund_identifica.py:1` — "Baja la identifiación..."
- `download.py:1` — "Esto son modulos para bajar una cartola..."
- `download.py:105` — "Es la función que hace la baja de la cartola"
- `bcentral.py:58` — `baja_datos_bcch`

**Remediación**: Unificar al inglés `download_*` en nombres de funciones.

---

## 3. Legibilidad del Código

### 3.1 Patrón `print(...) if verbose else None` — Importancia: 6/10

**Ubicación**: `cartolas/download.py:47-49`, `:74`, `:114`, `:117-118`

```python
# Antes
print(f"Descargando cartolas desde {start_date} hasta {end_date}") if verbose else None

# Después — más legible
if verbose:
    print(f"Descargando cartolas desde {start_date} hasta {end_date}")
```

El patrón ternario para side effects es un antipatrón: genera `None` innecesariamente y es menos legible que un `if` simple. Aparece 5 veces en `download.py`.

---

### 3.2 Fechas hardcodeadas (magic values) — Importancia: 8/10

**Ubicación**: `comparador/tablas.py:49-58`

```python
selected_dates = {
    "OM": max_date,
    "1M": date(2025, 2, 28),   # hardcoded
    "3M": date(2024, 12, 31),  # hardcoded
    "6M": date(2024, 9, 30),   # hardcoded
    "1Y": date(2024, 3, 31),   # hardcoded
    "3Y": date(2022, 3, 31),   # hardcoded
    "5Y": date(2020, 3, 31),   # hardcoded
    "YTD": date(2024, 12, 31), # hardcoded
}
```

Hay código comentado (:60-68) que calcula las fechas dinámicamente. Las fechas hardcodeadas quedarán obsoletas.

**Remediación**: Usar las funciones de `utiles/fechas.py`:

```python
from utiles.fechas import date_n_months_ago, date_n_years_ago, ultimo_dia_mes_anterior, ultimo_dia_año_anterior

selected_dates = {
    "OM": max_date,
    "1M": ultimo_dia_mes_anterior(max_date),
    "3M": date_n_months_ago(3, max_date),
    "6M": date_n_months_ago(6, max_date),
    "1Y": date_n_years_ago(1, max_date),
    "3Y": date_n_years_ago(3, max_date),
    "5Y": date_n_years_ago(5, max_date),
    "YTD": ultimo_dia_año_anterior(max_date),
}
```

---

### 3.3 Número mágico `29` — Importancia: 4/10

**Ubicación**: `utiles/fechas.py:65`

```python
def consecutive_date_ranges(
    date_list: list[date], max_days: int = 29
) -> list[tuple[date, date]]:
```

El `29` es el límite de la CMF (30 días máximo por descarga, -1 para margen). Está documentado en el docstring (:72) pero no como constante.

**Remediación**:

```python
# En config.py
CMF_MAX_DOWNLOAD_DAYS = 29  # CMF permite máximo 30 días, se usa 29 por margen

# En fechas.py
from cartolas.config import CMF_MAX_DOWNLOAD_DAYS

def consecutive_date_ranges(
    date_list: list[date], max_days: int = CMF_MAX_DOWNLOAD_DAYS
) -> list[tuple[date, date]]:
```

---

### 3.4 Número mágico `6` en predicción de captcha — Importancia: 3/10

**Ubicación**: `cartolas/download.py:76`

```python
if len(prediction) != 6:
```

**Remediación**:

```python
CAPTCHA_LENGTH = 6

if len(prediction) != CAPTCHA_LENGTH:
```

---

### 3.5 Comentarios que repiten el código — Importancia: 5/10

**Ubicación**: Múltiples archivos, especialmente `eco/bcentral.py`

```python
# eco/bcentral.py — ejemplos de comentarios redundantes
env_variables = dotenv_values(".env")  # Cargamos variables de entorno desde .env      ← :18
LAST_DATE = datetime.now() - timedelta(days=1)  # :21, el nombre ya lo dice
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)  # Inicializamos la API del BCCh   ← :32
DATOS_JSON = read_bcentral_tickers()  # Diccionario con metadatos de series             ← :51

# utiles/fechas.py:173-176 — 3 comentarios para 3 líneas de código autoexplicativo
n_months_ago = base_date - relativedelta(months=n)  # Restar n meses usando relativedelta
return n_months_ago  # Retornar la fecha resultante
```

**Remediación**: Eliminar comentarios que solo repiten lo que el código ya dice. Mantener solo los que explican el *porqué*.

---

### 3.6 `download_fund_identification()` con variable muerta — Importancia: 4/10

**Ubicación**: `cartolas/fund_identifica.py:127-155`

```python
def download_fund_identification() -> str:  # :123 — dice que retorna str pero retorna DataFrame
    text_cmf = get_fund_identification()
    df = cmf_text_to_df(text_cmf)
    columnas = {  # :127-139 — este dict se define pero NUNCA se usa
        "RUN_ADM": pl.UInt32,
        ...
    }
    df.columns = [...]  # :141-153 — reasigna columnas que ya tienen esos nombres (cmf_text_to_df ya los pone)
    return df
```

**Remediación**:

```python
def download_fund_identification() -> pl.DataFrame:
    text_cmf = get_fund_identification()
    return cmf_text_to_df(text_cmf)
```

---

## 4. Firmas de Funciones

### 4.1 `get_cartola_from_cmf` — 9 parámetros — Importancia: 6/10

**Ubicación**: `cartolas/download.py:31-41`

```python
def get_cartola_from_cmf(
    start_date, end_date, headless, url, verbose,
    temp_file_path, error_folder, correct_folder, cartolas_txt_folder
):
```

7 de 9 parámetros tienen defaults de `config.py`. Solo `start_date` y `end_date` son necesarios. El problema es que luego pasa 7 de estos a `fetch_cartola_data()` (:85-93) individualmente.

**Remediación**: Agrupar paths en un dataclass o usar directamente las constantes de config en `fetch_cartola_data`:

```python
def fetch_cartola_data(page: Page, prediction: str, verbose: bool = VERBOSE):
    """Usa las constantes de config directamente en vez de recibirlas como parámetros."""
    ...
```

---

### 4.2 `fetch_cartola_data` sin type hints — Importancia: 5/10

**Ubicación**: `cartolas/download.py:96-104`

```python
def fetch_cartola_data(
    verbose,            # sin type hint
    temp_file_path,     # sin type hint
    error_folder,       # sin type hint
    correct_folder,     # sin type hint
    cartolas_txt_folder,# sin type hint
    page,               # sin type hint
    prediction,         # sin type hint
):
```

**Remediación**:

```python
def fetch_cartola_data(
    verbose: bool,
    temp_file_path: Path,
    error_folder: Path,
    correct_folder: Path,
    cartolas_txt_folder: Path,
    page: Page,
    prediction: str,
) -> None:
```

---

### 4.3 Decoradores `retry` sin `@wraps` — Importancia: 5/10

**Ubicación**: `utiles/decorators.py:30`, `:65`

`retry_function` y `exp_retry_function` no usan `@wraps(func)` en sus wrappers, a diferencia de `timer` (:108) que sí lo hace. Esto causa que `func.__name__` se pierda para debugging.

**Remediación**:

```python
def retry_function(func, max_attempts=10, delay=10):
    @wraps(func)  # agregar
    def wrapper(*args, **kwargs) -> T:
        ...

def exp_retry_function(func, max_attempts=12):
    @wraps(func)  # agregar
    def wrapper(*args, **kwargs) -> T:
        ...
```

---

### 4.4 Doble decorador retry en `get_cartola_from_cmf` — Importancia: 4/10

**Ubicación**: `cartolas/download.py:29-30`

```python
@exp_retry_function
@retry_function
def get_cartola_from_cmf(...):
```

Esto aplica `retry_function` (10 intentos, delay fijo 10s) y encima `exp_retry_function` (12 intentos, delay exponencial). En el peor caso: 12 * 10 = **120 intentos**. Probablemente excesivo.

**Remediación**: Usar solo uno de los dos, o crear un decorador combinado con backoff exponencial y límite razonable.

---

## 5. Expresiones Booleanas Complejas

### 5.1 Ninguna expresión booleana excesivamente compleja encontrada — Importancia: N/A

El código mantiene las condiciones simples. No se detectaron ternarios anidados ni expresiones booleanas difíciles de leer (excepto el patrón `print() if verbose else None` ya mencionado).

---

## 6. Resumen de Hallazgos

| # | Hallazgo | Importancia | Ubicación principal |
|---|----------|:-----------:|---------------------|
| 1.1 | Mezcla español/inglés en funciones | 8/10 | `utiles/fechas.py`, `utiles/file_tools.py`, `eco/bcentral.py` |
| 1.2 | Mezcla español/inglés en constantes | 6/10 | `cartolas/config.py`, `comparador/merge.py` |
| 1.3 | Parámetro `sorted` sombrea built-in | 7/10 | `cartolas/read.py:8`, `cartolas/soyfocus.py:28` |
| 1.4 | Funciones duplicadas (`cmf_to_pl` / `cmf_text_to_df`) | 7/10 | `cartolas/fund_identifica.py` |
| 1.5 | Typo en docstring | 3/10 | `cartolas/fund_identifica.py:1` |
| 2.1 | Type hints incorrectos (`str` en vez de `list`) | 5/10 | `eco/bcentral.py:58-63, 83-89` |
| 2.2 | Terminología "baja" vs "download" | 4/10 | `eco/bcentral.py`, `cartolas/download.py` |
| 3.1 | Antipatrón `print() if x else None` | 6/10 | `cartolas/download.py` (5 ocurrencias) |
| 3.2 | Fechas hardcodeadas | 8/10 | `comparador/tablas.py:49-58` |
| 3.3 | Número mágico `29` | 4/10 | `utiles/fechas.py:65` |
| 3.4 | Número mágico `6` (captcha) | 3/10 | `cartolas/download.py:76` |
| 3.5 | Comentarios redundantes | 5/10 | `eco/bcentral.py`, `utiles/fechas.py` |
| 3.6 | Variable muerta + return type incorrecto | 4/10 | `cartolas/fund_identifica.py:123-155` |
| 4.1 | Función con 9 parámetros | 6/10 | `cartolas/download.py:31-41` |
| 4.2 | `fetch_cartola_data` sin type hints | 5/10 | `cartolas/download.py:96-104` |
| 4.3 | Decoradores retry sin `@wraps` | 5/10 | `utiles/decorators.py:30, 65` |
| 4.4 | Doble decorador retry (120 intentos posibles) | 4/10 | `cartolas/download.py:29-30` |

---

## 7. Aspectos Positivos

- **Constantes UPPER_SNAKE_CASE**: Consistente en todo el proyecto.
- **Funciones snake_case**: Sin excepciones.
- **Docstrings**: Cobertura ~85%, con Args/Returns bien documentados.
- **Paradigma funcional**: Bien aplicado, sin clases innecesarias.
- **Type hints en funciones principales**: Buena cobertura en `comparador/` y `cartolas/`.
- **Nombres de columnas calculadas**: `PATRIMONIO_AJUSTADO`, `GASTOS_TOTALES_PESOS`, etc. — descriptivos y consistentes con el dominio CMF.
- **`_validate_custom_mapping()`**: Uso correcto del prefijo `_` para función privada (`comparador/merge.py:168`).
