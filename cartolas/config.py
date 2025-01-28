from pathlib import Path
from datetime import date, datetime, timedelta
import polars as pl

# Carpeta de este módulo
CURRENT_FOLDER = Path(__file__).parent

DEFAULT_HEADLESS = True
URL_CARTOLAS = (
    "https://www.cmfchile.cl/institucional/estadisticas/fondos_cartola_diaria.php"
)
VERBOSE = True
TIMEOUT = 500_000

# Carpeta donde se guardan los errores
ERROR_FOLDER_NAME = "errors"
ERROR_FOLDER = CURRENT_FOLDER / ERROR_FOLDER_NAME

# Carpeta donde se guardan los correctosuv r
CORRECT_FOLDER_NAME = "correct"
CORRECT_FOLDER = CURRENT_FOLDER / CORRECT_FOLDER_NAME

# Carpeta donde se guardan los txt de las cartolas
CARTOLAS_FOLDER_NAME = "txt"
CARTOLAS_FOLDER = CURRENT_FOLDER / CARTOLAS_FOLDER_NAME
WILDCARD_CARTOLAS_TXT = "ffmm*.txt"

# Este es la carpeta donde se guardan los archivos temporales
PARQUET_FOLDER_NAME = "parquet"
PARQUET_FOLDER = CURRENT_FOLDER / PARQUET_FOLDER_NAME
PARQUET_FILE_NAME = "cartolas.parquet"
PARQUET_FILE_PATH = PARQUET_FOLDER / PARQUET_FILE_NAME

# El import es acá para evitar importaciones circulares con file_tools.py
from utiles.file_tools import generate_hash_image_name  # noqa: E402

# Este es la carpeta donde se guardan los archivos temporales
TEMP_FOLDER_NAME = "temp"
TEMP_FOLDER = CURRENT_FOLDER / TEMP_FOLDER_NAME
TEMP_FILE_NAME = generate_hash_image_name()
TEMP_FILE_PWD = TEMP_FOLDER / TEMP_FILE_NAME

## FECHAS
FECHA_MINIMA = date(2007, 12, 31)
# Esto considera los días para atrás que es la última cartola
# Si es antes de las 11 es el de ante ayer, si es después de las 11 es el de ayer
DIAS_ATRAS = 1 if datetime.now().hour > 11 else 2
FECHA_MAXIMA = datetime.now().date() - timedelta(days=DIAS_ATRAS)
INITIAL_DATE_RANGE: int = 33  # días que baja la primera vez

# Caracteristicas de polars
COLUMNAS_BOOLEAN = ["PARTICIPES_INST", "FONDO_PEN"]
COLUMNAS_NULL = ["FACTOR DE AJUSTE", "FACTOR DE REPARTO"]
SORTING_ORDER = ["RUN_ADM", "RUN_FM", "SERIE", "FECHA_INF"]

SCHEMA = {
    "RUN_ADM": pl.UInt32,
    "NOM_ADM": pl.String,
    "RUN_FM": pl.UInt16,  # OJO QUE ES HASTA 65.535
    "FECHA_INF": pl.String,  # PORQUE ES MAS FÁCIL LA CONVERSIÓN A Date
    "ACTIVO_TOT": pl.Float64,
    "MONEDA": pl.String,
    "PARTICIPES_INST": pl.String,
    "INVERSION_EN_FONDOS": pl.Float64,
    "SERIE": pl.String,
    "CUOTAS_APORTADAS": pl.Float64,
    "CUOTAS_RESCATADAS": pl.Float64,
    "CUOTAS_EN_CIRCULACION": pl.Float64,
    "VALOR_CUOTA": pl.Float64,
    "PATRIMONIO_NETO": pl.Float64,
    "NUM_PARTICIPES": pl.UInt32,  # HASTA 4.294.967.295
    "NUM_PARTICIPES_INST": pl.UInt16,  # OJO QUE ES HASTA 65.535
    "FONDO_PEN": pl.String,
    "REM_FIJA": pl.Float64,
    "REM_VARIABLE": pl.Float64,
    "GASTOS_AFECTOS": pl.Float64,
    "GASTOS_NO_AFECTOS": pl.Float64,
    "COMISION_INVERSION": pl.Float64,
    "COMISION_RESCATE": pl.Float64,
    "FACTOR DE AJUSTE": pl.Float64,
    "FACTOR DE REPARTO": pl.Float64,
}
