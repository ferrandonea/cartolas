# Auditoría de Complejidad del Código

**Fecha**: 2026-03-16
**Codebase**: cartolas
**Total archivos Python**: 33 (4.063 líneas)

---

## 1. Complejidad Ciclomática

### Funciones con complejidad > 10

| Función | Archivo | Complejidad Estimada | Importancia |
|---------|---------|---------------------|-------------|
| `generate_cla_data` | `comparador/cla_monthly.py:288` | ~18 | 8/10 |
| `write_hoja_10_salida` | `comparador/cla_monthly.py:466` | ~15 | 6/10 |
| `create_soyfocus_parquet` | `cartolas/soyfocus.py:25` | ~12 | 5/10 |
| `prepare_relevant_categories` | `comparador/merge.py:234` | ~14 | 7/10 |
| `update_parquet_by_year` | `cartolas/update_by_year.py:38` | ~11 | 6/10 |
| `prepare_cartolas_in_pesos` | `comparador/merge.py:43` | ~10 | 5/10 |

#### Detalle: `generate_cla_data` — Complejidad ~18 — **8/10**

**Problema**: Función de 175 líneas que orquesta 9 pasos secuenciales, contiene lógica condicional para `custom_mapping` (4 ramas), `excel_steps` (3 niveles × 7 puntos de chequeo = ~21 evaluaciones de `save_xlsx`), y manejo de `excel_categorias`.

**Remediación**: Extraer la lógica de `custom_mapping` y la de escritura Excel en funciones separadas.

```python
# Antes (líneas 354-386 de cla_monthly.py):
# 33 líneas de lógica custom_mapping incrustadas en generate_cla_data

# Después:
def _resolve_custom_categories(
    df_base: pl.LazyFrame,
    custom_mapping: dict[int, int],
    categories: list[str],
) -> tuple[list[str], list[tuple[str, str]] | None]:
    """Resuelve categorías custom y retorna (categories, excel_categorias)."""
    custom_num_cats = list(set(custom_mapping.values()))
    num_to_name = dict(
        df_base.filter(pl.col("NUM_CATEGORIA").is_in(custom_num_cats))
        .select("NUM_CATEGORIA", "CATEGORIA")
        .unique()
        .collect()
        .iter_rows()
    )
    run_to_new_cat = {}
    for run_fm, num_cat in custom_mapping.items():
        if num_cat not in num_to_name:
            raise ValueError(
                f"NUM_CATEGORIA {num_cat} (para RUN_FM {run_fm}) no tiene "
                f"fondos retail en los datos de Elmer."
            )
        run_to_new_cat[run_fm] = num_to_name[num_cat]

    cats_to_remove = {
        SOYFOCUS_DEFAULTS[run_fm][0]
        for run_fm in run_to_new_cat
        if run_fm in SOYFOCUS_DEFAULTS
    }
    new_categories = [c for c in categories if c not in cats_to_remove] + list(
        run_to_new_cat.values()
    )
    excel_categorias = [
        (run_to_new_cat[run_fm], display) if run_fm in run_to_new_cat else (cat, display)
        for run_fm, (cat, display) in SOYFOCUS_DEFAULTS.items()
    ]
    return new_categories, excel_categorias
```

#### Detalle: `write_hoja_10_salida` — Complejidad ~15 — **6/10**

**Problema**: 176 líneas (466-642) con un loop por categoría que contiene 5 sub-bloques casi idénticos (cada uno itera sobre `periodos` con lógica condicional de `val.empty`/`pd.notnull`). Mucha repetición de patrón de escritura de celdas.

**Remediación**: Extraer un helper para escribir una fila de valores.

```python
def _write_period_row(worksheet, row, df_cat, periodos, col_name, fmt, fmt_empty, col_a_fmt, label):
    """Escribe una fila de valores por período en el worksheet."""
    worksheet.write(row, 0, label, col_a_fmt)
    for j, per in enumerate(periodos):
        val = df_cat.loc[df_cat["PERIODO"] == per, col_name]
        if not val.empty and pd.notnull(val.values[0]):
            worksheet.write(row, j + 1, float(val.values[0]), fmt)
        else:
            worksheet.write(row, j + 1, "", fmt_empty)
```

#### Detalle: `prepare_relevant_categories` — Complejidad ~14 — **7/10**

**Problema**: Función de 89 líneas (234-322) con 3 bloques condicionales `if custom_mapping is not None`, cada uno con lógica de construcción de expresiones Polars encadenadas. La lógica de validación ya fue extraída a `_validate_custom_mapping`, pero la aplicación del mapping sigue siendo compleja.

