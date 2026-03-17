"""
Este módulo se encarga de actualizar las cartolas de la CMF,
ya sea en un archivo Parquet monolítico o en archivos separados por año.
"""

import logging
from datetime import date
from pathlib import Path

from cartolas.config import CARTOLAS_FOLDER, FECHA_MINIMA, PARQUET_FILE_PATH, PARQUET_FOLDER_YEAR, SCHEMA, get_fecha_maxima, FECHA_MAXIMA
from cartolas.download import download_cartolas_range
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.save import save_lazyframe_to_parquet
from cartolas.transform import transform_cartola_folder
from utiles.fechas import date_range, consecutive_date_ranges
from utiles.decorators import timer
from utiles.file_tools import clean_txt_folder

import polars as pl

logger = logging.getLogger(__name__)


def _get_dates_in_parquet(parquet_path: Path) -> list[date]:
    if parquet_path.exists():
        return (
            read_parquet_cartolas_lazy(parquet_path=parquet_path)
            .select(["FECHA_INF"])
            .unique()
            .collect()
            .to_series()
            .to_list()
        )
    return []


def _print_missing_ranges(missing_dates: list[date], label: str = ""):
    prefix = f" para {label}" if label else ""
    logger.info(f"Fechas faltantes{prefix}: (rangos)")
    for i, fecha in enumerate(consecutive_date_ranges(missing_dates)):
        logger.info(f"{i}: {' -> '.join([x.strftime('%d/%m/%Y') for x in fecha])}")


def get_year_parquet_path(year: int, base_dir: Path) -> Path:
    return base_dir / f"cartolas_{year}.parquet"


@timer
def update_parquet(
    parquet_file=None,
    min_date: date = FECHA_MINIMA,
    max_date: date = None,
    sleep_time: int = 1,
    by_year: bool = False,
) -> None:
    """
    Actualiza los datos de las cartolas en archivos Parquet.

    Args:
        parquet_file (Path): Ruta del archivo Parquet (monolítico) o directorio (by_year).
            Si None, usa PARQUET_FILE_PATH o PARQUET_FOLDER_YEAR según by_year.
        min_date (date): Fecha mínima para la actualización.
        max_date (date): Fecha máxima para la actualización.
        sleep_time (int): Tiempo de espera entre descargas en segundos.
        by_year (bool): Si True, usa archivos separados por año.
    """
    if max_date is None:
        max_date = get_fecha_maxima()

    if parquet_file is None:
        parquet_file = PARQUET_FOLDER_YEAR if by_year else PARQUET_FILE_PATH
    if by_year:
        _update_by_year(parquet_file, min_date, max_date, sleep_time)
    else:
        _update_single(parquet_file, min_date, max_date, sleep_time)


def _update_single(parquet_file, min_date, max_date, sleep_time):
    dates_in_parquet = _get_dates_in_parquet(parquet_file)
    lazy_parquet_df = (
        read_parquet_cartolas_lazy(parquet_path=parquet_file)
        if parquet_file.exists()
        else pl.LazyFrame(schema_overrides=SCHEMA)
    )

    all_dates = date_range(min_date, max_date)
    missing_dates = sorted(list(set(all_dates) - set(dates_in_parquet)))

    if missing_dates:
        _print_missing_ranges(missing_dates)
        download_cartolas_range(missing_dates, sleep_time)
        lazy_df_newdata = transform_cartola_folder(unique=True)
        df = pl.concat([lazy_parquet_df, lazy_df_newdata])
        logger.info("Grabando parquet")
        save_lazyframe_to_parquet(lazy_df=df, filename=parquet_file)
        clean_txt_folder(folder=CARTOLAS_FOLDER, delete_all=True)
    else:
        logger.info("Archivo parquet actualizado, no hay cambios")


def _update_by_year(base_dir, min_date, max_date, sleep_time):
    base_dir.mkdir(parents=True, exist_ok=True)
    years_range = range(min_date.year, max_date.year + 1)

    missing_dates_by_year = {}
    for year in years_range:
        year_file = get_year_parquet_path(year, base_dir)
        year_start = max(date(year, 1, 1), min_date)
        year_end = min(date(year, 12, 31), max_date)
        year_dates = date_range(year_start, year_end)
        dates_in_parquet = _get_dates_in_parquet(year_file)
        missing_dates = sorted(list(set(year_dates) - set(dates_in_parquet)))
        if missing_dates:
            missing_dates_by_year[year] = missing_dates

    if missing_dates_by_year:
        for year, dates in missing_dates_by_year.items():
            _print_missing_ranges(dates, str(year))
            download_cartolas_range(dates, sleep_time)
            lazy_df_newdata = transform_cartola_folder(unique=True).filter(
                pl.col("FECHA_INF").dt.year() == year
            )
            year_file = get_year_parquet_path(year, base_dir)
            if year_file.exists():
                lazy_year_df = read_parquet_cartolas_lazy(parquet_path=year_file)
                df = pl.concat([lazy_year_df, lazy_df_newdata])
            else:
                df = lazy_df_newdata
            logger.info(f"Grabando parquet para el año {year}")
            save_lazyframe_to_parquet(lazy_df=df, filename=year_file)
        clean_txt_folder(folder=CARTOLAS_FOLDER, delete_all=True)
    else:
        logger.info("Archivos parquet actualizados, no hay cambios")


from utiles.logging_config import setup_logging

if __name__ == "__main__":
    setup_logging()
    update_parquet()
