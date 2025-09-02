from cartolas.read import read_parquet_cartolas_lazy
from cartolas.config import PARQUET_FOLDER_YEAR
import polars as pl
from datetime import date
from eco.bcentral import PARQUET_PATH as BCCH_PARQUET

if __name__ == "__main__":
    df = read_parquet_cartolas_lazy(
        parquet_path=PARQUET_FOLDER_YEAR
    ).filter(pl.col("RUN_FM").is_in([9809, 9810, 9811]))
    
    print (df.collect().columns)
    
    df.collect().write_csv("soyfocus.csv")