# Auditoria de Testing - Proyecto Cartolas

**Fecha**: 2026-03-16
**Estado actual**: El proyecto no tiene infraestructura de testing formal (0% cobertura)

---

## Resumen Ejecutivo

El proyecto Cartolas procesa datos financieros criticos (fondos mutuos chilenos) con **cero tests formales**. No existe pytest, ni archivos `test_*.py`, ni CI/CD. La unica "validacion" son bloques `if __name__ == "__main__"` en algunos modulos para ejecucion manual.

---

## 1. COBERTURA DE TESTS

### 1.1 Unit Tests
**Cobertura: 0%** | **Importancia: 10/10**

No existen unit tests para ninguna funcion del proyecto.

**Funciones criticas sin tests:**

| Modulo | Funcion | Riesgo |
|--------|---------|--------|
| `cartolas/transform.py` | `transform_single_cartola()` | Transformacion CSV→LazyFrame sin validacion de columnas |
| `cartolas/save.py` | `save_lazyframe_to_parquet()` | Escritura sin manejo de errores de disco |
| `utiles/fechas.py` | `date_range()`, `consecutive_date_ranges()` | Logica de fechas con edge cases (bisiesto, limites de mes) |
| `utiles/decorators.py` | `@retry_function`, `@exp_retry_function` | Logica de reintentos que traga excepciones |
| `cartolas/polars_utils.py` | `map_s_n_to_bool()`, `replace_null_with_one()` | Transformaciones de datos |
| `comparador/cla_monthly.py` | `add_cumulative_returns()`, `add_period_returns()` | Calculos financieros con division por cero posible |

**Remediacion:**

```toml
# pyproject.toml - agregar dependencias de test
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
    "polars>=1.16.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

```python
# tests/conftest.py
import pytest
import polars as pl
from pathlib import Path

@pytest.fixture
def sample_cartola_csv(tmp_path):
    """CSV minimo con formato CMF."""
    content = "RUN_FM;SERIE;FECHA_INF;VALOR_CUOTA;MONEDA;NOM_ADM;REMUNERACION;COMISION_FIJA;COMISION_VARIABLE;GASTOS_DE_OPERACION;OTROS_GASTOS_OPER;OTROS_GASTOS_NO_OPER;IMPUESTOS;DERECHO_REGISTRO;TOTAL_PARTICIPES;TOTAL_CUOTAS;PATRIMONIO_NETO;APV;FONDO_INVERSION;SERIE_ACTIVA\n9809;A;01/03/2026;1500.50;PESOS;ADM1;0.1;0.2;0.0;0.05;0.0;0.0;0.0;0.0;100;50000;75025000;S;N;S"
    csv_file = tmp_path / "ffmm_test.txt"
    csv_file.write_text(content)
    return csv_file

@pytest.fixture
def sample_schema():
    """Schema minimo para tests."""
    from cartolas.config import SCHEMA
    return SCHEMA

@pytest.fixture
def empty_folder(tmp_path):
    """Carpeta vacia para tests de transform_cartola_folder."""
    folder = tmp_path / "empty"
    folder.mkdir()
    return folder
```

### 1.2 Integration Tests
**Cobertura: 0%** | **Importancia: 9/10**

No existen tests de integracion para los flujos:
- Descarga CMF → Transformacion → Guardado Parquet
- Lectura Parquet → Merge con BCCh → Merge con Elmer → Reporte CLA
- Actualizacion BCCh (API → Parquet)

### 1.3 Tests E2E
**Cobertura: 0%** | **Importancia: 7/10**

No existen tests end-to-end que validen el flujo completo de `actualiza_parquet.py` o `cla_mensual.py`.

### 1.4 Rutas Criticas Sin Cobertura
**Importancia: 10/10**

1. **`eco/bcentral.py:220`** - Bug: `df` indefinido si `FileNotFoundError` capturado y `last_date < LAST_DATE`:
```python
# eco/bcentral.py - BUG ACTUAL
try:
    df = load_bcch_from_parquet()
    last_date = get_last_date_from_parquet(df)
except FileNotFoundError:
    last_date = datetime(1970, 1, 1).date()
    # df NO SE DEFINE AQUI

if last_date >= LAST_DATE.date():
    return df  # NameError si vino del except!
