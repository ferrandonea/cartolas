# Crítica del paquete Cartolas

## Resumen ejecutivo

El proyecto cumple bien su objetivo funcional: descarga, transforma y analiza cartolas de fondos mutuos chilenos. El uso de Polars LazyFrames es generalmente idiomático y la estructura modular es razonable. Sin embargo, hay problemas significativos de deuda técnica, duplicación de código, y prácticas que dificultan el mantenimiento a largo plazo.

---

## 1. Problemas críticos

### 1.1 Duplicación masiva en comparador/

`cla_monthly_new_conservador.py` es una **copia de 607 líneas** de `cla_monthly.py` con **una sola línea diferente** (línea 40: cambia la categoría ELMER). Además:

- `add_cumulative_returns()` está copiada idéntica en **4 archivos**: `tablas.py`, `cla_monthly.py`, `cla_monthly_new_conservador.py`, `cla_new.py`
- `generate_cla_dates()` está copiada en **3 archivos**
- `cla_new.py` es un subconjunto truncado de `cla_monthly.py` (borrador que quedó)

**Impacto:** Cualquier fix o mejora hay que replicarlo manualmente en múltiples archivos.

### 1.2 Side-effects en tiempo de importación

`eco/bcentral.py` ejecuta al hacer `import`:
- Login a la API del Banco Central (`bcchapi.Siete(usr=..., pwd=...)`)
- Lectura de `.env`
- Lectura de un archivo JSON
- Cálculo de `LAST_DATE`

Cualquier módulo que importe `eco.bcentral` dispara una conexión de red. Si las credenciales son inválidas o no hay `.env`, el import falla con un error críptico.

Otros side-effects en importación: `cartolas/config.py` genera un hash aleatorio y calcula `FECHA_MAXIMA`; `comparador/elmer.py` calcula timestamps.

### 1.3 Dependencia circular

```
utiles.file_tools → cartolas.config (importa CARTOLAS_FOLDER)
cartolas.config   → utiles.file_tools (importa generate_hash_image_name)
```

Ambos archivos usan imports diferidos a mitad de archivo con `# noqa: E402`. Es un code smell arquitectónico.

### 1.4 Fechas hardcodeadas en tablas.py

`filter_pivot_by_selected_dates()` tiene fechas absolutas como `date(2025, 2, 28)`, `date(2024, 12, 31)`. La función es inútil para cualquier otro mes. La lógica dinámica correcta está **comentada** pero no se usa.

---

## 2. Problemas de diseño

### 2.1 Funciones que mezclan cálculo con persistencia

Las 3 funciones principales de `soyfocus.py` (`create_soyfocus_parquet`, `soy_focus_by_run`, `create_tac_report`) calculan transformaciones Y escriben a disco. Imposible usar las transformaciones sin generar archivos Parquet.

### 2.2 Funciones excesivamente largas

| Función | Archivo | Líneas | Problema |
|---------|---------|--------|----------|
| `write_hoja_10_salida` | `cla_monthly.py` | 175 | Mezcla formatos Excel, datos y escritura celda por celda |
| `generate_cla_data` | `cla_monthly.py` | 137 | Mezcla lógica de negocio con exportación Excel |
| `prepare_cartolas_in_pesos` | `merge.py` | 122 | Cadena de 15+ `.with_columns()` |
| `create_soyfocus_parquet` | `soyfocus.py` | 100 | 13 llamadas consecutivas a `.with_columns()` |

### 2.3 Monkey-patching

`cla_monthly_custom.py` reemplaza temporalmente `merge_module.merge_cartolas_with_categories` con un wrapper en runtime. Frágil, no thread-safe, difícil de razonar.

### 2.4 Sin API pública

Todos los `__init__.py` están vacíos. El paquete no define qué es público y qué es interno. No hay `__all__`.

---

## 3. Calidad de código

### 3.1 Sin logging

Todo el proyecto usa `print()`. No hay `import logging`. El patrón `print(...) if verbose else None` se repite decenas de veces — es un anti-patrón (la expresión ternaria evalúa `None` innecesariamente).

### 3.2 Type hints incorrectos

| Archivo | Problema |
|---------|----------|
| `soyfocus.py:16` | `SOYFOCUS_RUNS: list[str]` pero las keys de `SOYFOCUS_FUNDS` son `int` |
| `elmer.py:242` | `last_elmer_data_as_polars` declara retornar `list[dict]`, retorna `pl.LazyFrame` |
| `bcentral.py:59` | `tickers: str` pero recibe `list[str]` |
| `fund_identifica.py:123` | `download_fund_identification() -> str` pero retorna `pl.DataFrame` |
| `soyfocus.py` | Mezcla `list[str] | None` (moderno) con `Optional[List[str]]` (legacy) |

### 3.3 Código muerto

