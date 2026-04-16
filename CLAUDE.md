# CLAUDE.md

## Comandos de desarrollo

```bash
# Instalar dependencias
uv sync

# Scripts principales (ejecutar desde la raíz del proyecto)
uv run python actualiza_parquet.py      # Actualización diaria: descarga CMF + actualiza BCCh
uv run python actualiza_parquet_year.py  # Actualización por año (datos históricos)
uv run python cla_mensual.py            # Genera reporte CLA mensual (Excel)
uv run python soyfocus.py               # Análisis de fondos SoyFocus
uv run python resumen_apv.py            # Resumen APV

# Linting (no hay configuración de ruff en pyproject.toml aún)
uv run ruff check .
uv run ruff format .
```

## Arquitectura

El proyecto analiza fondos mutuos chilenos descargando cartolas diarias desde la CMF, enriqueciéndolas con datos del Banco Central y El Mercurio Inversiones.

### Paradigma

- **Polars LazyFrames** en todo el pipeline. Se usa `pl.scan_parquet()` / `pl.scan_csv()` y se encadenan operaciones lazy. Solo se materializa con `.collect()` al final.
- **Paradigma funcional**: funciones puras que reciben y retornan LazyFrames.
- **Configuración centralizada** en `cartolas/config.py`: rutas, URLs, esquema de datos, constantes.


## Patrones clave

- **Decoradores de retry** (`utiles/decorators.py`): `@retry_function(max_attempts, delay)` para reintentos con delay fijo, `@exp_retry_function(max_attempts)` para backoff exponencial (2^n seg). Usados en descarga CMF.
- **@timer**: Mide tiempo de ejecución. Aplicado en funciones de análisis pesadas.
- **Esquema estricto**: `config.SCHEMA` define tipos Polars para todas las columnas. Se aplica en transformación.
- **Fondos SoyFocus**: RUN_FM 9809 (Moderado), 9810 (Conservador), 9811 (Arriesgado). Definidos en `config.SOYFOCUS_FUNDS`.

## Datos

- **Almacenamiento principal**: Parquet en `cartolas/data/parquet/` (~750MB `cartolas.parquet`)
- **Datos por año**: `cartolas/data/yearly/cartolas_YYYY.parquet` (2007-2026)
- **BCCh**: `cartolas/data/bcch/bcch.parquet` + `bcentral_tickers.json`
- **El Mercurio**: JSON cacheado en `cartolas/data/elmer/`
- **TXT descargados**: `cartolas/data/txt/` (temporales, se limpian tras transformación)
- **Reportes Excel**: generados por CLA mensual en `cartolas/data/excel/`

## Convenciones

- **Idioma mixto**: código en español e inglés. Nombres de columnas en español/mayúsculas (vienen de CMF). Variables y funciones en inglés o español según contexto.
- **Gestor de paquetes**: `uv` (no pip). Siempre usar `uv run`, `uv sync`, `uv add`.
- **Python**: >=3.11.9
- **Sin tests formales** actualmente.
- **Variables de entorno**: `.env` con credenciales de BCCh (`BCCH_USER`, `BCCH_PASS`) y SendGrid.

# Commit
Después de cada commit me tienes que decir su identificador