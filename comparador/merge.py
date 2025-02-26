from cartolas.soyfocus import read_parquet_cartolas_lazy
from cartolas.config import PARQUET_FOLDER_YEAR
from datetime import datetime, timedelta
import polars as pl
from .elmer import last_elmer_data_as_polars
from eco.bcentral import baja_bcch_as_polars, baja_dolar_observado_as_polars ,baja_dolar_y_euro_as_polars
from utiles.listas import multiply_list

MAX_YEARS = 10
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
COLUMNAS_GASTOS = ["REM_FIJA", "REM_VARIABLE", "GASTOS_AFECTOS", "GASTOS_NO_AFECTOS"]
COLUMNAS_COMISIONES = ["COMISION_INVERSION", "COMISION_RESCATE"]
COLUMNAS_FACTORES = ["FACTOR DE AJUSTE", "FACTOR DE REPARTO"]

# Bajo el parquet de cartolas de todos los años de todos los fondos
SUMA_GASTOS = sum([pl.col(x) for x in COLUMNAS_GASTOS])
SUMA_COMISIONES = sum([pl.col(x) for x in COLUMNAS_COMISIONES])
PRODUCTO_FACTORES = multiply_list([pl.col(x) for x in COLUMNAS_FACTORES])

cartola_df = (
    read_parquet_cartolas_lazy(PARQUET_FOLDER_YEAR)
    .filter(pl.col("FECHA_INF") >= MIN_DATE)
    .select(COLUMNAS_RELEVANTES)
    .with_columns(SUMA_GASTOS.alias("GASTOS_TOTALES"))
    #.drop(COLUMNAS_GASTOS)
    .with_columns(SUMA_COMISIONES.alias("COMISIONES_TOTALES"))
    #.drop(COLUMNAS_COMISIONES)
    .with_columns(PRODUCTO_FACTORES.alias("PRODUCTO_FACTORES"))
    #.drop(COLUMNAS_FACTORES)
    .sort(["RUN_FM", "SERIE", "FECHA_INF"])  # Agregamos SERIE al ordenamiento
    .with_columns([
        pl.col("VALOR_CUOTA")
        .shift(1)
        .over(["RUN_FM", "SERIE"])  # Agregamos SERIE al particionamiento
        .alias("VALOR_CUOTA_ANTERIOR")
    ])
    .with_columns((pl.col("VALOR_CUOTA")*pl.col("PRODUCTO_FACTORES")).alias("VALOR_CUOTA_AJUSTADO"))
    .with_columns((pl.col("VALOR_CUOTA_AJUSTADO")/pl.col("VALOR_CUOTA_ANTERIOR")).alias("RENTABILIDAD"))
    .filter(~pl.col("MONEDA").is_in(["MONEDA NO DEF."])) # Elimino las cartolas que no tienen moneda definida
)

# Primero veamos qué columnas tenemos
print (cartola_df.collect().head(5))

#cartola_df.collect().head(100_000).write_csv("cartolas_con_valor_anterior.csv")
# Bajo datos del banco central

#print (cartola_df.select("MONEDA").unique().collect())
#print (cartola_df.filter(~pl.col("MONEDA").is_in(["MONEDA NO DEF."])).collect())
#print (cartola_df.collect())
#print (cartola_df.select("MONEDA").unique().collect())

#eco_df = baja_bcch_as_polars().lazy()
eco_df = baja_dolar_y_euro_as_polars().lazy()
print (eco_df.collect())
print (eco_df.melt(id_vars=["FECHA_INF"], value_vars=["PROM", "EUR"], variable_name="MONEDA", value_name="VALOR").sort(["FECHA_INF", "MONEDA"]).collect())
# cartola_df.join(eco_df, on=["FECHA_INF"], how="left").collect().head(100_000).write_csv("cartolas_con_valor_anterior_y_eco.csv")


# print (cartola_df.select("MONEDA").unique().collect())


# cartola_df.filter(pl.col("RUN_FM").is_in([9809,9810,9811])).collect().write_csv("cartolas_con_valor_anterior_y_eco_9809_9810_9811.csv")
# print(cartola_df.filter(~pl.col("MONEDA").is_in(["$$","PROM"])).collect())
# cartola_df.filter(~pl.col("MONEDA").is_in(["$$","PROM"])).collect().write_csv("cartolas_con_valor_anterior_y_eco_9809_9810_9811_no_pesos.csv")
# cartola_df.filter(pl.col("RUN_FM").is_in([10225])).collect().write_csv("cartolas_con_valor_anterior_y_eco_10225.csv")
# # # Bajo el parquet de elmer de todos los años de todos los fonuvx rdos


# # elmer_df = last_elmer_data_as_polars().lazy()

# # print (elmer_df)
# # print (elmer_df.collect())
# # print (elmer_df.columns)

# # # Fusiono los dataframes por RUN_FM y SERIE
# # merged_df = cartola_df.join(elmer_df, on=["RUN_FM","SERIE"], how="left")

# # print (merged_df.columns)
# # print (merged_df.collect())


# # #merged_df = df.join(elmer_df, on=["RUN_FM","SERIE"], how="left").select(["RUN_FM","SERIE","TIPOINV"]).filter(pl.col("TIPOINV").is_in(["RETAIL / PEQUEÑO INVERSOR"]))
# # #print (merged_df.columns)
# # #print (merged_df.collect())
# # df = baja_bcch_as_polars()
# # print (df.columns)
# # print (df)
