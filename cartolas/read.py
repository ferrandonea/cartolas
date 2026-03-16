"""Funciones que leen la información histórica almacenada en la carpeta correcta."""

import polars as pl
from pathlib import Path


def read_parquet_cartolas_lazy(
    parquet_path: str | Path, is_sorted: bool = True
) -> pl.LazyFrame:
    """
    Lee archivos Parquet desde una carpeta de manera perezosa (lazy).

    Args:
        parquet_path (str | Path): Ruta a la carpeta que contiene los archivos Parquet.
        is_sorted (bool): Si True, ordena el DataFrame resultante por las columnas
                       'FECHA_INF', 'RUN_ADM', 'RUN_FM', 'SERIE'.

    Returns:
        pl.LazyFrame: Un LazyFrame de Polars que representa los datos leídos.
    """
    # Verificar si la ruta existe
    if not Path(parquet_path).exists():
        raise FileNotFoundError(f"La ruta {parquet_path} no existe")

    # Escanear todos los archivos Parquet en la carpeta
    lazy_df = pl.scan_parquet(parquet_path)

    # Ordenar el DataFrame si se especifica
    return (
        lazy_df.sort(["FECHA_INF", "RUN_ADM", "RUN_FM", "SERIE"]) if is_sorted else lazy_df
    )


if __name__ == "__main__":
    # Ejemplo de uso de la función read_parquet_cartolas_lazy
    df = read_parquet_cartolas_lazy(
        parquet_path="c:/Users/Usuario/Downloads/CMF/cartolas/correct/"
    )
