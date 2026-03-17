# Changelog

## 0.5.0
### Cambiado
- Migración de captchapass (TensorFlow ~600MB) a ONNX Runtime (~70MB)
- Nuevo módulo `cartolas/captcha.py` reemplaza dependencia externa `captchapass`
- Modelo OCR convertido de Keras a ONNX (`cartolas/modelo/ocr_model.onnx`)
- Eliminada dependencia de TensorFlow y 80+ dependencias transitivas
- Compatible con Python 3.12+ (antes solo 3.11.9+)

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
