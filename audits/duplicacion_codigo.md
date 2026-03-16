# Auditoría de Duplicación de Código — Proyecto Cartolas

**Fecha:** 2026-03-16
**Alcance:** Todo el repositorio (`cartolas/`, `comparador/`, `eco/`, scripts raíz)

---

## Resumen Ejecutivo

Se identificaron **12 categorías de duplicación** que afectan 15+ archivos. Las más críticas son: scripts CLA prácticamente idénticos (9/10), pipelines de actualización con ~80% de overlap (8/10), y constantes SoyFocus dispersas en 4+ lugares (8/10). La remediación completa reduciría ~300 líneas de código duplicado y eliminaría fuentes frecuentes de bugs por inconsistencia.

---

## Tabla de Hallazgos

| # | Hallazgo | Severidad | Archivos afectados | Esfuerzo |
|---|----------|:---------:|:-------------------:|:--------:|
| 1 | Scripts `cla_mensual.py` vs `cla_mensual2.py` | **9/10** | 2 | Bajo |
| 2 | `update.py` vs `update_by_year.py` — pipeline duplicado | **8/10** | 2 | Medio |
| 3 | Constantes SoyFocus en 4+ lugares | **8/10** | 4 | Bajo |
| 4 | Cálculos financieros duplicados (`merge.py` vs `soyfocus.py`) | **7/10** | 2 | Alto |
| 5 | Fechas hardcodeadas en `tablas.py` | **7/10** | 2 | Bajo |
| 6 | Definiciones de columnas repetidas | **6/10** | 3 | Medio |
| 7 | Patrón `isinstance(df, pl.LazyFrame)` repetido | **6/10** | 1 | Bajo |
| 8 | RUN_FM hardcodeados `[9809, 9810, 9811]` | **6/10** | 2 | Bajo |
| 9 | Patrón `fill_nan/fill_null` repetido | **5/10** | 4 | Bajo |
| 10 | Carga de `.env` duplicada | **5/10** | 2 | Bajo |
| 11 | Patrón `unique().collect().to_list()` | **5/10** | 2 | Bajo |
| 12 | Patrón `shift().over()` repetido | **4/10** | 2 | Bajo |

---

## Detalle de Hallazgos

### 1. Scripts `cla_mensual.py` vs `cla_mensual2.py` — Severidad: 9/10

**Problema:** Dos scripts casi idénticos coexisten en la raíz del proyecto. `cla_mensual2.py` es una evolución de `cla_mensual.py` con ligeras variaciones en el mapeo de categorías y formato de salida.

**Ubicación:**
- `cla_mensual.py` (líneas 1-30)
- `cla_mensual2.py` (líneas 1-70)

**Código duplicado en `cla_mensual.py`:**
```python
from comparador.cla_monthly import generate_cla_data
from cartolas.update_by_year import update_parquet_by_year
from eco.bcentral import update_bcch_parquet

if __name__ == "__main__":
    update_parquet_by_year()
    update_bcch_parquet()
    generate_cla_data()
```

**Código duplicado en `cla_mensual2.py`:**
```python
from comparador.cla_monthly import generate_cla_data
from cartolas.update_by_year import update_parquet_by_year
from eco.bcentral import update_bcch_parquet

# ... mismo pipeline con variaciones en custom_mapping
if __name__ == "__main__":
    update_parquet_by_year()
    update_bcch_parquet()
    generate_cla_data(custom_mapping=custom_mapping)
```

**Remediación:** Eliminar `cla_mensual.py` y mantener solo `cla_mensual2.py` (o viceversa), parametrizando las diferencias. Alternativamente, crear una función `run_cla_pipeline(custom_mapping=None)` en `comparador/` que ambos scripts invoquen.

---

### 2. `update.py` vs `update_by_year.py` — Pipeline duplicado ~80% — Severidad: 8/10

**Problema:** Ambos módulos implementan el mismo pipeline de descarga → transformación → guardado con ~80% de código compartido. La única diferencia real es la granularidad temporal (diaria vs anual).

**Ubicación:**
- `cartolas/update.py` — pipeline completo de actualización diaria
- `cartolas/update_by_year.py` — pipeline de actualización por año

**Patrón compartido:**
```python
# Ambos archivos repiten:
# 1. Descarga de archivos TXT desde CMF
# 2. Transformación TXT → LazyFrame con esquema tipado
# 3. Guardado como Parquet con deduplicación
```

**Remediación:** Extraer la lógica común a una función `_run_update_pipeline(date_ranges, output_path)` en un módulo compartido (e.g., `cartolas/pipeline.py`), y que ambos scripts la invoquen con diferentes parámetros de rango de fechas y ruta de salida.

---

### 3. Constantes SoyFocus en 4+ lugares — Severidad: 8/10

