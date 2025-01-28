import polars as pl
from pathlib import Path


def save_lazyframe_to_parquet(lazy_df: pl.LazyFrame, filename: str | Path, unique: bool = True):
    """Graba lazyframe en parquet"""
    lazy_df = lazy_df.unique() if unique else lazy_df
    lazy_df.collect().write_parquet(filename)
    print(f"Archivo parquet grabado con éxito en {filename}")
