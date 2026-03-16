# Auditoría de Principios SOLID

**Fecha**: 2026-03-16
**Calificación general**: 4/10

---

## S — Principio de Responsabilidad Única (SRP)

**Calificación: 5/10**

### Hallazgo S1: `download.py` mezcla scraping, captcha, browser y I/O de archivos

**Importancia: 6/10**

`get_cartola_from_cmf()` (línea 31) hace todo en una sola función:
- Lanza Playwright y controla el browser
- Descarga y predice captchas (`captchapass.predict`)
- Llena formularios HTML
- Guarda archivos a disco (renombrando imágenes a `error_folder` o `correct_folder`)

**Remediación:**

```python
# Extraer la resolución de captcha a su propia función
def solve_captcha(page: Page, temp_file_path: Path) -> str:
    captcha_img = page.query_selector("img#captcha_img")
    src = captcha_img.get_attribute("src")
    image_data = page.evaluate("""...""", src)
    with open(temp_file_path, "wb") as f:
        f.write(bytearray(image_data))
    prediction = predict(temp_file_path)
    if len(prediction) != 6:
        raise ValueError("El captcha no tiene 6 caracteres")
    return prediction

# Extraer el llenado del formulario
def fill_cmf_form(page: Page, start_date: str, end_date: str, captcha: str):
    page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
    page.evaluate(f"document.querySelector('#txt_termino').value = '{end_date}';")
    page.get_by_label("Ingrese los caracteres de la").fill(captcha)
```

---

### Hallazgo S2: `merge.py` mezcla carga de datos, lógica de negocio y llamadas a APIs externas

**Importancia: 7/10**

`prepare_cartolas_in_pesos()` (línea 43) en un solo flujo:
1. Lee Parquet (`read_parquet_cartolas_lazy`)
2. Llama a la API del BCCh (`update_bcch_for_cartolas()`) — línea 70
3. Hace joins y cálculos financieros complejos (líneas 74-164)

No se puede testear la lógica de cálculos sin descargar datos reales.

**Remediación:**

```python
# Separar la obtención de datos de la transformación
def prepare_cartolas_in_pesos(
    cartola_df: pl.LazyFrame,  # inyectar en vez de leer internamente
    eco_df: pl.LazyFrame,      # inyectar en vez de llamar API
) -> pl.LazyFrame:
    merged_df = cartola_df.join(eco_df, on=["MONEDA", "FECHA_INF"], how="left")
    # ... cálculos financieros ...
    return merged_df
```

---

### Hallazgo S3: `cla_monthly.py` mezcla cálculos financieros con formato Excel

**Importancia: 6/10**

`write_hoja_10_salida()` (línea 466, 175 líneas) es una función monolítica que:
- Define 11 formatos de celda Excel (líneas 487-543)
- Itera categorías y períodos
- Escribe datos celda por celda con lógica de formateo condicional (verde/rojo)

`generate_cla_data()` (línea 288, 175 líneas) orquesta 9 pasos que mezclan lógica de negocio con persistencia Excel.

**Remediación:**

Separar el formateo Excel en su propio módulo:

```python
# comparador/excel_formatter.py
def create_excel_formats(workbook):
    return {
        "azul": workbook.add_format({...}),
        "porcentaje_verde": workbook.add_format({...}),
        ...
    }

def write_category_block(worksheet, formats, row, cat_data, periodos):
    # ... lógica de escritura ...
    return row + 7  # filas escritas
```

---

### Hallazgo S4: `elmer.py` mezcla HTTP, transformación y persistencia JSON

**Importancia: 4/10**

El módulo tiene funciones separadas (`get_elmer_data`, `filter_elmer_data`, `save_elmer_data`), lo cual es razonable. Sin embargo, `last_elmer_data()` (línea 205) combina lógica de cache (verificar si el archivo es del mes actual) con obtención de datos.

---

## O — Principio Abierto/Cerrado (OCP)

**Calificación: 3/10**

### Hallazgo O1: Fechas hardcodeadas en `tablas.py:49-58` — BUG ACTIVO