**Problema:** Los fondos SoyFocus (RUN 9809, 9810, 9811) están definidos en 4 representaciones distintas con estructuras de datos diferentes.

**Ubicación exacta:**

| Archivo | Línea | Definición |
|---------|-------|------------|
| `cartolas/config.py` | 105 | `SOYFOCUS_FUNDS = {9809: "MODERADO", 9810: "CONSERVADOR", 9811: "ARRIESGADO"}` |
| `comparador/cla_monthly.py` | 41-45 | `SOYFOCUS_DEFAULTS = {9810: ("BALANCEADO CONSERVADOR", "Fondo Conservador Focus"), ...}` |
| `comparador/merge.py` | 257-262 | `categories_mapping = {"BALANCEADO CONSERVADOR": 9810, ...}` |
| `resumen_apv.py` | 13 | `[9809, 9810, 9811]` hardcodeado en filtro |

**Ejemplo de inconsistencia:**
```python
# config.py — usa nombre corto
{9809: "MODERADO", 9810: "CONSERVADOR", 9811: "ARRIESGADO"}

# cla_monthly.py — usa nombre largo + display name
{9810: ("BALANCEADO CONSERVADOR", "Fondo Conservador Focus"), ...}

# merge.py — mapeo inverso (nombre → RUN)
{"BALANCEADO CONSERVADOR": 9810, ...}
```

**Remediación:** Crear una única fuente de verdad en `config.py` con un dataclass o dict anidado:
```python
SOYFOCUS = {
    9809: {"nombre": "MODERADO", "categoria": "BALANCEADO MODERADO", "display": "Fondo Moderado Focus"},
    9810: {"nombre": "CONSERVADOR", "categoria": "BALANCEADO CONSERVADOR", "display": "Fondo Conservador Focus"},
    9811: {"nombre": "ARRIESGADO", "categoria": "BALANCEADO AGRESIVO", "display": "Fondo Arriesgado Focus"},
}
# Derivar las demás representaciones:
SOYFOCUS_FUNDS = {k: v["nombre"] for k, v in SOYFOCUS.items()}
SOYFOCUS_RUNS = list(SOYFOCUS.keys())
CATEGORIES_MAPPING = {v["categoria"]: k for k, v in SOYFOCUS.items()}
```

---

### 4. Cálculos financieros duplicados — Severidad: 7/10

**Problema:** `comparador/merge.py` y `cartolas/soyfocus.py` implementan cálculos financieros casi idénticos (~70% overlap): rentabilidad diaria, rentabilidad acumulada, patrimonio anterior, etc.

**Ubicación:**

| Cálculo | `merge.py` | `soyfocus.py` |
|---------|-----------|---------------|
| Valor cuota anterior | 104-109 | 141-145 |
| Patrimonio anterior | 143-152 | 148-152 |
| Rentabilidad diaria | 110-124 | 155-165 |
| Cum prod acumulada | (en `cla_monthly.py` 132-140) | — |

**Snippet `merge.py` (líneas 104-109):**
```python
pl.col("VALOR_CUOTA_PESOS")
    .shift(1)
    .over(["RUN_FM", "SERIE"])
    .alias("VALOR_CUOTA_ANTERIOR_PESOS")
```

**Snippet `soyfocus.py` (líneas 141-145):**
```python
pl.col("VALOR_CUOTA")
    .shift(1)
    .over(["RUN_FM", "SERIE"])
    .alias("VALOR_CUOTA_ANTERIOR")
```

**Remediación:** Crear un módulo `cartolas/financials.py` con funciones reutilizables:
```python
def previous_value(col: str, alias: str, partition: list[str] = ["RUN_FM", "SERIE"]) -> pl.Expr:
    return pl.col(col).shift(1).over(partition).alias(alias)

def daily_return(current: str, previous: str, alias: str) -> pl.Expr:
    return (pl.col(current) / pl.col(previous)).alias(alias)
```

---

### 5. Fechas hardcodeadas en `tablas.py` — Severidad: 7/10

**Problema:** `comparador/tablas.py` tiene fechas de 2024/2025 hardcodeadas que dejarán de funcionar correctamente. Existe código dinámico correcto **comentado** justo debajo.

**Ubicación:** `comparador/tablas.py` líneas 49-58

**Código problemático:**
```python
selected_dates = {
    "OM": max_date,
    "1M": date(2025, 2, 28),      # ← HARDCODED
    "3M": date(2024, 12, 31),     # ← HARDCODED
    "6M": date(2024, 9, 30),      # ← HARDCODED
    "1Y": date(2024, 3, 31),      # ← HARDCODED
    "3Y": date(2022, 3, 31),      # ← HARDCODED
    "5Y": date(2020, 3, 31),      # ← HARDCODED
    "YTD": date(2024, 12, 31),    # ← HARDCODED
}
```

