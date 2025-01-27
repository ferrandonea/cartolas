from pathlib import Path
from datetime import date, datetime, timedelta

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
INITIAL_DATE_RANGE = 33 # días que baja la primera vez


