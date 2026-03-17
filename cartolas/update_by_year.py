"""Wrapper para retrocompatibilidad. Usa cartolas.update.update_parquet(by_year=True)."""

from cartolas.config import FECHA_MINIMA, get_fecha_maxima, PARQUET_FOLDER_YEAR
from cartolas.update import update_parquet


def update_parquet_by_year(
    base_dir=PARQUET_FOLDER_YEAR,
    min_date=FECHA_MINIMA,
    max_date=None,
    sleep_time=1,
):
    if max_date is None:
        max_date = get_fecha_maxima()
    update_parquet(
        parquet_file=base_dir,
        min_date=min_date,
        max_date=max_date,
        sleep_time=sleep_time,
        by_year=True,
    )


if __name__ == "__main__":
    update_parquet_by_year()
