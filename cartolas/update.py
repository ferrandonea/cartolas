"""Este módulo se encarga de actualizar las cartolas de la CMF."""

from pathlib import Path
from datetime import date, datetime, timedelta
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.config import CURRENT_FOLDER
from utiles.fechas import date_range, consecutive_date_ranges
from .download import get_cartola_from_cmf
from utiles.file_tools import clean_txt_folder


def first_run() -> None:
    pass

if __name__ == "__main__":
    pass