**Importancia: 10/10**

```python
# tablas.py:49-58
selected_dates = {
    "OM": max_date,
    "1M": date(2025, 2, 28),   # HARDCODED
    "3M": date(2024, 12, 31),  # HARDCODED
    "6M": date(2024, 9, 30),   # HARDCODED
    "1Y": date(2024, 3, 31),   # HARDCODED
    "3Y": date(2022, 3, 31),   # HARDCODED
    "5Y": date(2020, 3, 31),   # HARDCODED
    "YTD": date(2024, 12, 31), # HARDCODED
}
```

Esto es un bug: las fechas están congeladas. El código comentado (líneas 60-68) tiene la versión correcta usando funciones dinámicas. Además, las funciones necesarias ya existen en `utiles/fechas.py`.

**Remediación:**

```python
# tablas.py — Descomentar y usar las funciones de fechas.py
from utiles.fechas import last_day_n_months_ago, last_day_n_months_ago_by_year

selected_dates = {
    "OM": max_date,
    "1M": last_day_n_months_ago(max_date, 1),
    "3M": last_day_n_months_ago(max_date, 3),
    "6M": last_day_n_months_ago(max_date, 6),
    "1Y": last_day_n_months_ago_by_year(max_date, 1),
    "3Y": last_day_n_months_ago_by_year(max_date, 3),
    "5Y": last_day_n_months_ago_by_year(max_date, 5),
    "YTD": ultimo_dia_año_anterior(max_date),
}
```

---

### Hallazgo O2: No hay abstracciones para fuentes de datos externas

**Importancia: 7/10**

Cada integración está hardcodeada en su módulo:
- `bcentral.py`: llama directamente a `bcchapi.Siete` (línea 32)
- `elmer.py`: llama directamente a `requests.get()` (línea 89)
- `download.py`: instancia `sync_playwright()` directamente (línea 51)

Agregar una nueva fuente de datos requiere modificar código existente.

**Remediación:**

Usar Protocol (typing) para definir contratos:

```python
# cartolas/protocols.py
from typing import Protocol
import polars as pl

class EconomicDataSource(Protocol):
    def fetch(self, tickers: list[str]) -> pl.LazyFrame: ...

class FundCategorySource(Protocol):
    def get_categories(self) -> pl.LazyFrame: ...
```

---

### Hallazgo O3: Periodos y categorías hardcodeados sin extensibilidad

**Importancia: 5/10**

En `cla_monthly.py:34-38`:
```python
MESES_CLA = [1, 3, 6]
AÑOS_CLA = [1, 3, 5]
CATEGORIAS_CLA = ["CONSERVADOR", "MODERADO", "AGRESIVO"]
```

Y en `merge.py:257-262`:
```python
categories_mapping = {
    "BALANCEADO CONSERVADOR": 9810,
    "BALANCEADO MODERADO": 9809,
    "BALANCEADO AGRESIVO": 9811,
    "DEUDA CORTO PLAZO NACIONAL": 9810,
}
```

Agregar una categoría o período requiere modificar múltiples archivos.

**Remediación:**

Centralizar en `config.py` o un archivo de configuración externo (YAML/JSON):

```python
# config.py
CLA_PERIODS = {"months": [1, 3, 6], "years": [1, 3, 5]}
CATEGORY_FUND_MAPPING = {
    "BALANCEADO CONSERVADOR": 9810,
    "BALANCEADO MODERADO": 9809,
    "BALANCEADO AGRESIVO": 9811,
}
```

---

## L — Principio de Sustitución de Liskov (LSP)

**Calificación: N/A**

El codebase no usa herencia ni clases. Todo son funciones a nivel de módulo y constantes globales. LSP no aplica.

---

## I — Principio de Segregación de Interfaces (ISP)

**Calificación: 5/10**

### Hallazgo I1: `generate_cla_data()` tiene demasiados parámetros opcionales

**Importancia: 5/10**

