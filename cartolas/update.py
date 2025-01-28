"""Este módulo se encarga de actualizar las cartolas de la CMF."""

from datetime import date, timedelta
from cartolas.config import FECHA_MINIMA, INITIAL_DATE_RANGE, PARQUET_FILE_PATH
from utiles.fechas import date_range, consecutive_date_ranges
from cartolas.download import download_cartolas_range
from utiles.decorators import timer
from cartolas.transform import transform_cartola_folder
from cartolas.save import save_lazyframe_to_parquet
from pathlib import Path
from utiles.file_tools import clean_txt_folder
from cartolas.read import read_parquet_cartolas_lazy

FECHA_MAXIMA = date(2008, 2, 10)


@timer
def first_run(
    start_date: date = FECHA_MINIMA,
    days: int = INITIAL_DATE_RANGE,
    parquet_file: Path = PARQUET_FILE_PATH,
) -> None:
    # Creamos los sets de fechas para bajar
    date_sets = consecutive_date_ranges(
        date_range(start_date=start_date, end_date=start_date + timedelta(days))
    )

    for i, (s_date, e_date) in enumerate(date_sets):
        print(f"Rango: {i}, inicio={s_date}, fin={e_date}")
        download_cartolas_range(start_date=s_date, end_date=e_date)

    lazy_df = transform_cartola_folder(unique=True)
    save_lazyframe_to_parquet(lazy_df=lazy_df, filename=parquet_file)
    clean_txt_folder(delete_all=True)


@timer
def update_parquet(start_date: date = FECHA_MINIMA, end_date: date = FECHA_MAXIMA):
    lazy_df = read_parquet_cartolas_lazy(parquet_file=PARQUET_FILE_PATH)

    # Saco las fechas que están en el parquet en una lista
    dates_in_parquet = (
        lazy_df.select(["FECHA_INF"]).unique().collect().to_series().to_list()
    )
    all_dates = date_range(start_date=start_date, end_date=end_date)

    missing_dates = sorted(list(set(all_dates) - set(dates_in_parquet)))

    missing_dates_sets = consecutive_date_ranges(missing_dates)

    # print (dates_in_parquet)
    # print (all_dates)
    print(max(dates_in_parquet))
    print(missing_dates)
    print(missing_dates_sets)


if __name__ == "__main__":
    # first_run()
    update_parquet()
