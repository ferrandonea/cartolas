from cartolas.config import (
    SOYFOCUS_FUNDS,
    PARQUET_FILE_PATH,
    SOYFOCUS_PARQUET_FILE_PATH,
)
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.save import save_lazyframe_to_parquet
import polars as pl
from pathlib import Path

# Lista de RUNs identificadores de los fondos SoyFocus
SOYFOCUS_RUNS = list(SOYFOCUS_FUNDS.keys())


def save_soyfocus_parquet(
    allfunds_file: Path = PARQUET_FILE_PATH,
    soyfocus_file: Path = SOYFOCUS_PARQUET_FILE_PATH,
):
    """
    Filtra y guarda los datos de los fondos SoyFocus desde un archivo parquet que contiene todos los fondos.

    Esta función lee un archivo parquet que contiene datos de todos los fondos, filtra para mantener
    solo los fondos de SoyFocus, elimina las columnas administrativas y guarda el resultado en un
    nuevo archivo parquet.

    Args:
        allfunds_file (Path): Ruta al archivo parquet fuente que contiene los datos de todos los fondos.
            Por defecto usa PARQUET_FILE_PATH desde config.
        soyfocus_file (Path): Ruta donde se guardarán los datos filtrados de SoyFocus.
            Por defecto usa SOYFOCUS_PARQUET_FILE_PATH desde config.
    """
    # Lee el archivo parquet fuente de manera diferida y filtra solo los fondos SoyFocus
    lazy_df = (
        read_parquet_cartolas_lazy(parquet_path=allfunds_file)
        .filter(pl.col("RUN_FM").is_in(SOYFOCUS_RUNS))
        .drop(["RUN_ADM", "NOM_ADM"])  # Elimina las columnas administrativas
        .with_columns(
            (
                (
                    pl.col("CUOTAS_EN_CIRCULACION")
                    + pl.col("CUOTAS_RESCATADAS")
                    - pl.col("CUOTAS_APORTADAS")
                )
                * pl.col("VALOR_CUOTA")
            ).alias("PATRIMONIO_AJUSTADO")
        )  # Patrimonio ajustado según la circular 1738 CMF
        .with_columns((pl.col("REM_FIJA")+pl.col("REM_VARIABLE")+pl.col("GASTOS_AFECTOS")+pl.col("GASTOS_NO_AFECTOS")).alias("COSTOS_TOTALES"))
        .with_columns((pl.col("PATRIMONIO_AJUSTADO") + pl.col("COSTOS_TOTALES")).alias("PATRIMONIO_AJUSTADO_COSTOS"))
        .with_columns((pl.col("COSTOS_TOTALES")/pl.col("PATRIMONIO_AJUSTADO_COSTOS")).alias("TASA_COSTOS_DIARIA"))
        .with_columns((pl.col("TASA_COSTOS_DIARIA")*366).alias("TASA_COSTOS_ANUAL"))
    )

    # Guarda los datos filtrados en un nuevo archivo parquet
    save_lazyframe_to_parquet(lazy_df=lazy_df, filename=soyfocus_file, unique=True)


def read_soyfocus_parquet(parquet_path: Path = SOYFOCUS_PARQUET_FILE_PATH):
    """
    Lee un archivo parquet que contiene datos de los fondos SoyFocus.

    Esta función lee un archivo parquet que contiene datos de los fondos SoyFocus y lo devuelve
    como un DataFrame Polars.

    Args:
        parquet_path (Path): Ruta al archivo parquet que contiene los datos de los fondos SoyFocus.
            Por defecto usa SOYFOCUS_PARQUET_FILE_PATH desde config.

    Returns:
        pl.DataFrame: DataFrame Polars que contiene los datos de los fondos SoyFocus.
    """
    return read_parquet_cartolas_lazy(parquet_path=parquet_path, sorted=False)


if __name__ == "__main__":
    save_soyfocus_parquet()
    df = read_soyfocus_parquet()
    print(df.collect())