`cla_monthly.py:288`:
```python
def generate_cla_data(
    input_date: date = date.today(),
    categories: list[str] = CATEGORIAS_ELMER,
    relevant_columns: list[str] = RELEVANT_COLUMNS,
    save_xlsx: bool = False,
    xlsx_name: str = "cla_data.xlsx",
    excel_steps: EXCEL_STEPS = "minimal",
    custom_mapping: dict[int, int] | None = None,
) -> pl.DataFrame:
```

7 parámetros que mezclan lógica de negocio (`input_date`, `categories`, `custom_mapping`) con presentación (`save_xlsx`, `xlsx_name`, `excel_steps`).

**Remediación:**

Separar en dos funciones:

```python
def generate_cla_data(
    input_date: date = date.today(),
    categories: list[str] = CATEGORIAS_ELMER,
    custom_mapping: dict[int, int] | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Retorna (df_with_stats, df_stats)"""
    ...

def export_cla_to_excel(
    df_stats: pl.DataFrame,
    xlsx_name: str = "cla_data.xlsx",
    excel_steps: EXCEL_STEPS = "minimal",
):
    """Exporta resultados CLA a Excel"""
    ...
```

---

### Hallazgo I2: Funciones que aceptan tanto `DataFrame` como `LazyFrame` implícitamente

**Importancia: 4/10**

En `tablas.py`, múltiples funciones hacen `isinstance` check:
```python
# tablas.py:22, 87, 124
if isinstance(df, pl.LazyFrame):
    df = df.collect()
```

Esto indica que la interfaz no es clara: el caller no sabe si debe pasar DataFrame o LazyFrame.

**Remediación:**

Definir tipos explícitos y ser consistente. Si la función necesita DataFrame, exigirlo:

```python
def create_returns_pivot_table(
    df: pl.DataFrame,  # no LazyFrame
    pivot_values: str = "RENTABILIDAD_ACUMULADA"
) -> pl.DataFrame:
    # Eliminar el isinstance check
    ...
```

---

## D — Principio de Inversión de Dependencias (DIP)

**Calificación: 2/10**

### Hallazgo D1: Cliente BCCh instanciado globalmente al importar el módulo

**Importancia: 9/10**

`bcentral.py:32`:
```python
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)
```

Este objeto se crea al hacer `import eco.bcentral`, lo que significa:
- Requiere credenciales válidas en `.env` solo para importar el módulo
- No se puede testear sin conexión real
- No se puede inyectar un mock

**Remediación:**

```python
# bcentral.py — Lazy initialization
_bcch_client = None

def get_bcch_client() -> bcchapi.Siete:
    global _bcch_client
    if _bcch_client is None:
        _bcch_client = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)
    return _bcch_client

def baja_datos_bcch(
    tickers=TICKERS,
    nombres=NOMBRES,
    bfill=True,
    last_date=LAST_DATE,
    client: bcchapi.Siete | None = None,  # inyección opcional
):
    client = client or get_bcch_client()
    if bfill:
        return client.cuadro(series=tickers, nombres=nombres, hasta=last_date).ffill()
    return client.cuadro(series=tickers, nombres=nombres, hasta=last_date)
```

---

### Hallazgo D2: Timestamp global en `elmer.py` hace el módulo no-determinístico

**Importancia: 7/10**

`elmer.py:17-21`:
```python
CURRENT_DATE = datetime.now().strftime("%Y-%m")
UPDATE_DATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
JSON_FILE_NAME = ELMER_FOLDER / f"{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
```

El nombre del archivo JSON se genera al importar. Cada import produce un nombre distinto.

**Remediación:**

```python
# Generar el nombre al momento de guardar, no al importar
def _generate_json_filename() -> Path:
    return ELMER_FOLDER / f"{datetime.now().strftime('%Y%m%d%H%M%S')}.json"

def save_elmer_data(lista_fondos: list, filename: Path | None = None):
    filename = filename or _generate_json_filename()
    with open(filename, "w") as f:
        json.dump(lista_fondos, f)
```

---

### Hallazgo D3: `DIAS_ATRAS` evaluado al importar `config.py`