**Remediación**: Extraer la construcción de expresiones `when/then/otherwise` a un helper.

```python
def _build_override_expr(base_col: str, mapping: dict, match_col: str, value_fn) -> pl.Expr:
    """Construye expresión when/then/otherwise encadenada."""
    expr = pl.col(base_col)
    for key, value in mapping.items():
        expr = (
            pl.when(pl.col(match_col) == value_fn(key, value))
            .then(pl.lit(value_fn(key, value)))
            .otherwise(expr)
        )
    return expr
```

---

## 2. Complejidad Cognitiva

### Funciones difíciles de entender

| Función | Archivo | Nivel Cognitivo | Razón | Importancia |
|---------|---------|----------------|-------|-------------|
| `generate_cla_data` | `comparador/cla_monthly.py:288` | Alto | 9 pasos secuenciales + branching por custom_mapping + branching por excel_steps | 8/10 |
| `create_soyfocus_parquet` | `cartolas/soyfocus.py:25` | Alto | Cadena de 13 `.with_columns()` consecutivos sin separación lógica | 7/10 |
| `prepare_cartolas_in_pesos` | `comparador/merge.py:43` | Alto | Cadena de 12 `.with_columns()` con joins y cálculos financieros mezclados | 7/10 |
| `write_hoja_10_salida` | `comparador/cla_monthly.py:466` | Medio-Alto | 9 formatos Excel + loop anidado + 5 sub-bloques repetitivos | 6/10 |
| `create_tac_report` | `cartolas/soyfocus.py:278` | Medio | Cadena de 8 `.with_columns()` con fórmulas financieras complejas | 5/10 |

#### Detalle: Cadenas largas de `.with_columns()` — **7/10**

**Problema**: `create_soyfocus_parquet` (líneas 87-179) y `prepare_cartolas_in_pesos` (líneas 60-164) son cadenas monolíticas de 12-13 operaciones `.with_columns()`. Cada operación agrega una columna calculada, pero no hay separación entre las fases lógicas (preparación → cálculos intermedios → resultados finales).

**Remediación**: Agrupar operaciones relacionadas en funciones con nombres descriptivos. Ejemplo para `create_soyfocus_parquet`:

```python
def _add_patrimonio_ajustado(df: pl.LazyFrame) -> pl.LazyFrame:
    """Calcula patrimonio ajustado, gastos y costos."""
    return (
        df.with_columns(
            ((pl.col("CUOTAS_EN_CIRCULACION") + pl.col("CUOTAS_RESCATADAS")
              - pl.col("CUOTAS_APORTADAS")) * pl.col("VALOR_CUOTA")
            ).alias("PATRIMONIO_AJUSTADO")
        )
        .with_columns((pl.col("GASTOS_AFECTOS") + pl.col("GASTOS_NO_AFECTOS")).alias("GASTOS_TOTALES"))
        .with_columns((pl.col("REM_FIJA") + pl.col("REM_VARIABLE") + pl.col("GASTOS_TOTALES")).alias("COSTOS_TOTALES"))
        .with_columns((pl.col("PATRIMONIO_AJUSTADO") + pl.col("GASTOS_TOTALES")).alias("PATRIMONIO_AJUSTADO_GASTOS"))
        .with_columns((pl.col("PATRIMONIO_AJUSTADO") + pl.col("COSTOS_TOTALES")).alias("PATRIMONIO_AJUSTADO_COSTOS"))
    )

def _add_flujos(df: pl.LazyFrame) -> pl.LazyFrame:
    """Calcula flujos netos de cuotas."""
    return (
        df.with_columns((pl.col("CUOTAS_APORTADAS") - pl.col("CUOTAS_RESCATADAS")).alias("CUOTAS_NETAS"))
        .with_columns((pl.col("CUOTAS_NETAS") * pl.col("VALOR_CUOTA").round(0)).alias("FLUJO_NETO"))
    )

def _add_rentabilidad(df: pl.LazyFrame) -> pl.LazyFrame:
    """Calcula valores anteriores y rentabilidad."""
    return (
        df.with_columns(pl.col("VALOR_CUOTA").shift(1).over(["RUN_FM", "SERIE"]).alias("VALOR_CUOTA_ANTERIOR"))
        .with_columns(pl.col("PATRIMONIO_NETO").shift(1).over(["RUN_FM", "SERIE"]).alias("PATRIMONIO_NETO_ANTERIOR"))
        .with_columns((pl.col("VALOR_CUOTA") * pl.col("FACTOR DE REPARTO") * pl.col("FACTOR DE AJUSTE")).alias("VALOR_CUOTA_AJUSTADO"))
        .with_columns((pl.col("VALOR_CUOTA_AJUSTADO") / pl.col("VALOR_CUOTA_ANTERIOR")).alias("RENTABILIDAD"))
        .with_columns((pl.col("PATRIMONIO_NETO") - pl.col("PATRIMONIO_NETO_ANTERIOR")).alias("DELTA_PATRIMONIO_NETO"))
        .with_columns(((pl.col("DELTA_PATRIMONIO_NETO") - pl.col("FLUJO_NETO")).round(0)).alias("EFECTO_PRECIO_EN_DELTA_PATRIMONIO"))
        .with_columns(pl.col("PATRIMONIO_NETO_ANTERIOR").fill_null(0).fill_nan(0))
    )
```

