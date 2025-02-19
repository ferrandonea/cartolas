"""
Este módulo se encarga de actualizar las cartolas de la CMF en archivos separados por año.

Contiene funciones para actualizar los datos de las cartolas en múltiples archivos Parquet,
uno por cada año.
"""

from datetime import date
from pathlib import Path

from cartolas.config import FECHA_MINIMA, FECHA_MAXIMA, PARQUET_FOLDER_YEAR
from cartolas.download import download_cartolas_range
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.save import save_lazyframe_to_parquet
from cartolas.transform import transform_cartola_folder
from utiles.fechas import date_range, consecutive_date_ranges
from utiles.decorators import timer
from utiles.file_tools import clean_txt_folder

import polars as pl


def get_year_parquet_path(year: int, base_dir: Path = Path("cartolas/data")) -> Path:
    """
    Genera la ruta del archivo parquet para un año específico.

    Args:
        year (int): Año para el cual generar la ruta
        base_dir (Path): Directorio base donde se guardarán los archivos

    Returns:
        Path: Ruta completa del archivo parquet para el año especificado
    """
    return base_dir / f"cartolas_{year}.parquet"


@timer
def update_parquet_by_year(
    base_dir: Path = PARQUET_FOLDER_YEAR,
    min_date: date = FECHA_MINIMA,
    max_date: date = FECHA_MAXIMA,
    sleep_time: int = 10,
) -> None:
    """
    Actualiza los datos de las cartolas en archivos Parquet separados por año.

    Args:
        base_dir (Path): Directorio base donde se guardarán los archivos
        min_date (date): Fecha mínima para la actualización
        max_date (date): Fecha máxima para la actualización
        sleep_time (int): Tiempo de espera entre descargas en segundos

    Returns:
        None
    """
    # Asegura que el directorio base existe
    base_dir.mkdir(parents=True, exist_ok=True)

    # Obtiene el rango de años a procesar
    years_range = range(min_date.year, max_date.year + 1)

    # Diccionario para almacenar las fechas faltantes por año
    missing_dates_by_year = {}

    # Para cada año, verifica las fechas existentes y faltantes
    for year in years_range:
        year_file = get_year_parquet_path(year, base_dir)

        # Define el rango de fechas para este año
        year_start = max(date(year, 1, 1), min_date)
        year_end = min(date(year, 12, 31), max_date)
        year_dates = date_range(year_start, year_end)

        if year_file.exists():
            # Lee el archivo parquet del año
            lazy_year_df = read_parquet_cartolas_lazy(parquet_path=year_file)
            # Obtiene las fechas únicas en el archivo
            dates_in_parquet = (
                lazy_year_df.select(["FECHA_INF"])
                .unique()
                .collect()
                .to_series()
                .to_list()
            )
        else:
            # Si el archivo no existe, no hay fechas existentes
            dates_in_parquet = []

        # Calcula las fechas faltantes para este año
        missing_dates = sorted(list(set(year_dates) - set(dates_in_parquet)))
        if missing_dates:
            missing_dates_by_year[year] = missing_dates

    # Si hay fechas faltantes en algún año, procesa las actualizaciones
    if missing_dates_by_year:
        # Muestra los rangos de fechas faltantes por año
        for year, dates in missing_dates_by_year.items():
            print(f"\nFechas faltantes para {year}:")
            for i, fecha in enumerate(consecutive_date_ranges(dates)):
                print(i, ":", " -> ".join([x.strftime("%d/%m/%Y") for x in fecha]))

            # Descarga las cartolas para las fechas faltantes
            download_cartolas_range(dates, sleep_time)

            # Transforma los datos descargados
            lazy_df_newdata = transform_cartola_folder(unique=True)

            # Filtra solo los datos del año actual
            lazy_df_newdata = lazy_df_newdata.filter(
                pl.col("FECHA_INF").dt.year() == year
            )

            # Lee o crea el archivo del año
            year_file = get_year_parquet_path(year, base_dir)
            if year_file.exists():
                lazy_year_df = read_parquet_cartolas_lazy(parquet_path=year_file)
                # Concatena los datos existentes con los nuevos
                df = pl.concat([lazy_year_df, lazy_df_newdata])
            else:
                df = lazy_df_newdata

            # Guarda el archivo del año
            print(f"Grabando parquet para el año {year}")
            save_lazyframe_to_parquet(lazy_df=df, filename=year_file)

        # Limpia los archivos temporales
        clean_txt_folder(delete_all=True)

    else:
        print("Archivos parquet actualizados, no hay cambios")


if __name__ == "__main__":
    update_parquet_by_year()