**Importancia: 6/10**

`config.py:67`:
```python
DIAS_ATRAS = 1 if datetime.now().hour > 10 else 2
FECHA_MAXIMA = datetime.now().date() - timedelta(days=DIAS_ATRAS)
```

Si `config.py` se importa a las 09:00, `DIAS_ATRAS=2`. Si se usa a las 15:00, sigue siendo 2. Resultado incorrecto.

**Remediación:**

```python
# config.py — Convertir a función
def get_dias_atras() -> int:
    return 1 if datetime.now().hour > 10 else 2

def get_fecha_maxima() -> date:
    return datetime.now().date() - timedelta(days=get_dias_atras())
```

---

### Hallazgo D4: Sin inyección de dependencias en cadena `merge → bcentral → elmer`

**Importancia: 8/10**

Cadena de dependencias concretas:
```
cla_monthly.py:350  → merge_cartolas_with_categories()
  merge.py:342      → prepare_cartolas_in_pesos()
    merge.py:70     → update_bcch_for_cartolas()  [API BCCh]
  merge.py:341      → prepare_relevant_categories()
    merge.py:267    → last_elmer_data_as_polars()  [API Elmer + JSON]
```

No hay ningún punto donde inyectar datos de prueba. Cada función llama directamente a la siguiente.

**Remediación:**

Pasar los DataFrames como parámetros opcionales:

```python
# merge.py
def merge_cartolas_with_categories(
    cartola_df: pl.LazyFrame | None = None,
    elmer_df: pl.LazyFrame | None = None,
    custom_mapping: dict[int, int] | None = None,
) -> pl.LazyFrame:
    if elmer_df is None:
        elmer_df = prepare_relevant_categories(custom_mapping=custom_mapping)
    if cartola_df is None:
        cartola_df = prepare_cartolas_in_pesos()
    # ... join logic ...
```

---

### Hallazgo D5: Import circular en `config.py`

**Importancia: 5/10**

`config.py:54-55`:
```python
# El import es acá para evitar importaciones circulares con file_tools.py
from utiles.file_tools import generate_hash_image_name  # noqa: E402
```

Un módulo de configuración no debería tener dependencias de módulos utilitarios que a su vez importan la configuración.

**Remediación:**

Mover `TEMP_FILE_NAME` fuera de `config.py`, o hacer que `generate_hash_image_name()` no dependa de `config`:

```python
# config.py — Generar el nombre in-situ sin importar file_tools
import hashlib, uuid
TEMP_FILE_NAME = hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12] + ".png"
TEMP_FILE_PWD = TEMP_FOLDER / TEMP_FILE_NAME
```

---

## Resumen

| Principio | Nota | Hallazgos Críticos |
|-----------|------|--------------------|
| **S** — Responsabilidad Única | 5/10 | `merge.py`, `download.py` y `cla_monthly.py` mezclan múltiples responsabilidades |
| **O** — Abierto/Cerrado | 3/10 | Fechas hardcodeadas (bug activo), sin abstracciones para extensibilidad |
| **L** — Sustitución de Liskov | N/A | No hay herencia en el codebase |
| **I** — Segregación de Interfaces | 5/10 | Funciones con demasiados parámetros, tipos de entrada ambiguos |
| **D** — Inversión de Dependencias | 2/10 | Estado global al importar, cero inyección de dependencias, imposible testear |

### Prioridad de remediación

1. **D1**: Lazy init del cliente BCCh (elimina side-effect al importar)
2. **O1**: Descomentar fechas dinámicas en `tablas.py` (bug activo)
3. **D3**: Convertir `DIAS_ATRAS`/`FECHA_MAXIMA` a funciones
4. **D2**: Generar nombre JSON al guardar, no al importar
5. **D4**: Inyectar DataFrames como parámetros opcionales en `merge.py`
6. **S2**: Separar obtención de datos de transformación en `merge.py`
7. **S3**: Extraer formateo Excel a su propio módulo
8. **O2**: Definir Protocols para fuentes de datos
