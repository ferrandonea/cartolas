from cartolas.soyfocus import read_parquet_cartolas_lazy
from cartolas.config import PARQUET_FOLDER_YEAR
from datetime import datetime, timedelta
import polars as pl
from .elmer import last_elmer_data_as_polars

MAX_YEARS = 1
MIN_DATE = datetime.now() - timedelta(days=MAX_YEARS * 365)
COLUMNAS_RELEVANTES = [
    "RUN_ADM",
    "RUN_FM",
    "FECHA_INF",
    "MONEDA",
    "SERIE",
    "CUOTAS_APORTADAS",
    "CUOTAS_RESCATADAS",
    "CUOTAS_EN_CIRCULACION",
    "VALOR_CUOTA",
    "NUM_PARTICIPES",
    "REM_FIJA",
    "REM_VARIABLE",
    "GASTOS_AFECTOS",
    "GASTOS_NO_AFECTOS",
    "COMISION_INVERSION",
    "COMISION_RESCATE",
    "FACTOR DE AJUSTE",
    "FACTOR DE REPARTO",
]

# Bajo el parquet de cartolas de todos los años de todos los fondos
cartola_df = read_parquet_cartolas_lazy(PARQUET_FOLDER_YEAR).filter(
    pl.col("FECHA_INF") >= MIN_DATE
).select(COLUMNAS_RELEVANTES)

print(cartola_df.collect().columns)

# TODO: Transformar el dataframe de cartolas para que sea compatible con el de elmer
def transform_cartola_df(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.col("FECHA_INF").str.strptime(pl.Datetime, "%Y-%m-%d"),
        pl.col("RUN_FM").str.split("_").alias("RUN_FM_SERIE"),
    )

# # Bajo el parquet de elmer de todos los años de todos los fonuvx rdos
# elmer_df = last_elmer_data_as_polars().lazy()

# print (elmer_df)
# print (elmer_df.collect())
# print (elmer_df.columns)

# # Fusiono los dataframes por RUN_FM y SERIE
# merged_df = cartola_df.join(elmer_df, on=["RUN_FM","SERIE"], how="left")

# print (merged_df.columns)
# print (merged_df.collect())


# #merged_df = df.join(elmer_df, on=["RUN_FM","SERIE"], how="left").select(["RUN_FM","SERIE","TIPOINV"]).filter(pl.col("TIPOINV").is_in(["RETAIL / PEQUEÑO INVERSOR"]))
# #print (merged_df.columns)
# #print (merged_df.collect())