```

2. **`comparador/cla_monthly.py`** - Division por cero en `add_period_returns()` cuando `RENTABILIDAD_ACUMULADA == 0`
3. **`comparador/elmer.py:134`** - `IndexError` si `FONDOFULL` no contiene "-": `FONDOFULL.split("-", 1)[1]`
4. **`cartolas/transform.py`** - `pl.concat([])` con carpeta vacia lanza `ValueError`

---

## 2. CALIDAD DE TESTS

### 2.1 Naming de Tests
**Estado: N/A** | **Importancia: 6/10**

No hay tests. Convencion recomendada:
```python
# tests/test_fechas.py
def test_date_range_misma_fecha_retorna_lista_unitaria():
    ...

def test_consecutive_date_ranges_lista_vacia_retorna_vacio():
    ...

def test_date_n_months_ago_febrero_bisiesto():
    ...
```

### 2.2 Patron Arrange-Act-Assert
**Estado: N/A** | **Importancia: 7/10**

Ejemplo recomendado:
```python
# tests/test_transform.py
def test_transform_single_cartola_schema_correcto(sample_cartola_csv, sample_schema):
    # Arrange
    from cartolas.transform import transform_single_cartola

    # Act
    result = transform_single_cartola(sample_cartola_csv, schema=sample_schema).collect()

    # Assert
    assert "FECHA_INF" in result.columns
    assert result["FECHA_INF"].dtype == pl.Date
    assert result["RUN_FM"].dtype == pl.UInt16
    assert len(result) == 1
```

### 2.3 Independencia de Tests
**Estado: N/A** | **Importancia: 8/10**

Riesgo principal: muchas funciones dependen de `config.py` que calcula `FECHA_MAXIMA` al importarse. Esto haria tests no-deterministicos.

**Remediacion:**
```python
# tests/conftest.py
import pytest
from unittest.mock import patch
from datetime import date

@pytest.fixture(autouse=True)
def fecha_fija():
    """Fija la fecha para todos los tests."""
    with patch("cartolas.config.FECHA_MAXIMA", date(2026, 3, 14)):
        yield
```

### 2.4 Uso de Mocks
**Estado: N/A** | **Importancia: 9/10**

Tres dependencias externas requieren mocks obligatorios:

```python
# tests/conftest.py
@pytest.fixture
def mock_bcch_api():
    """Mock de la API del Banco Central."""
    with patch("eco.bcentral.BCCh") as mock:
        mock.cuadro.return_value = pd.DataFrame({
            "DOLAR": [900.0, 901.0],
            "EURO": [950.0, 951.0],
        }, index=pd.to_datetime(["2026-03-13", "2026-03-14"]))
        yield mock

@pytest.fixture
def mock_elmer_api():
    """Mock de la API de El Mercurio."""
    with patch("comparador.elmer.requests.get") as mock:
        mock.return_value.json.return_value = {
            "d": [{"FONDOFULL": "9809-A", "CATEGORIA": "BALANCEADO MODERADO"}]
        }
        yield mock

@pytest.fixture
def mock_playwright():
    """Mock de Playwright para CMF."""
    with patch("cartolas.download.sync_playwright") as mock:
        yield mock
```

### 2.5 Manejo de Datos de Test
**Estado: N/A** | **Importancia: 7/10**

Recomendacion: usar `tmp_path` de pytest para archivos temporales y fixtures de Polars para DataFrames.

```python
@pytest.fixture
def sample_cartola_lazyframe():
    return pl.LazyFrame({
        "RUN_FM": pl.Series([9809, 9810], dtype=pl.UInt16),
        "SERIE": ["A", "A"],
        "FECHA_INF": [date(2026, 3, 1), date(2026, 3, 1)],
        "VALOR_CUOTA": [1500.50, 2000.75],
        "MONEDA": ["PESOS", "PESOS"],
        "RENTABILIDAD_DIARIA_PESOS": [1.001, 0.999],
    })
```

---

## 3. PATRONES DE TESTING

### 3.1 Piramide de Tests
**Estado: Inexistente** | **Importancia: 9/10**

Distribucion recomendada para este proyecto:

```
        /  E2E  \          2 tests  (flujos completos con mocks de APIs)
       /----------\
      / Integracion \      8 tests  (pipelines multi-modulo)
     /----------------\
    /    Unit Tests     \  40 tests (funciones individuales)
   /______________________\
