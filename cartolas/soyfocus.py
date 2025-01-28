from cartolas.config import SOYFOCUS_FUNDS, PARQUET_FILE_PATH, SOYFOCUS_PARQUET_FILE_PATH
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.save import save_lazyframe_to_parquet
import polars as pl
from pathlib import Path

SOYFOCUS_RUNS = list(SOYFOCUS_FUNDS.keys())

def save_soyfocus_parquet(allfunds_file : Path = PARQUET_FILE_PATH, soyfocus_file: Path = SOYFOCUS_PARQUET_FILE_PATH):
    lazy_df = read_parquet_cartolas_lazy(parquet_path=allfunds_file).filter(pl.col("RUN_FM").is_in(SOYFOCUS_RUNS)).drop(["RUN_ADM", "NOM_ADM"])
    save_lazyframe_to_parquet(lazy_df=lazy_df, filename=soyfocus_file, unique=True)

if __name__ == "__main__":
    save_soyfocus_parquet()