#### Detalle: Niveles de abstracción mezclados — **6/10**

**Problema**: `generate_cla_data` mezcla lógica de negocio (cálculos de rentabilidad), lógica de presentación (guardado en Excel, formateo), y lógica de orquestación (pasos 1-9). Los checks de `if save_xlsx and excel_steps in [...]` aparecen 7 veces intercalados con la lógica de negocio.

**Remediación**: Separar el pipeline de datos del guardado Excel.

```python
def generate_cla_data(...) -> pl.DataFrame:
    # Solo pipeline de datos, retorna df_with_stats y df_stats
    ...
    return df_with_stats, df_stats

def generate_cla_excel(input_date, xlsx_name, excel_steps="minimal", **kwargs):
    # Orquesta generate_cla_data + guardado Excel
    df_with_stats, df_stats = generate_cla_data(input_date, **kwargs)
    if excel_steps != "none":
        _save_to_excel(df_stats, xlsx_name, excel_steps)
    return df_with_stats
```

---

## 3. Métricas de Líneas de Código

### Archivos > 300 líneas

| Archivo | Líneas | Importancia |
|---------|--------|-------------|
| `comparador/cla_monthly.py` | 650 | 8/10 |
| `cartolas/soyfocus.py` | 428 | 6/10 |
| `comparador/merge.py` | 357 | 7/10 |
| `utiles/fechas.py` | 307 | 3/10 |

### Funciones > 50 líneas

| Función | Archivo | Líneas | Importancia |
|---------|---------|--------|-------------|
| `write_hoja_10_salida` | `comparador/cla_monthly.py:466` | 176 | 6/10 |
| `generate_cla_data` | `comparador/cla_monthly.py:288` | 175 | 8/10 |
| `create_soyfocus_parquet` | `cartolas/soyfocus.py:25` | 161 | 7/10 |
| `prepare_cartolas_in_pesos` | `comparador/merge.py:43` | 122 | 7/10 |
| `soy_focus_by_run` | `cartolas/soyfocus.py:188` | 88 | 4/10 |
| `prepare_relevant_categories` | `comparador/merge.py:234` | 89 | 7/10 |
| `create_tac_report` | `cartolas/soyfocus.py:278` | 133 | 5/10 |
| `update_parquet_by_year` | `cartolas/update_by_year.py:38` | 96 | 6/10 |

**Nota**: `utiles/fechas.py` tiene 307 líneas pero ~60% son docstrings y código de test en `__main__`. La complejidad real es baja — **3/10**.

---

## 4. Métricas de Acoplamiento

### Acoplamiento Aferente (quien depende de este módulo)

| Módulo | Dependientes | Importancia |
|--------|-------------|-------------|
| `cartolas/config.py` | 9 módulos | 9/10 |
| `cartolas/read.py` | 4 módulos | 5/10 |
| `utiles/fechas.py` | 4 módulos | 4/10 |
| `utiles/decorators.py` | 4 módulos | 3/10 |
| `utiles/file_tools.py` | 3 módulos | 4/10 |
| `comparador/merge.py` | 2 módulos | 5/10 |
| `comparador/cla_monthly.py` | 3 módulos | 6/10 |

### Acoplamiento Eferente (de cuántos módulos depende)

| Módulo | Dependencias | Importancia |
|--------|-------------|-------------|
| `comparador/merge.py` | 5 módulos | 6/10 |
| `comparador/cla_monthly.py` | 3 módulos | 5/10 |
| `cartolas/update_by_year.py` | 6 módulos | 5/10 |
| `cartolas/update.py` | 6 módulos | 5/10 |
| `cartolas/download.py` | 5 módulos | 4/10 |

### Índice de Inestabilidad (Ce / (Ca + Ce))

