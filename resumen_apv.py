from cartolas.read import read_parquet_cartolas_lazy
from cartolas.config import PARQUET_FOLDER_YEAR
import polars as pl
from datetime import date
from eco.bcentral import PARQUET_PATH as BCCH_PARQUET

print(BCCH_PARQUET)


if __name__ == "__main__":
    df = read_parquet_cartolas_lazy(
        parquet_path=PARQUET_FOLDER_YEAR
    ).filter(pl.col("RUN_FM").is_in([9809, 9810, 9811])).select(
        "RUN_FM",
        "FECHA_INF",
        "SERIE",
        "VALOR_CUOTA",
    )
    df.collect().filter(pl.col("SERIE").is_in(["APV", "APV-FREE"])).sort("FECHA_INF").filter(pl.col("FECHA_INF") > date(2024, 1, 1)).write_csv("apv.csv")
    
    df_bcch = pl.read_parquet(BCCH_PARQUET)
    df_bcch.select(pl.col(["FECHA_INF", "UF"])).filter(pl.col("FECHA_INF") > date(2024, 1, 1)).write_csv("uf.csv")