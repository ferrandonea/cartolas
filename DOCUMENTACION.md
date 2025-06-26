# Documentación Completa - Proyecto Cartolas

## 🏛️ Resumen Ejecutivo

**Cartolas** es un sistema integral de análisis financiero para fondos mutuos chilenos, especializado en los fondos **SoyFocus**. El proyecto automatiza la descarga, procesamiento y análisis de datos de la **CMF (Comisión para el Mercado Financiero)**, proporcionando análisis comparativo, cálculo de rentabilidades, métricas de costos regulatorios y reportes automatizados.

### Características Principales
- ✅ Descarga automatizada de cartolas diarias desde CMF
- ✅ Análisis comparativo mensual (CLA - Comparative Long Analysis)
- ✅ Cálculo de métricas regulatorias (TAC, TDC)
- ✅ Integración con datos económicos del Banco Central
- ✅ Análisis especializado de fondos SoyFocus
- ✅ Generación de reportes Excel automatizados

---

## 📁 Estructura del Proyecto

```
cartolas/
├── cartolas/                 # Módulo principal
│   ├── data/                # Datos almacenados
│   │   ├── parquet/         # Archivos de datos principales
│   │   ├── yearly/          # Datos organizados por año
│   │   ├── bcch/            # Datos del Banco Central
│   │   ├── elmer/           # Datos de El Mercurio
│   │   └── images/          # Capturas de pantalla (debug)
│   ├── download.py          # Descarga de cartolas
│   ├── transform.py         # Transformación de datos
│   ├── read.py              # Lectura de datos
│   ├── save.py              # Guardado optimizado
│   ├── update.py            # Actualización incremental
│   └── soyfocus.py          # Análisis SoyFocus
├── comparador/              # Sistema de comparación
│   ├── cla_monthly.py       # Análisis CLA mensual
│   ├── elmer.py             # Integración El Mercurio
│   ├── merge.py             # Fusión de datos
│   └── tablas.py            # Análisis tabular
├── eco/                     # Módulos económicos
│   └── bcentral.py          # Integración Banco Central
├── utiles/                  # Utilidades comunes
└── scripts principales...
```

---

## 🚀 Instalación y Configuración

