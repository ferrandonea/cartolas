"""Funciones que leen la información histórica almacenada en la carpeta correcta."""

import polars as pl
from pathlib import Path


def read_parquet_cartolas_lazy(
    parquet_file: str | Path, sorted: bool = True
) -> pl.LazyFrame:
    # TODO: Que lea una carpeta y no un archivo

    if not Path(parquet_file).exists():
        raise FileNotFoundError(f"El archivo {parquet_file} no existe")
    lazy_df = pl.scan_parquet(parquet_file)
    return (
        lazy_df.sort(["FECHA_INF", "RUN_ADM", "RUN_FM", "SERIE"]) if sorted else lazy_df
    )


if __name__ == "__main__":
    df = read_parquet_cartolas_lazy(
        parquet_file="c:/Users/Usuario/Downloads/CMF/cartolas/correct/2021-09-30.parquet"
    )
