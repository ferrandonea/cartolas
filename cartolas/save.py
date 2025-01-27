import polars as pl
from pathlib import Path

def save_lazyframe_to_parquet(lazy_df: pl.LazyFrame, filename: str | Path):
    """ Graba lazyframe en parquet"""
    
    lazy_df.collect().write_parquet(filename)