### Requisitos
- Python >= 3.11.9
- [uv](https://github.com/astral-sh/uv) (gestor de paquetes)

### Instalación
```bash
# Clonar el repositorio
git clone [url-del-repo]
cd cartolas

# Instalar dependencias
uv sync

# Configurar variables de entorno (crear .env)
SENDGRID_API_KEY=tu_api_key_sendgrid
BCCh_USER=tu_usuario_banco_central
BCCh_PASS=tu_password_banco_central
```

### Configuración Inicial
El archivo `cartolas/config.py` contiene toda la configuración del sistema:
- URLs de descarga
- Rutas de archivos
- Esquemas de datos
- Configuración de correos

---

## 📊 Módulos Principales

### 1. **Descarga de Datos (`cartolas/download.py`)**

**Propósito**: Automatiza la descarga de cartolas desde el sitio web de la CMF.

```python
from cartolas.download import get_cartola_from_cmf
from datetime import date

# Descargar cartolas para un rango de fechas
get_cartola_from_cmf(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 1, 31),
    headless=True  # Ejecutar sin interfaz gráfica
)
```

**Características**:
- ✅ Resolución automática de captchas
- ✅ Manejo de límites de 30 días por descarga
- ✅ Sistema de reintentos exponenciales
- ✅ Descarga en paralelo cuando es posible

### 2. **Transformación de Datos (`cartolas/transform.py`)**

**Propósito**: Convierte archivos TXT de cartolas a formato estructurado Parquet.

```python
from cartolas.transform import transform_cartola_folder

# Transformar todos los archivos TXT de una carpeta
transform_cartola_folder(
    source_folder="ruta/a/txt",
    target_file="ruta/salida.parquet"
)
```

**Transformaciones realizadas**:
- Conversión de fechas (YYYYMMDD → Date)
- Mapeo de booleanos (S/N → True/False)
- Aplicación de esquemas tipados
- Creación de columnas derivadas

### 3. **Análisis SoyFocus (`cartolas/soyfocus.py`)**

**Propósito**: Análisis especializado de los fondos SoyFocus con cálculos financieros avanzados.

**Fondos SoyFocus**:
- **9809**: Moderado
- **9810**: Conservador  
- **9811**: Arriesgado

```python
from cartolas.soyfocus import create_soyfocus_parquet

# Generar análisis completo de SoyFocus
create_soyfocus_parquet()
```

**Métricas calculadas**:
- 📈 Rentabilidades diarias y acumuladas
- 💰 Patrimonio ajustado según circular CMF
- 📊 Flujos netos monetarios
- 💸 Gastos totales (afectos + no afectos)
- 🎯 TAC (Tasa Anual de Costos)
- 📉 TDC (Tasa Diaria de Costos)

### 4. **Sistema de Comparación (`comparador/`)**

#### Análisis CLA Mensual (`cla_monthly.py`)
**Propósito**: Genera análisis comparativo mensual de rentabilidades.

```python
from comparador.cla_monthly import generate_cla_data

# Generar análisis CLA para una fecha específica
generate_cla_data(
    reference_date=date(2024, 12, 31),
    output_file="cla_202412.xlsx"
)
```

**Períodos de análisis**:
- 1 mes, 3 meses, 6 meses
- 1 año, 3 años, 5 años

**Métricas incluidas**:
- Rentabilidades absolutas y relativas
- Rankings por categoría
- Comparación vs fondos SoyFocus
- Estadísticas por categoría (promedio, máximo, mínimo)

#### Integración El Mercurio (`elmer.py`)
**Propósito**: Obtiene categorización de fondos desde El Mercurio Inversiones.

```python
from comparador.elmer import get_all_elmer_data

# Descargar datos de todas las categorías
data = get_all_elmer_data()
```

### 5. **Integración Banco Central (`eco/bcentral.py`)**

**Propósito**: Descarga y mantiene actualizados datos económicos del BCCh.

```python
from eco.bcentral import update_bcch_parquet

# Actualizar datos del Banco Central
update_bcch_parquet()
```

**Series económicas descargadas**:
- 💵 Dólar observado
- 💶 Euro
- 🏠 UF (Unidad de Fomento)
- 📊 Otras series relevantes

---

## 🔄 Flujos de Trabajo

### A. Flujo de Actualización Diaria

```bash
# Ejecutar actualización diaria completa
uv run python actualiza_parquet.py
```

**Proceso**:
1. ✅ Verificar fechas faltantes en parquet
2. ✅ Descargar cartolas faltantes de CMF
3. ✅ Transformar datos TXT a formato estructurado
4. ✅ Actualizar archivo parquet consolidado
5. ✅ Actualizar datos económicos BCCh
6. ✅ Limpiar archivos temporales

### B. Flujo de Análisis CLA Mensual

```bash
# Generar reporte CLA mensual
uv run python cla_mensual.py
```

**Proceso**:
1. ✅ Actualizar datos de fondos y económicos
2. ✅ Cargar categorías desde El Mercurio
3. ✅ Convertir valores a pesos chilenos
4. ✅ Calcular rentabilidades por período
5. ✅ Comparar con fondos SoyFocus
6. ✅ Generar reporte Excel con formato visual

### C. Flujo de Reporte APV

```bash
# Generar resumen APV
uv run python resumen_apv.py
```

---

## 📈 Datos y Esquemas

### Esquema Principal de Cartolas

El esquema de datos está definido en `config.py`:

```python
SCHEMA = {
    "RUN_ADM": pl.UInt32,           # RUN administradora
    "NOM_ADM": pl.String,           # Nombre administradora
    "RUN_FM": pl.UInt16,            # RUN fondo mutuo
    "FECHA_INF": pl.String,         # Fecha información
    "ACTIVO_TOT": pl.Float64,       # Activo total
    "MONEDA": pl.String,            # Moneda (CLP, USD, EUR)
    "SERIE": pl.String,             # Serie del fondo
    "VALOR_CUOTA": pl.Float64,      # Valor de la cuota
    "PATRIMONIO_NETO": pl.Float64,  # Patrimonio neto
    "NUM_PARTICIPES": pl.UInt32,    # Número de partícipes
    # ... más campos
}
```

### Tipos de Archivos Generados

- **📊 `.parquet`**: Datos principales (formato columnar eficiente)
- **📋 `.xlsx`**: Reportes CLA con formato visual
- **📄 `.csv`**: Exportaciones para análisis externos
- **🖼️ `.png`**: Capturas de debug de descarga

---

## 🛠️ Scripts de Uso Común

### Actualización de Datos

```bash
# Actualización diaria básica
uv run python actualiza_parquet.py

# Actualización por año (para datos históricos)
uv run python actualiza_parquet_year.py
```

### Generación de Reportes

```bash
# Reporte CLA mensual
uv run python cla_mensual.py

# Resumen APV
uv run python resumen_apv.py
```

### Uso Programático

```python
# Ejemplo: Análisis personalizado de rentabilidades
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.config import PARQUET_FILE_PATH
import polars as pl

# Cargar datos
df = read_parquet_cartolas_lazy(PARQUET_FILE_PATH)

# Filtrar fondos SoyFocus del último año
soyfocus_data = (
    df.filter(
        (pl.col("RUN_FM").is_in([9809, 9810, 9811])) &
        (pl.col("FECHA_INF") >= "2024-01-01")
    )
    .collect()
)

print(soyfocus_data.head())
```

---

## ⚙️ Configuración Avanzada

### Variables de Entorno (`.env`)

```bash
# API SendGrid para envío de correos
SENDGRID_API_KEY=SG.xxxxx

# Credenciales Banco Central
BCCh_USER=tu_usuario
BCCh_PASS=tu_password

# Configuración opcional
VERBOSE=true
HEADLESS=true
```

### Personalización de Configuración

Editar `cartolas/config.py` para:
- Cambiar rutas de archivos
- Modificar timeouts de descarga
- Ajustar esquemas de datos
- Configurar destinatarios de correos

---

## 🔍 Solución de Problemas Comunes

### Error de Descarga de CMF
```bash
# Verificar conexión y configuración
python -c "from cartolas.download import get_cartola_from_cmf; print('OK')"
```

### Problemas con Captcha
- El sistema usa `captchapass` para resolver captchas automáticamente
- Si falla, verificar la librería esté actualizada

### Datos Faltantes
```python
# Verificar qué fechas faltan
from cartolas.update import update_parquet
update_parquet()  # Detecta y descarga automáticamente
```

### Archivos Corruptos
```bash
# Regenerar desde archivos TXT
uv run python -c "from cartolas.transform import transform_cartola_folder; transform_cartola_folder()"
```

---

## 📞 Soporte y Contacto

Para consultas técnicas o problemas:
- **Email**: francisco@soyfocus.com
- **Repositorio**: [GitHub del proyecto]

### Contribuciones

1. Fork del repositorio
2. Crear rama feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Agrega nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

---

## 📚 Recursos Adicionales

### Documentación Técnica
- **Polars**: Framework de análisis de datos usado
- **Playwright**: Automatización web
- **CMF**: Sitio oficial de cartolas
- **BCCh API**: Documentación del Banco Central

### Archivos de Interés
- `CHANGELOG.md`: Historial de cambios
- `pyproject.toml`: Configuración del proyecto
- `uv.lock`: Dependencias exactas

---

*Documentación generada automáticamente - Versión 0.3.0*