**Código dinámico comentado (líneas 60-68):**
```python
# selected_dates = {
#     "1M": last_day_n_months_ago(max_date, 1),
#     "3M": last_day_n_months_ago(max_date, 3),
#     ...
# }
```

**Otras fechas hardcodeadas:**
- `resumen_apv.py` línea 19: `pl.col("FECHA_INF") > date(2024, 1, 1)`
- `cartolas/download.py` líneas 146-147: `start_date = date(2021, 1, 1)` (en bloque `__main__`, menor impacto)

**Remediación:** Descomentar el código dinámico en `tablas.py` y eliminar las fechas hardcodeadas. En `resumen_apv.py`, parametrizar la fecha de inicio.

---

### 6. Definiciones de columnas repetidas — Severidad: 6/10

**Problema:** Listas de columnas relevantes definidas independientemente en 3 módulos con overlap significativo.

**Ubicación:**

**`comparador/merge.py` líneas 13-32:**
```python
COLUMNAS_RELEVANTES = [
    "RUN_ADM", "RUN_FM", "FECHA_INF", "MONEDA", "SERIE",
    "CUOTAS_APORTADAS", "CUOTAS_RESCATADAS", "CUOTAS_EN_CIRCULACION",
    "VALOR_CUOTA", "NUM_PARTICIPES", "REM_FIJA", "REM_VARIABLE",
    "GASTOS_AFECTOS", "GASTOS_NO_AFECTOS", "COMISION_INVERSION",
    "COMISION_RESCATE", "FACTOR DE AJUSTE", "FACTOR DE REPARTO"
]
```

**`cartolas/soyfocus.py` líneas 224-249:** 25 columnas con comentarios detallados, overlap ~70% con `merge.py`.

**`comparador/cla_monthly.py` líneas 48-56:**
```python
RELEVANT_COLUMNS = [
    "RUN_FM", "SERIE", "FECHA_INF", "CATEGORIA",
    "RENTABILIDAD_ACUMULADA", "RUN_SOYFOCUS", "SERIE_SOYFOCUS"
]
```

**Remediación:** Centralizar en `config.py` las columnas base del esquema CMF y definir subconjuntos nombrados:
```python
COLUMNAS_BASE = ["RUN_FM", "FECHA_INF", "SERIE", ...]
COLUMNAS_FINANCIERAS = COLUMNAS_BASE + ["REM_FIJA", "REM_VARIABLE", ...]
COLUMNAS_CLA = ["RUN_FM", "SERIE", "FECHA_INF", "CATEGORIA", ...]
```

---

### 7. Patrón `isinstance(df, pl.LazyFrame)` repetido — Severidad: 6/10

**Problema:** El mismo check de tipo aparece 4 veces en `comparador/tablas.py`.

**Ubicación:** `comparador/tablas.py` líneas 22-23, 87-88, 124-125, 168-169

**Patrón repetido:**
```python
if isinstance(df, pl.LazyFrame):
    df = df.collect()
```

**Remediación:** Crear utilidad en `utiles/`:
```python
def ensure_dataframe(df: pl.LazyFrame | pl.DataFrame) -> pl.DataFrame:
    return df.collect() if isinstance(df, pl.LazyFrame) else df
```

---

### 8. RUN_FM hardcodeados — Severidad: 6/10

**Problema:** Los RUN de fondos SoyFocus aparecen como literales numéricos fuera de `config.py`.

**Ubicación:**
- `resumen_apv.py` línea 13: `pl.col("RUN_FM").is_in([9809, 9810, 9811])`
- `comparador/merge.py` líneas 257-262: `categories_mapping` con 9809, 9810, 9811

**Remediación:** Importar desde `config.py`:
```python
from cartolas.config import SOYFOCUS_FUNDS
# ...
pl.col("RUN_FM").is_in(list(SOYFOCUS_FUNDS.keys()))
```

---

### 9. Patrón `fill_nan/fill_null` repetido — Severidad: 5/10

**Problema:** La combinación `.fill_nan().fill_null()` aparece 9+ veces con variaciones en el valor de relleno (0 o 1) y el orden de las llamadas.

**Ubicación:**

| Archivo | Líneas | Variante |
|---------|--------|----------|
| `comparador/cla_monthly.py` | 137-138 | `.fill_nan(1).fill_null(1)` |
| `comparador/merge.py` | 77 | `.fill_null(1)` |
| `comparador/merge.py` | 123-124 | `.fill_nan(1).fill_null(1)` |
| `comparador/merge.py` | 147-148 | `.fill_nan(0).fill_null(0)` |
| `comparador/tablas.py` | 171 | `.fill_null(1).fill_nan(1)` |
| `cartolas/soyfocus.py` | 178 | `.fill_null(0).fill_nan(0)` |
| `cartolas/soyfocus.py` | 351-352 | `.fill_nan(0).fill_null(0)` |
| `cartolas/soyfocus.py` | 372-373 | `.fill_nan(0).fill_null(0)` |
| `ejercicios/vivienda.py` | 62 | `.fill_nan(0).fill_null(0)` |