| Módulo | Ca | Ce | Inestabilidad | Nota |
|--------|----|----|--------------|------|
| `cartolas/config.py` | 9 | 2 | 0.18 | Estable (bien) |
| `comparador/merge.py` | 2 | 5 | 0.71 | Inestable |
| `comparador/cla_monthly.py` | 3 | 3 | 0.50 | Intermedio |
| `cartolas/update_by_year.py` | 1 | 6 | 0.86 | Muy inestable (aceptable, es script de orquestación) |

### Hallazgo: Dependencia circular `config.py` ↔ `file_tools.py` — **9/10**

**Problema**: `cartolas/config.py:55` importa `generate_hash_image_name` de `utiles/file_tools.py`, y `utiles/file_tools.py:53` importa `CARTOLAS_FOLDER` de `cartolas/config.py`. Ambos usan `# noqa: E402` para evitar el error de linting por import fuera de orden.

**Remediación**: Mover `generate_hash_image_name` y `generate_hash_name` a un módulo sin dependencias de `config.py`, o pasar `CARTOLAS_FOLDER` como parámetro en `file_tools.py` en lugar de importarlo a nivel de módulo.

```python
# utiles/file_tools.py — Eliminar el import circular
# Antes (línea 53):
from cartolas.config import CARTOLAS_FOLDER  # noqa: E402

# Después: usar parámetro en lugar de import
def clean_txt_folder(
    folder: str | Path,  # Ya no tiene default que requiere config
    wildcard: str = WILDCARD_CARTOLAS_TXT,
    ...
) -> None:
```

---

## 5. Análisis de Cohesión

### Módulos con responsabilidad única bien definida

| Módulo | Responsabilidad | Cohesión | Nota |
|--------|----------------|----------|------|
| `cartolas/read.py` | Lectura de parquet | Alta | 1 función, enfocada |
| `cartolas/save.py` | Escritura de parquet | Alta | 1 función, enfocada |
| `cartolas/transform.py` | TXT → LazyFrame | Alta | 2 funciones relacionadas |
| `cartolas/polars_utils.py` | Helpers de Polars | Alta | 2 funciones utilitarias |
| `utiles/decorators.py` | Decoradores | Alta | 3 decoradores bien definidos |
| `utiles/listas.py` | Operaciones de listas | Alta | 1 función |

### Modulos con cohesión mejorable

| Módulo | Problema | Importancia |
|--------|----------|-------------|
| `comparador/cla_monthly.py` | Mezcla pipeline de datos + formateo Excel + constantes | 8/10 |
| `cartolas/soyfocus.py` | 3 funciones grandes poco relacionadas entre sí (parquet, by_run, tac) | 6/10 |
| `comparador/merge.py` | Mezcla preparación de datos económicos + validación de mapping + merge | 6/10 |
| `utiles/file_tools.py` | Mezcla generación de hashes + limpieza de archivos + lectura JSON | 5/10 |
| `comparador/tablas.py` | Fechas hardcodeadas (líneas 50-57), mezcla Polars con NumPy | 7/10 |

#### Detalle: `comparador/cla_monthly.py` — **8/10**

**Problema**: Este archivo tiene 650 líneas y combina:
1. Constantes de configuración (líneas 33-71)
2. Pipeline de cálculos financieros (funciones `add_*`)
3. Función orquestadora `generate_cla_data`
4. Formateo y escritura de Excel (`write_hoja_10_salida`)

**Remediación**: Separar en al menos 2 archivos:
- `comparador/cla_monthly.py` — pipeline de datos y constantes
- `comparador/cla_excel.py` — escritura y formateo Excel (`write_hoja_10_salida` + lógica de `dfs_intermedios`)

#### Detalle: `comparador/tablas.py` — Fechas hardcodeadas — **7/10**

**Problema**: `filter_pivot_by_selected_dates` (línea 45) tiene fechas literales hardcodeadas:
```python
selected_dates = {
    "1M": date(2025, 2, 28),
    "3M": date(2024, 12, 31),
    ...
}
```
Esto hace que la función no sea reutilizable y requiera editar el código cada mes.

**Remediación**: Usar las funciones de `utiles/fechas.py` que ya existen:
```python
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

## 6. Otros Hallazgos

### 6.1 Ejecución de código a nivel de módulo en `eco/bcentral.py` — **8/10**

**Problema**: Líneas 18-55 ejecutan código al importar el módulo:
```python
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)  # Login al importar!
DATOS_JSON = read_bcentral_tickers()  # Lee JSON al importar!
```
Cualquier `import eco.bcentral` hace login al BCCh y lee archivos. Si `.env` no existe o las credenciales son inválidas, el import falla.

**Remediación**: Usar lazy initialization o un factory function.

```python
_bcch_client = None

