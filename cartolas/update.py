"""
Este módulo se encarga de actualizar las cartolas de la CMF.

Contiene funciones para actualizar los datos de las cartolas en un archivo Parquet.
"""

from datetime import date

from cartolas.config import FECHA_MINIMA, PARQUET_FILE_PATH, SCHEMA, get_fecha_maxima
from cartolas.download import download_cartolas_range
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.save import save_lazyframe_to_parquet
from cartolas.transform import transform_cartola_folder
from utiles.fechas import date_range, consecutive_date_ranges
from utiles.decorators import timer
from utiles.file_tools import clean_txt_folder

import polars as pl


@timer
def update_parquet(
    parquet_file=PARQUET_FILE_PATH,
    min_date: date = FECHA_MINIMA,
    max_date: date = None,
    sleep_time: int = 1,
) -> None:
    """
    Actualiza los datos de las cartolas en un archivo Parquet.

    Args:
        parquet_file (Path): Ruta del archivo Parquet.
        min_date (date): Fecha mínima para la actualización.
        max_date (date): Fecha máxima para la actualización.
        sleep_time (int): Tiempo de espera entre descargas en segundos.

    Returns:
        None
    """

    if max_date is None:
        max_date = get_fecha_maxima()

    # TODO: Esto se podría unir con el script de baja diaria de la cartola
    # TODO: Bajar cada día los últimos 30 días por si hay cambios (eso pasa)

    # Chequea si existe o no el archivo parquet
    if parquet_file.exists():
        # Lee el archivo parquet
        lazy_parquet_df = read_parquet_cartolas_lazy(parquet_path=parquet_file)
        # Obtiene las fechas únicas en el archivo parquet
        dates_in_parquet = (
            lazy_parquet_df.select(["FECHA_INF"])
            .unique()
            .collect()
            .to_series()
            .to_list()
        )

    else:
        # Si el archivo parquet no existe, crea un LazyFrame vacío con el esquema definido
        lazy_parquet_df = pl.LazyFrame(schema_overrides=SCHEMA)
        # Obviamente en este caso no hay fechas
        dates_in_parquet = []

    # Rango de todas las fechas entre la mínima y la máxima
    all_dates = date_range(min_date, max_date)

    # Fechas faltantes en el parquet
    missing_dates = sorted(list(set(all_dates) - set(dates_in_parquet)))

    # Si hay alguna fecha faltante se hace correr el proceso de bajarlas y subirlas
    if missing_dates:
        # Lista de sets de fechas (esto es solo para ver que se está bajando bien)
        print("Fechas faltantes: (rangos)")
        for i, fecha in enumerate(consecutive_date_ranges(missing_dates)):
            print(i, ":", " -> ".join([x.strftime("%d/%m/%Y") for x in fecha]))

        # Se bajan las cartolas desde la cmf
        download_cartolas_range(missing_dates, sleep_time)

        # Transforma los datos del csv en el formato del parquet
        # Por ejemplo se cambian los S/N por bool y se ajustan los factores de ajuste y reparto
        # Y estos datos se guardan en un LazyFrame
        lazy_df_newdata = transform_cartola_folder(unique=True)

        # Se unen los dos LazyFrame, uno del parquet y otro del nuevo
        # TODO: ver atributos de la función concat, creo que asume que es horizontal
        df = pl.concat([lazy_parquet_df, lazy_df_newdata])

        # Se graba el parquet y se verifica que no haya duplicados
        print("Grabando parquet")
        save_lazyframe_to_parquet(lazy_df=df, filename=parquet_file)

        # Se borran los txt
        clean_txt_folder(delete_all=True)

    else:
        print("Archivo parquet actualizado, no hay cambios")


if __name__ == "__main__":
    update_parquet()
