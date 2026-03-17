# Cartolas

Análisis de fondos mutuos chilenos. Descarga cartolas diarias desde la CMF, enriquece con datos del Banco Central (UF, dólar, TPM) y categorización de El Mercurio Inversiones, y genera reportes comparativos de rentabilidad.

## Requisitos

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) como gestor de paquetes
- Playwright (se instala con `uv sync`, requiere `playwright install chromium`)
- Credenciales API del Banco Central de Chile

## Instalación

```bash
git clone <repo-url> && cd cartolas
uv sync
uv run playwright install chromium
```

Crear un archivo `.env` en la raíz del proyecto:

```env
BCCH_USER=tu_email@ejemplo.com
BCCH_PASS=tu_password
```

## Uso

```bash
# Actualización por año (default): descarga CMF + actualiza BCCh
cartolas update

# Actualización monolítica (parquet único)
cartolas update --all

# Reporte CLA mensual (actualiza datos + genera Excel)
cartolas report cla

# Reporte CLA sin actualizar datos
cartolas report cla --no-update

# Reporte CLA con ruta personalizada
cartolas report cla --output reportes/marzo.xlsx

# Genera parquets SoyFocus (detalle, por RUN y TAC)
cartolas report soyfocus

# Exporta datos APV + UF del último año a CSV
cartolas report apv
cartolas report apv --output mi_apv.csv
```

## Variables de entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `BCCH_USER` | Email registrado en API Banco Central | Sí |
| `BCCH_PASS` | Contraseña API Banco Central | Sí |
| `CARTOLAS_LOG_LEVEL` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`). Default: `INFO` | No |

## Estructura del proyecto

```
cartolas/       # Core: descarga, transformación, lectura y guardado de cartolas
comparador/     # Análisis CLA mensual, merge con categorías El Mercurio
eco/            # Integración con Banco Central (bcchapi)
utiles/         # Decoradores (@retry, @timer), utilidades de fechas y archivos
cli.py          # CLI unificado (entry point)
```

| Paquete | Qué hace |
|---------|----------|
| `cartolas` | Pipeline completo: scraping CMF con Playwright → transformación a Polars LazyFrame → guardado en Parquet |
| `comparador` | Genera reportes CLA mensuales cruzando cartolas con datos BCCh y categorización El Mercurio |
| `eco` | Descarga y actualiza series económicas del Banco Central (UF, dólar, euro, oro, TPM, UTM) |
| `utiles` | Decoradores de retry/timer, funciones de fechas, manejo de archivos, configuración de logging |
