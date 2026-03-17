from cartolas.read import read_parquet_cartolas_lazy
from cartolas.config import PARQUET_FOLDER_YEAR
import polars as pl
from eco.bcentral import PARQUET_PATH as BCCH_PARQUET
from utiles.fechas import date_n_years_ago

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
    df_collected = df.collect()
    df_apv = df_collected.filter(pl.col("SERIE").is_in(["APV", "APV-FREE"])).sort("FECHA_INF")
    max_date = df_apv.select(pl.col("FECHA_INF").max()).item()
    df_apv.filter(pl.col("FECHA_INF") > date_n_years_ago(1, max_date)).write_csv("apv.csv")

    df_bcch = pl.read_parquet(BCCH_PARQUET)
    df_bcch.select(pl.col(["FECHA_INF", "UF"])).filter(pl.col("FECHA_INF") > date_n_years_ago(1, max_date)).write_csv("uf.csv")