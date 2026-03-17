from pathlib import Path
from datetime import date, datetime, timedelta
import polars as pl
from dotenv import dotenv_values

_env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")

# Data subfolder
DATA_FOLDER_NAME = "data"

# Carpeta de este módulo
CURRENT_FOLDER = Path(__file__).parent / DATA_FOLDER_NAME

# Configuración por defecto
DEFAULT_HEADLESS = True
URL_CARTOLAS = (
    "https://www.cmfchile.cl/institucional/estadisticas/fondos_cartola_diaria.php"
)
VERBOSE = True
TIMEOUT = 500_000


IMAGES_FOLDER_NAME = "images"
IMAGES_FOLDER = CURRENT_FOLDER / IMAGES_FOLDER_NAME

# Carpeta donde se guardan los errores
ERROR_FOLDER_NAME = "errors"
ERROR_FOLDER = IMAGES_FOLDER / ERROR_FOLDER_NAME

# Carpeta donde se guardan los archivos correctos
CORRECT_FOLDER_NAME = "correct"
CORRECT_FOLDER = IMAGES_FOLDER / CORRECT_FOLDER_NAME

# Carpeta donde se guardan los archivos txt de las cartolas
CARTOLAS_FOLDER_NAME = "txt"
CARTOLAS_FOLDER = CURRENT_FOLDER / CARTOLAS_FOLDER_NAME
WILDCARD_CARTOLAS_TXT = "ffmm*.txt"

# Carpeta donde se guardan los archivos Parquet
PARQUET_FOLDER_NAME = "parquet"
PARQUET_FOLDER = CURRENT_FOLDER / PARQUET_FOLDER_NAME
PARQUET_FILE_NAME = "cartolas.parquet"
PARQUET_FILE_PATH = PARQUET_FOLDER / PARQUET_FILE_NAME

# Carpeta donde se guardan los archivos Parquet por año
PARQUET_FOLDER_YEAR_NAME = "yearly"
PARQUET_FOLDER_YEAR = CURRENT_FOLDER / PARQUET_FOLDER_YEAR_NAME

# Carpeta donde se guardan los json de El Mercurio
ELMER_FOLDER_NAME = "elmer"
ELMER_FOLDER = CURRENT_FOLDER / ELMER_FOLDER_NAME

# Carpeta donde se guardan los archivos Parquet de datos del Banco Central
BCCH_FOLDER_NAME = "bcch"
BCCH_FOLDER = CURRENT_FOLDER / BCCH_FOLDER_NAME

# El import es acá para evitar importaciones circulares con file_tools.py
from utiles.file_tools import generate_hash_image_name  # noqa: E402

# Carpeta donde se guardan los archivos temporales
TEMP_FOLDER_NAME = "temp"
TEMP_FOLDER = IMAGES_FOLDER / TEMP_FOLDER_NAME
TEMP_FILE_NAME = generate_hash_image_name()
TEMP_FILE_PWD = TEMP_FOLDER / TEMP_FILE_NAME

## FECHAS
FECHA_MINIMA = date(2007, 12, 31)
# Esto considera los días para atrás que es la última cartola
# Si es antes de las 11 es el de ante ayer, si es después de las 11 es el de ayer
DIAS_ATRAS = 1 if datetime.now().hour > 10 else 2
FECHA_MAXIMA = datetime.now().date() - timedelta(days=DIAS_ATRAS)
INITIAL_DATE_RANGE: int = 33  # días que baja la primera vez

# Características de polars
COLUMNAS_BOOLEAN = ["PARTICIPES_INST", "FONDO_PEN"]
COLUMNAS_NULL = ["FACTOR DE AJUSTE", "FACTOR DE REPARTO"]
SORTING_ORDER = ["RUN_ADM", "RUN_FM", "SERIE", "FECHA_INF"]

# Esquema de las columnas para los DataFrames de Polars
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

SOYFOCUS_FUNDS = {9809: "MODERADO", 9810: "CONSERVADOR", 9811: "ARRIESGADO"}

# Carpeta donde se guardan los archivos Parquet
SOYFOCUS_PARQUET_FILE_NAME = "soyfocus.parquet"
SOYFOCUS_BY_RUN_FILE_NAME = "soyfocus_by_run.parquet"
SOYFOCUS_TAC_FILE_NAME = "soyfocus_tac.parquet"
SOYFOCUS_PARQUET_FILE_PATH = PARQUET_FOLDER / SOYFOCUS_PARQUET_FILE_NAME
SOYFOCUS_BY_RUN_PARQUET_FILE_PATH = PARQUET_FOLDER / SOYFOCUS_BY_RUN_FILE_NAME
SOYFOCUS_TAC_PARQUET_FILE_PATH = PARQUET_FOLDER / SOYFOCUS_TAC_FILE_NAME

# COSAS DE MAIL
SENDER_MAIL = _env.get("SENDER_MAIL", "francisco@soyfocus.com")
SENDER_NAME = _env.get("SENDER_NAME", "Francisco")
TO_EMAILS = [e.strip() for e in _env.get("TO_EMAILS", "francisco@soyfocus.com").split(",")]
