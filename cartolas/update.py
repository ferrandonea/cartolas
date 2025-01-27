"""Este módulo se encarga de actualizar las cartolas de la CMF."""

from pathlib import Path
from datetime import date, datetime, timedelta
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.config import CURRENT_FOLDER
from utiles.fechas import date_range, consecutive_date_ranges
from .download import download_cartolas
## FECHAS
FECHA_MINIMA = date(2007, 12, 31)
# Esto considera los días para atrás que es la última cartola
# Si es antes de las 11 es el de ante ayer, si es después de las 11 es el de ayer
DIAS_ATRAS = 1 if datetime.now().hour > 11 else 2
FECHA_MAXIMA = datetime.now().date() - timedelta(days=DIAS_ATRAS)
INITIAL_DATE_RANGE = 33 # días que baja la primera vez

# Este es la carpeta donde se guardan los archivos temporales
PARQUET_FOLDER_NAME = "parquet"
PARQUET_FOLDER = CURRENT_FOLDER / PARQUET_FOLDER_NAME
PARQUET_FILE_NAME = "cartolas.parquet"
PARQUET_FILE_PATH = PARQUET_FOLDER / PARQUET_FILE_NAME


def first_run(
    parquet_file_path: Path = PARQUET_FILE_PATH,
    start_date: date = FECHA_MINIMA,
    end_date: date = FECHA_MINIMA + timedelta(33),
) -> None:
    """Esto solo se corre la primera vez que uno instala esto en un computador"""

    if parquet_file_path.exists():
        print(f"Archivo {parquet_file_path.filename} ya existe")
        return
    update_cartolas(parquet_file_path, start_date, end_date)
    

def update_cartolas(
    parquet_file_path: Path = PARQUET_FILE_PATH,
    start_date: date = FECHA_MINIMA,
    end_date: date = FECHA_MINIMA + timedelta(INITIAL_DATE_RANGE),
) -> None:
    rango_fechas = consecutive_date_ranges(date_range(start_date, end_date))
    num_rangos = len(rango_fechas)
    print (f"{start_date=}, {end_date=}, {num_rangos=}")
    
    for i, (start_date, end_date) in enumerate(rango_fechas):
        print(f"Descargando rango {i+1} de {num_rangos}")
        print(f"{start_date=}, {end_date=}")
        download_cartolas(start_date, end_date, verbose=True)


if __name__ == "__main__":
    first_run()    