**Remediación:** No es crítico — es un patrón idiomático de Polars. Sin embargo, se podría normalizar el orden (siempre `fill_nan` antes de `fill_null`) y crear un helper si se desea:
```python
def fill_safe(col: str, default=0) -> pl.Expr:
    return pl.col(col).fill_nan(default).fill_null(default)
```

---

### 10. Carga de `.env` duplicada — Severidad: 5/10

**Problema:** Dos módulos cargan `.env` de forma independiente.

**Ubicación:**
- `eco/bcentral.py` línea 10, 18: `from dotenv import dotenv_values` → `env_variables = dotenv_values(".env")`
- `cartolas/economy.py` línea 1, 3: `from dotenv import dotenv_values` → `config = dotenv_values(".env")`

**Remediación:** Centralizar en `cartolas/config.py`:
```python
from dotenv import dotenv_values
ENV = dotenv_values(".env")
```
Y que ambos módulos importen `from cartolas.config import ENV`.

---

### 11. Patrón `unique().collect().to_list()` — Severidad: 5/10

**Problema:** Patrón repetido para obtener valores únicos de una columna.

**Ubicación:** Aparece en `comparador/merge.py` y `cartolas/soyfocus.py` (4+ instancias).

**Patrón:**
```python
runs = df.select("RUN_FM").unique().collect().to_series().to_list()
```

**Remediación:** Crear helper:
```python
def unique_values(lf: pl.LazyFrame, col: str) -> list:
    return lf.select(col).unique().collect().to_series().to_list()
```

---

### 12. Patrón `shift().over()` repetido — Severidad: 4/10

**Problema:** El patrón para obtener el valor anterior particionado aparece 4 veces.

**Ubicación:**
- `cartolas/soyfocus.py` líneas 141-145, 148-152
- `comparador/merge.py` líneas 104-109, 143-152

**Patrón:**
```python
pl.col("COLUMNA").shift(1).over(["RUN_FM", "SERIE"]).alias("COLUMNA_ANTERIOR")
```

**Remediación:** (Ya cubierta en hallazgo #4). Crear expresión reutilizable `previous_value()`.

---

## Plan de Remediación Priorizado

### Fase 1 — Quick Wins (1-2 horas, impacto alto)

| Acción | Hallazgo | Impacto |
|--------|----------|---------|
| Eliminar `cla_mensual.py`, mantener solo `cla_mensual2.py` | #1 | Elimina script duplicado completo |
| Descomentar fechas dinámicas en `tablas.py` | #5 | Elimina bug temporal |
| Reemplazar RUN hardcodeados por `config.SOYFOCUS_FUNDS` | #8 | Centraliza constantes |
| Centralizar carga `.env` en `config.py` | #10 | Elimina import duplicado |

### Fase 2 — Consolidación de Constantes (2-3 horas, impacto medio-alto)

| Acción | Hallazgo | Impacto |
|--------|----------|---------|
| Crear definición única SoyFocus en `config.py` con derivaciones | #3 | Elimina 4 definiciones dispersas |
| Mover definiciones de columnas a `config.py` | #6 | Centraliza esquema |
| Crear `ensure_dataframe()` en `utiles/` | #7 | Elimina 4 checks repetidos |

### Fase 3 — Refactoring Estructural (4-6 horas, impacto alto)

| Acción | Hallazgo | Impacto |
|--------|----------|---------|
| Crear `cartolas/financials.py` con expresiones reutilizables | #4, #12 | Elimina ~50 líneas duplicadas |
| Unificar `update.py` y `update_by_year.py` con pipeline común | #2 | Elimina ~80% de duplicación |
| Normalizar patrón `fill_nan/fill_null` | #9 | Consistencia en todo el proyecto |

### Fase 4 — Mejoras Opcionales (bajo impacto)

| Acción | Hallazgo | Impacto |
|--------|----------|---------|
| Crear helper `unique_values()` | #11 | Legibilidad |
| Documentar decisiones de diseño | Todos | Prevención futura |

---

## Métricas Estimadas

- **Líneas duplicadas identificadas:** ~300
- **Archivos afectados:** 15+
- **Reducción estimada post-remediación:** ~200 líneas (-15% en módulos afectados)
- **Riesgo de inconsistencia actual:** Alto (especialmente constantes SoyFocus y fechas)