```

**Remediacion - estructura de carpetas:**
```
tests/
├── conftest.py
├── unit/
│   ├── test_fechas.py          # 8 tests
│   ├── test_file_tools.py      # 5 tests
│   ├── test_decorators.py      # 4 tests
│   ├── test_polars_utils.py    # 3 tests
│   ├── test_transform.py       # 6 tests
│   ├── test_save.py            # 4 tests
│   ├── test_read.py            # 3 tests
│   ├── test_elmer.py           # 4 tests
│   └── test_bcentral.py        # 3 tests
├── integration/
│   ├── test_update_flow.py     # 3 tests
│   ├── test_cla_monthly.py     # 3 tests
│   └── test_merge.py           # 2 tests
└── e2e/
    ├── test_actualiza.py       # 1 test
    └── test_cla_report.py      # 1 test
```

### 3.2 Anti-patrones Detectados
**Importancia: 8/10**

| Anti-patron | Ubicacion | Problema |
|-------------|-----------|----------|
| **Evaluacion lazy sin validacion** | `transform.py`, `merge.py`, `cla_monthly.py` | Errores solo aparecen al `.collect()`, imposible testear transformaciones intermedias |
| **Estado global en config.py** | `cartolas/config.py` | `FECHA_MAXIMA` calculada al importar, no inyectable |
| **print() en vez de logging** | Todo el proyecto | No se puede capturar/validar output en tests |
| **Excepciones genericas** | `utiles/decorators.py` | `except Exception` impide testing de errores especificos |
| **APIs sin timeout** | `eco/bcentral.py`, `comparador/elmer.py` | Tests colgarian si el mock no intercepta |

### 3.3 Tests Fragiles Potenciales
**Importancia: 6/10**

Riesgo de fragilidad si se implementan tests que dependan de:
- Orden de columnas en Parquet (cambiar a validacion por nombre)
- Valores exactos de float (usar `pytest.approx()`)
- Hora del dia (por `DIAS_ATRAS` en config.py)
- Existencia de archivos en `cartolas/data/` (usar `tmp_path`)

### 3.4 Velocidad de Tests
**Importancia: 5/10**

Riesgos de lentitud:
- `cartolas.parquet` es ~750MB - no usar en tests
- Playwright requiere browser real - siempre mockear
- APIs externas agregan latencia - siempre mockear
- `@timer` imprime a stdout en cada test

---

## 4. TESTS FALTANTES

### 4.1 Escenarios de Error
**Importancia: 10/10**

```python
# tests/unit/test_transform.py
def test_transform_single_cartola_archivo_inexistente():
    """Debe lanzar FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        transform_single_cartola(Path("/no/existe.txt")).collect()

def test_transform_cartola_folder_vacia(empty_folder):
    """Debe manejar carpeta vacia sin lanzar ValueError de concat."""
    # ACTUALMENTE FALLA: pl.concat([]) lanza ValueError
    # FIX: agregar check len(list_txts) == 0 → return pl.LazyFrame()
    with pytest.raises(ValueError):
        transform_cartola_folder(empty_folder).collect()

# tests/unit/test_bcentral.py
def test_update_bcch_parquet_sin_archivo(tmp_path, mock_bcch_api):
    """No debe lanzar NameError cuando el parquet no existe."""
    # ACTUALMENTE FALLA: NameError en linea 220
    result = update_bcch_parquet(path=tmp_path / "bcch.parquet")
    assert result is not None
```

### 4.2 Edge Cases
**Importancia: 8/10**

```python
# tests/unit/test_fechas.py
def test_date_range_misma_fecha():
    """start == end debe retornar lista con un elemento."""
    result = date_range(date(2026, 1, 1), date(2026, 1, 1))
    assert len(result) == 1

def test_consecutive_date_ranges_lista_vacia():
    """Lista vacia debe retornar lista vacia."""
    result = consecutive_date_ranges([])
    assert result == []

def test_consecutive_date_ranges_fecha_unica():
    """Una sola fecha debe retornar un rango (fecha, fecha)."""
    result = consecutive_date_ranges([date(2026, 3, 1)])
    assert result == [(date(2026, 3, 1), date(2026, 3, 1))]

def test_date_n_months_ago_29_febrero():
    """Desde 29 feb debe retornar ultimo dia del mes anterior."""
    from dateutil.relativedelta import relativedelta
    result = date_n_months_ago(1, date(2024, 2, 29))
    assert result == date(2024, 1, 29)

# tests/unit/test_cla_monthly.py
def test_add_period_returns_division_por_cero():
    """RENTABILIDAD_ACUMULADA == 0 no debe crashear."""
    df = pl.DataFrame({
        "RUN_FM": [9809],
        "SERIE": ["A"],
        "FECHA_INF": [date(2026, 3, 1)],
        "RENTABILIDAD_ACUMULADA": [0.0],
    })
    # ACTUALMENTE: division por cero → inf/NaN silencioso
    result = add_period_returns(df, {0: date(2026, 3, 1)})
    assert not result["RENTABILIDAD_PERIODO"].to_list()[0] == float("inf")

# tests/unit/test_elmer.py
def test_filter_elmer_data_fondofull_sin_guion():
    """FONDOFULL sin '-' no debe lanzar IndexError."""
    datos = {"d": [{"FONDOFULL": "9809", "OTROS_CAMPOS": "..."}]}
    # ACTUALMENTE FALLA: FONDOFULL.split("-", 1)[1] → IndexError
    with pytest.raises(IndexError):
        filter_elmer_data(datos)
```

### 4.3 Tests de Seguridad
**Importancia: 6/10**

```python
# tests/unit/test_config.py
def test_env_file_no_expone_credenciales():
    """Las credenciales no deben estar hardcodeadas."""
    import cartolas.config as cfg
    source = Path(cfg.__file__).read_text()
    assert "BCCH_PASS" not in source or "env" in source.lower()
    assert "BCCH_USER" not in source or "env" in source.lower()

# tests/unit/test_download.py
def test_captcha_no_se_guarda_en_log():
    """El captcha resuelto no debe aparecer en logs."""
    # Validar que captchapass.predict() result no se imprime
    pass
```

### 4.4 Tests de Performance
**Importancia: 4/10**

```python
# tests/integration/test_performance.py
import time

def test_transform_rendimiento_aceptable(tmp_path):
    """Transformar 100 archivos CSV debe tomar < 5 segundos."""
    # Crear 100 CSVs pequenos
    for i in range(100):
        csv = tmp_path / f"ffmm_{i}.txt"
        csv.write_text("RUN_FM;SERIE;FECHA_INF;...\n9809;A;01/03/2026;...")

    start = time.time()
    transform_cartola_folder(tmp_path).collect()
    elapsed = time.time() - start
    assert elapsed < 5.0

def test_lectura_parquet_lazy_no_carga_memoria():
    """scan_parquet no debe cargar todo el archivo en RAM."""
    import tracemalloc
    tracemalloc.start()
    df = pl.scan_parquet("cartolas/data/parquet/cartolas.parquet")
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 100 * 1024 * 1024  # < 100MB para scan (no collect)
```

---

## 5. BUGS ENCONTRADOS DURANTE LA AUDITORIA

### 5.1 NameError en `eco/bcentral.py`
**Importancia: 10/10**

**Ubicacion**: `eco/bcentral.py`, funcion `update_bcch_parquet()`

**Problema**: Si el archivo parquet no existe, el `except FileNotFoundError` captura el error pero no define `df`. Luego, en el bloque `else`, se usa `df` que esta indefinido.

**Remediacion:**
```python
# eco/bcentral.py - update_bcch_parquet()
# Cambiar:
try:
    df = load_bcch_from_parquet()
    last_date = get_last_date_from_parquet(df)
except FileNotFoundError:
    last_date = datetime(1970, 1, 1).date()
    df = None  # <-- AGREGAR ESTA LINEA

if last_date >= LAST_DATE.date():
    if df is None:
        df = baja_bcch_as_polars(as_lazy=True)
        df.collect().write_parquet(path)
    return df
```

### 5.2 IndexError en `comparador/elmer.py`
**Importancia: 7/10**

**Ubicacion**: `comparador/elmer.py`, funcion `filter_elmer_data()`, aprox linea 134

**Problema**: `FONDOFULL.split("-", 1)[1]` lanza IndexError si el campo no contiene "-".

**Remediacion:**
```python
# Cambiar:
parts = fondo["FONDOFULL"].split("-", 1)
serie = parts[1] if len(parts) > 1 else ""
```

### 5.3 ValueError en `cartolas/transform.py`
**Importancia: 7/10**

**Ubicacion**: `cartolas/transform.py`, funcion `transform_cartola_folder()`

**Problema**: Si la carpeta esta vacia, `pl.concat([])` lanza `ValueError`.

**Remediacion:**
```python
# En transform_cartola_folder(), antes del concat:
list_txts = [txt_file for txt_file in cartola_folder.glob(wildcard)]
if not list_txts:
    return pl.LazyFrame(schema=schema)  # Retornar LazyFrame vacio con schema correcto
```

### 5.4 Division por Cero en `comparador/cla_monthly.py`
**Importancia: 8/10**

**Ubicacion**: `comparador/cla_monthly.py`, funciones `add_period_returns()` y `add_soyfocus_returns()`

**Problema**: Si `RENTABILIDAD_ACUMULADA == 0`, la division produce `inf` o `NaN` silenciosamente.

**Remediacion:**
```python
# Usar when/then para proteger la division:
pl.when(pl.col("RENTABILIDAD_ACUMULADA") != 0)
  .then(pl.col("RENTABILIDAD_RECIENTE") / pl.col("RENTABILIDAD_ACUMULADA"))
  .otherwise(None)
  .alias("RENTABILIDAD_PERIODO")
```

---

## 6. PLAN DE MEJORA PRIORIZADO

### Fase 1: Infraestructura (semana 1)
**Importancia: 10/10**

1. Agregar pytest al `pyproject.toml`
2. Crear `tests/` con `conftest.py`
3. Configurar `[tool.pytest.ini_options]` en `pyproject.toml`
4. Corregir el bug de NameError en `eco/bcentral.py`

```bash
uv add --dev pytest pytest-cov
mkdir -p tests/unit tests/integration
```

### Fase 2: Tests Unitarios Criticos (semanas 2-3)
**Importancia: 9/10**

Prioridad por modulo:

| Archivo de Test | Funciones a Testear | Tests Estimados |
|-----------------|---------------------|-----------------|
| `tests/unit/test_fechas.py` | `date_range`, `consecutive_date_ranges`, `date_n_months_ago`, `ultimo_dia_mes_anterior` | 8 |
| `tests/unit/test_transform.py` | `transform_single_cartola`, `transform_cartola_folder` | 6 |
| `tests/unit/test_polars_utils.py` | `map_s_n_to_bool`, `replace_null_with_one` | 3 |
| `tests/unit/test_file_tools.py` | `clean_txt_folder`, `leer_json`, `obtener_archivo_mas_reciente` | 5 |
| `tests/unit/test_bcentral.py` | `update_bcch_parquet`, `update_bcch_for_cartolas` | 3 |
| `tests/unit/test_elmer.py` | `filter_elmer_data`, `last_elmer_data` | 4 |

### Fase 3: Tests de Integracion (semana 4)
**Importancia: 8/10**

| Archivo de Test | Flujo a Testear | Tests Estimados |
|-----------------|-----------------|-----------------|
| `tests/integration/test_update_flow.py` | download → transform → save | 3 |
| `tests/integration/test_cla_monthly.py` | merge → returns → statistics → excel | 3 |
| `tests/integration/test_merge.py` | cartolas + bcch + elmer → merged | 2 |

### Fase 4: Mejoras Estructurales (semanas 5-6)
**Importancia: 7/10**

1. Inyectar configuracion (paths, fechas) en vez de usar globals
2. Reemplazar `print()` con `logging`
3. Parametrizar decoradores de retry
4. Agregar timeouts a `requests.get()` y `BCCh.cuadro()`

---

## 7. RESUMEN DE HALLAZGOS

| Hallazgo | Importancia | Estado |
|----------|-------------|--------|
| **0% cobertura de tests** | 10/10 | Sin infraestructura de testing |
| **Bug NameError en bcentral.py** | 10/10 | `df` indefinido tras FileNotFoundError |
| **Sin pytest ni dependencias de test** | 10/10 | No existe en pyproject.toml |
| **APIs externas sin timeout** | 9/10 | BCCh y Elmer pueden colgar indefinidamente |
| **Division por cero en calculos financieros** | 8/10 | `add_period_returns()`, `add_soyfocus_returns()` |
| **Excepciones genericas en decoradores** | 8/10 | `except Exception` en retry swallows errors |
| **Estado global no testeable (config.py)** | 8/10 | `FECHA_MAXIMA` calculada al import |
| **IndexError en elmer.py** | 7/10 | `split("-")[1]` sin validacion |
| **ValueError con carpeta vacia** | 7/10 | `pl.concat([])` en transform |
| **print() en vez de logging** | 6/10 | Imposible validar output en tests |
| **Sin CI/CD** | 6/10 | No hay pipeline de validacion automatica |
| **Sin tests de edge cases en fechas** | 6/10 | Bisiesto, limites de mes, misma fecha |
| **fill_null(1) enmascara errores** | 5/10 | TIPO_CAMBIO=1 para monedas sin dato |
| **Sin tests de performance** | 4/10 | Parquet de 750MB sin benchmarks |