def get_bcch_client():
    global _bcch_client
    if _bcch_client is None:
        env_variables = dotenv_values(".env")
        _bcch_client = bcchapi.Siete(
            usr=env_variables["BCCH_USER"],
            pwd=env_variables["BCCH_PASS"],
        )
    return _bcch_client
```

### 6.2 `download_fund_identification` variable `columnas` no usada — **3/10**

**Problema**: `cartolas/fund_identifica.py:127-139` define un dict `columnas` con el esquema deseado pero nunca lo aplica al DataFrame `df`. La función retorna `df` sin castear a esos tipos.

**Remediación**: Aplicar el esquema o eliminar la variable muerta.

### 6.3 Duplicación `cla_mensual.py` / `cla_mensual2.py` — **6/10**

**Problema**: `cla_mensual2.py` es casi idéntico a `cla_mensual.py` (misma estructura `main()`, mismos 3 pasos). La única diferencia es el `CUSTOM_CATEGORY_MAPPING` y la carpeta de salida.

**Remediación**: Unificar en un solo script con argumento CLI.

```python
# cla_mensual.py
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--custom-mapping", type=str, default=None,
                        help='JSON string, ej: \'{"9810": 17}\'')
    parser.add_argument("--output-folder", type=str, default="cla_mensual")
    args = parser.parse_args()

    custom_mapping = json.loads(args.custom_mapping) if args.custom_mapping else None
    if custom_mapping:
        custom_mapping = {int(k): v for k, v in custom_mapping.items()}
    ...
```

### 6.4 `retry_function` no preserva metadata con `@wraps` — **4/10**

**Problema**: `utiles/decorators.py:12` — `retry_function` y `exp_retry_function` no usan `@wraps(func)`, por lo que `__name__`, `__doc__`, etc. del wrapper reemplazan los de la función original. Esto rompe introspección y stacktraces.

**Remediación**:
```python
from functools import wraps

def retry_function(func, max_attempts=10, delay=10):
    @wraps(func)  # Agregar esta línea
    def wrapper(*args, **kwargs):
        ...
    return wrapper
```

### 6.5 Uso de `numpy` innecesario en `comparador/tablas.py` — **5/10**

**Problema**: `add_row_statistics` (línea 113) convierte a NumPy para calcular `nanmean`, `nanmax`, `nanmin` por fila. Polars puede hacer esto nativamente.

**Remediación**:
```python
def add_row_statistics(relative_returns: pl.DataFrame) -> pl.DataFrame:
    numeric_cols = [col for col in relative_returns.columns if col != "FECHA_INF"]
    return relative_returns.with_columns([
        pl.mean_horizontal(numeric_cols).alias("PROMEDIO_RENTABILIDAD"),
        pl.max_horizontal(numeric_cols).alias("MAX_RENTABILIDAD"),
        pl.min_horizontal(numeric_cols).alias("MIN_RENTABILIDAD"),
        pl.sum_horizontal([pl.col(c).is_not_null().cast(pl.UInt32) for c in numeric_cols]).alias("CANTIDAD_NO_NULOS"),
    ])
```

---

## 7. Resumen de Prioridades

| # | Hallazgo | Importancia | Esfuerzo |
|---|----------|-------------|----------|
| 1 | Dependencia circular `config.py` ↔ `file_tools.py` | 9/10 | Bajo |
| 2 | Código ejecutado al importar `eco/bcentral.py` | 8/10 | Medio |
| 3 | `generate_cla_data` demasiado compleja (175 líneas, CC~18) | 8/10 | Medio |
| 4 | `cla_monthly.py` mezcla pipeline + Excel (650 líneas) | 8/10 | Medio |
| 5 | Fechas hardcodeadas en `comparador/tablas.py` | 7/10 | Bajo |
| 6 | Cadenas de `.with_columns()` monolíticas en `soyfocus.py` y `merge.py` | 7/10 | Medio |
| 7 | `prepare_relevant_categories` complejidad ~14 | 7/10 | Medio |
| 8 | Duplicación `cla_mensual.py` / `cla_mensual2.py` | 6/10 | Bajo |
| 9 | `write_hoja_10_salida` patrón repetitivo (176 líneas) | 6/10 | Bajo |
| 10 | NumPy innecesario en `tablas.py` | 5/10 | Bajo |
| 11 | `retry_function` sin `@wraps` | 4/10 | Bajo |
| 12 | Variable `columnas` muerta en `fund_identifica.py` | 3/10 | Bajo |
