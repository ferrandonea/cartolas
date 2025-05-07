# Changelog

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
- Dockerizar el proyecto
- Dejar todas las funciones en un mismo idioma