- `download.py:main()` — docstring dice "ESTO ES TEMPORAL", fechas de 2021
- `fund_identifica.py:cmf_to_pl()` — duplica `cmf_text_to_df()`, no retorna nada
- `fund_identifica.py:127-139` — diccionario `columnas` definido pero nunca usado
- `cla_monthly.py:23` — `import numpy as np` nunca usado
- `cartolas/economy.py` — no lo importa ningún otro archivo del paquete

### 3.4 Uso de APIs deprecadas de Polars

- `pl.Utf8` en `transform.py:55` y `fund_identifica.py` — debería ser `pl.String`
- `pl.count("SERIE")` en `cla_monthly.py:247` — deprecado

### 3.5 Credenciales y datos sensibles

- `config.py:116-120`: email personal hardcodeado
- `economy.py`: credenciales BCCh cargadas como globales de módulo
- `.env` con path relativo — falla si se ejecuta desde otro directorio
- Paths personales hardcodeados en bloques `__main__` de `transform.py`, `read.py`, `soyfocus.py`

---

## 4. Anti-patrones de Polars

| Anti-patrón | Ubicación | Alternativa |
|-------------|-----------|-------------|
| Conversión a numpy para estadísticas por fila | `tablas.py:150-158` | `pl.mean_horizontal()`, `pl.max_horizontal()` |
| `map_elements` con lambda Python | `cla_monthly.py:386` | `pl.col().replace()` con diccionario |
| Loop `for` sobre columnas | `fund_identifica.py:103-108` | Un solo `.with_columns([...])` |
| `.collect()` múltiples veces sobre mismo LazyFrame | `merge.py:237-239` | Materializar una vez, reutilizar |
| 13 `.with_columns()` consecutivos con expresiones independientes | `soyfocus.py` | Agrupar expresiones independientes en un solo `.with_columns()` |

---

## 5. Configuración del proyecto

### 5.1 pyproject.toml incompleto

- Versión desincronizada: `pyproject.toml` dice 0.3.0, `CHANGELOG.md` dice 0.4.0
- Sin `[tool.ruff]`, `[tool.pytest]`, `[build-system]`, `[project.scripts]`
- Sin `[project.optional-dependencies]` para separar deps de desarrollo

### 5.2 Dependencias problemáticas

- **notebook, jupyterlab, ipykernel, matplotlib** son de desarrollo pero están en dependencies de producción
- **pandas** solo se usa para exportar a Excel (`df.to_pandas()`) — reemplazable con `polars.DataFrame.write_excel()`
- **numpy** se importa pero no se usa en `cla_monthly.py`
- **captchapass** sin version pin (apunta a git sin tag)

### 5.3 Sin linting ni tests

No hay configuración de ruff, ni pytest, ni mypy, ni pre-commit. No existe carpeta de tests.

### 5.4 .gitignore

- No ignora `cla_mensual2/` (puede contener ~1.4GB de .xlsx)
- No ignora `*.csv` en root (hay 3 CSVs generados sueltos)
- No ignora `~$*.xlsx` (locks temporales de Excel)
- Tiene secciones irrelevantes (Django, Flask, Scrapy, Celery, SageMath)

---

## 6. Estructura y archivos sobrantes

### Scripts root que deberían consolidarse

| Archivo | Estado |
|---------|--------|
| `actualiza_parquet.py` | Legítimo |
| `actualiza_parquet_year.py` | Legítimo (podría unificarse con el anterior vía argumento) |
| `cla_mensual.py` | Legítimo |
| `cla_mensual copy.py` | **Borrar** — copia literal con 1 import diferente |
| `cla_mensual2.py` | **Borrar o consolidar** — variante con custom mapping |
| `soyfocus.py` | **Borrar** — script one-off de 14 líneas |
| `resumen_apv.py` | **Borrar** — script one-off de 22 líneas con print hardcodeado |

### Archivos generados en root

`apv.csv`, `uf.csv`, `soyfocus.csv` — no deberían estar en el repo.

### Directorio ejercicios/

Contiene `vivienda.py` — sin relación con el proyecto.

---

## 7. Lo que está bien hecho

- **Polars LazyFrames** usado consistentemente en el pipeline principal (scan → transform → collect)
- **`polars_utils.py`** es el archivo mejor escrito: funciones cortas, docstrings completas, type hints correctos, código idiomático
- **`utiles/decorators.py`** tiene type hints con generics (`TypeVar T`) bien implementados
- **Separación modular** razonable: cartolas (core), comparador (análisis), eco (datos económicos), utiles
- **Configuración centralizada** en `config.py` con esquema tipado estricto
- **CLAUDE.md** es el documento más preciso y útil del proyecto
- **Actualización incremental** (solo descarga fechas faltantes) es un buen diseño
