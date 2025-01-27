"""Este módulo se encarga de actualizar las cartolas de la CMF."""

from pathlib import Path
from datetime import date, datetime, timedelta
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.config import CURRENT_FOLDER
from utiles.fechas import date_range, consecutive_date_ranges
from .download import get_cartola_from_cmf
from utiles.file_tools import clean_txt_folder


# Este es la carpeta donde se guardan los archivos temporales
PARQUET_FOLDER_NAME = "parquet"
PARQUET_FOLDER = CURRENT_FOLDER / PARQUET_FOLDER_NAME
PARQUET_FILE_NAME = "cartolas.parquet"
PARQUET_FILE_PATH = PARQUET_FOLDER / PARQUET_FILE_NAME


def first_run() -> None:

if __name__ == "__main__":
    pass