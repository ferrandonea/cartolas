# Changelog

## 0.6.0
### Agregado
- **CLI unificado con Click** (E3): nuevo `cli.py` con entry point `cartolas` registrado en `pyproject.toml`
  - `cartolas update` — actualización por año (default) + BCCh
  - `cartolas update --all` — actualización monolítica + BCCh
  - `cartolas report cla [--output] [--no-update]` — reporte CLA mensual
  - `cartolas report soyfocus` — genera parquets SoyFocus + TAC
  - `cartolas report apv [--output]` — exporta CSV APV + UF
- **67 tests unitarios** (E1): fechas, polars_utils, transform, merge, cla_monthly
- **Logging centralizado** (E4): `setup_logging()` con nivel configurable vía `CARTOLAS_LOG_LEVEL`, 36 prints migrados a logging
- **API pública por paquete** (E5): `__init__.py` con re-exports en `cartolas/`, `comparador/` y `utiles/`
- Build system con hatchling para registrar entry points via `uv`
- Validación de credenciales BCCh: error claro si `BCCH_USER` o `BCCH_PASS` faltan o están vacíos
- Creación automática de directorios del scraper (`temp/`, `errors/`, `correct/`, `txt/`) (F1)
- `apv.csv` y `uf.csv` agregados a `.gitignore`

### Cambiado
- **Reportes livianos** (E2): Excel CLA solo con hoja "Salida" (10KB/5seg vs 90MB/6min). `excel_steps` deprecated con warning
- **Import circular eliminado** (E6): `file_tools.py` ya no hace late-import de `config.CARTOLAS_FOLDER`
- **Retry con backoff en Elmer** (M2): reemplaza retry simple por backoff exponencial con logging
- **Validación de descarga CMF** (M3): retry simplificado en `download.py`
- **Lazy-load BCCh** (M1): `lru_cache` en cliente y credenciales
- **Update consolidado** (M7): `update.py` con parámetro `by_year`, `update_by_year.py` como wrapper
- **Fechas parametrizadas** (M5): eliminadas fechas hardcodeadas en `tablas.py` y `resumen_apv.py`
- **Email a `.env`** (M6): credenciales de email movidas de `config.py` a `.env`
- README reescrito: instalación, comandos con ejemplos, variables de entorno, estructura del proyecto

### Eliminado
- Scripts raíz reemplazados por CLI: `actualiza_parquet.py`, `actualiza_parquet_year.py`, `cla_mensual.py`, `soyfocus.py`, `resumen_apv.py`
- Código muerto: `economy.py`, `cla_mensual copy.py`, `cla_monthly_new_conservador.py`, `datostablacla_new.xlsx` (Q1-Q3)
- `listas.py` absorbido en `merge.py` (Q7)
- Debug code en `fund_identifica.py` y `tablas.py` (Q5)

### Corregido
- Firma `-> str` a `-> pl.DataFrame` en `fund_identifica.py` (Q6)
- `add_cumulative_returns()` movido a `utiles/polars_utils.py` (Q4)
- `filter_pivot_by_selected_dates` retorna `dict[str, pl.DataFrame]` para preservar períodos duplicados en enero

### Dependencias
- Agregada `click>=8.1.0`
- Agregada `hatchling` como build backend

## 0.5.0
### Cambiado
- Migración de captchapass (TensorFlow ~600MB) a ONNX Runtime (~70MB)
- Nuevo módulo `cartolas/captcha.py` reemplaza dependencia externa `captchapass`
- Modelo OCR convertido de Keras a ONNX (`cartolas/modelo/ocr_model.onnx`)
- Eliminada dependencia de TensorFlow y 80+ dependencias transitivas
- Compatible con Python 3.11+ (antes requería 3.11.9+, limitado por TensorFlow)

## 0.4.1
### Corregido
- Descarga CMF: usa `evaluate()` en campos de fecha para evitar interferencia de datepicker
- Descarga CMF: corrige patrón `expect_download` (acceso a `.value` fuera del `with`)
- Descarga CMF: timeout dedicado de 60s para descargas (evita bloqueo de 8+ min en captchas fallidos)
- Custom mapping CLA: actualiza NUM_CATEGORIA y usa Elmer como fuente de nombres
- Filtro Elmer por retail en validación de custom_mapping

### Mejorado
- Calidad de código (CAL-01, CAL-02, CAL-05, CAL-08)
- Fechas dinámicas y resiliencia en cálculos (BUG-01, RES-02, RES-03)
- Seguridad en download, elmer, fund_identifica y config (SEG-02..05, RES-01, RES-05)
- Decoradores y utilidades (RES-04, CAL-07, CAL-06)
- Correcciones en bcentral (BUG-02, SEG-01)
- Consolidación de lógica custom_mapping en cla_monthly, eliminación de archivos duplicados

### Agregado
- Documentación de auditorías de código y seguridad (`audits/`)
- CLAUDE.md con referencia del proyecto para Claude Code

## 0.4.0
### Agregado
- Documentación completa en español del proyecto (DOCUMENTACION.md)
- Nuevo script `resumen_apv.py` para análisis APV
- Mejoras en documentación y estructura del script `cla_mensual.py`
- Mejoras en docstrings de `comparador/new_new_cla.py`
- Actualizaciones de configuración en `pyproject.toml` y `uv.lock`

## 0.3.0
### Agregado
- Mejora en estructura de carpetas
- Nueva funcionalidad para guardar los archivos de cartolas por años
- Funcionalidad para output de CLA

## 0.2.1
### Agregado
- Módulo de soyfocus para los datos de los fondos administrados por nosotros.

## 0.2.0
Es en la práctica la primera versión estable
### Agregado
- Funciones para bajar los archivos desde la CMF y guardarlos en un archivo parquet

# TODO
- Ordenar los archivos de configuración
- Analizar si el parquet de cartolas se puede subir a Azure
- Hoy no se guardan los nombre de las administradoras por que ocupan demasiado espacio, eso se podría arreglar con otro parquet y un join.
- Comparador de fondos
- Dejar todas las funciones en un mismo idioma
