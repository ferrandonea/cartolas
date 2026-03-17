# Plan de mejoras — Cartolas

## Diagnóstico

### Propósito

Sistema de análisis financiero para **fondos mutuos chilenos**, orientado a los fondos **SoyFocus** (Moderado/Conservador/Arriesgado). Pipeline completo: scraping CMF con resolución de captcha → transformación a Parquet → enriquecimiento con datos BCCh y categorización El Mercurio → generación de reportes CLA mensuales en Excel.

### Corazón del sistema

1. **`cartolas/config.py`** — Todo parte de aquí: rutas, esquema, constantes
2. **`cartolas/download.py` + `captcha.py`** — Scraping con Playwright + ONNX, la parte más técnicamente compleja
3. **`comparador/cla_monthly.py`** (606 líneas) — Generador de reportes CLA, lógica de negocio más densa
4. **`comparador/merge.py`** — Join entre cartolas, BCCh y categorías Elmer; si falla, todo el análisis cae
5. **`cartolas/soyfocus.py`** (429 líneas) — Cálculos financieros (TAC, TDC, rentabilidades)

---

## Estado actual

### Quick Wins — COMPLETADOS

| # | Mejora | Estado |
|---|--------|--------|
| Q1 | Eliminar `economy.py` (código muerto) | **DONE** |
| Q2 | Eliminar archivos huérfanos (`cla_mensual copy.py`, `datostablacla_new.xlsx`) | **DONE** |
| Q3 | Borrar `cla_monthly_new_conservador.py` (95% copy-paste) | **DONE** |
| Q4 | Mover `add_cumulative_returns()` a `utiles/polars_utils.py` | **DONE** |
| Q5 | Limpiar código de debug en `fund_identifica.py` y `tablas.py` | **DONE** |
| Q6 | Corregir firma `-> str` a `-> pl.DataFrame` en `fund_identifica.py` | **DONE** |
| Q7 | Absorber `listas.py` en `merge.py` (inline `reduce(mul, ...)`) | **DONE** |

### Mejoras medianas — COMPLETADOS (M4 descartado)

| # | Mejora | Estado |
|---|--------|--------|
| M1 | Lazy-load de BCCh con `lru_cache` | **DONE** |
| M2 | Retry con backoff + logging en `elmer.py` | **DONE** |
| M3 | Validación de descarga + retry simplificado en `download.py` | **DONE** |
| M4 | Eliminar mezcla Pandas/NumPy | **DESCARTADO** (ver decisiones) |
| M5 | Parametrizar fechas hardcodeadas en `tablas.py` y `resumen_apv.py` | **DONE** |
| M6 | Email a `.env` en `config.py` | **DONE** |
| M7 | Consolidar `update.py` y `update_by_year.py` | **DONE** |

### Cambios estructurales

| # | Mejora | Impacto | Esfuerzo | Alcance | Estado |
|---|--------|---------|----------|---------|--------|
| E1 | **Tests**: 67 tests unitarios (fechas, polars_utils, transform, merge, cla_monthly) | Muy alto | 2-3 días | `tests/` (5 archivos) | **DONE** |
| E2 | **Reportes livianos**: Excel solo con hoja "Salida" (10KB/5seg vs 90MB/6min). Eliminadas hojas 1-9, `dfs_intermedios`, `excel_steps` (deprecated con warning) | Alto | 1 día | `comparador/cla_monthly.py`, callers | **DONE** |
| E3 | **CLI unificado**: reemplazar 5 scripts raíz sueltos por un CLI con `click` o `typer` (`cartolas update`, `cartolas report cla`, etc.) | Medio | 1 día | Scripts raíz + nuevo `cli.py` | PENDIENTE |
| E4 | **Logging**: reemplazar `print()` en decoradores y pipeline por `logging` con niveles configurables | Medio | 0.5 día | Todos los módulos | **DONE** |
| E5 | **`__init__.py` con exports**: definir API pública de cada paquete para simplificar imports | Bajo | 2h | 4 `__init__.py` | PENDIENTE |
| E6 | **Resolver imports circulares**: eliminar el late-import de `file_tools` en `config.py` reestructurando dependencias | Medio | 3h | `config.py`, `file_tools.py` | PENDIENTE |

### Fixes fuera de roadmap

| Fix | Descripción | Estado |
|-----|-------------|--------|
| F1 | **Creación automática de directorios del scraper**: `temp/`, `errors/`, `correct/`, `txt/` no se creaban antes de usarse en `download.py`, causando fallos en máquinas nuevas | **DONE** |

---

## Decisiones importantes

### M4 revertido: NumPy correcto para semántica NaN

`tablas.py:add_row_statistics()` usa `np.nanmean`/`np.nanmax`/`np.nanmin`/`np.isnan` para calcular estadísticas por fila ignorando NaN. Se intentó reemplazar con `pl.*_horizontal()` pero la semántica de NaN es diferente en Polars, produciendo una regresión funcional. NumPy se queda — su uso está justificado aquí. `bcentral.py` tampoco se tocó porque Pandas es dependencia de `bcchapi`, no nuestra.

### filter_pivot_by_selected_dates retorna dict[str, pl.DataFrame]

En enero, los períodos "1M" y "YTD" resuelven a la misma fecha (31 dic). Si se filtra con `is_in()` sobre una lista de fechas, el duplicado colapsa y se pierde un período. La función ahora retorna `{label: DataFrame}` para preservar todos los períodos sin contaminar el esquema con columnas extra (que romperían `calculate_relative_returns` y `add_row_statistics`, que asumen toda columna no-FECHA_INF es numérica).

### update_by_year.py conservado como wrapper

La lógica de update se consolidó en `update.py` con parámetro `by_year`. `update_by_year.py` se mantiene como wrapper delgado que llama `update_parquet(by_year=True)` para no romper callers externos (`cla_mensual.py`, `actualiza_parquet_year.py`).

---

## Próxima sesión: E6 (Resolver imports circulares)

## Orden sugerido para pendientes

1. **E6** — Resolver imports circulares
3. **E5** — `__init__.py` con exports
4. **E3** — CLI unificado
