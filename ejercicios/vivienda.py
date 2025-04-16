"""Análisis de las series vivienda"""

from cartolas.read import read_parquet_cartolas_lazy
from cartolas.config import PARQUET_FOLDER_YEAR
import polars as pl

RUNS_ADM = [77057272, 96836390]  # SoyFocus y Banco Estado
COLUMNAS_RELEVANTES = [
    "SERIE",
    "RUN_FM",
    "RUN_ADM",
    "FECHA_INF",
    "MONEDA",
    "CUOTAS_APORTADAS",
    "CUOTAS_RESCATADAS",
    "CUOTAS_EN_CIRCULACION",
    "VALOR_CUOTA",
    "NUM_PARTICIPES",
]


def transform_df_to_vivienda(parquet_folder: str = PARQUET_FOLDER_YEAR) -> pl.DataFrame:
    df = (
        read_parquet_cartolas_lazy(parquet_folder)
        .select(COLUMNAS_RELEVANTES)
        .collect()  # Hay un tema con los filtros en LazyFrame, si uno hace select y después filter se cae porque parece no encuentra la columna
        .filter(pl.col("SERIE") == "VIVIENDA")
        .filter(pl.col("RUN_ADM").is_in(RUNS_ADM))
        .with_columns(
            (pl.col("CUOTAS_APORTADAS") - pl.col("CUOTAS_RESCATADAS")).alias(
                "FLUJO_CUOTAS"
            )
        )
        .with_columns(
            (pl.col("FLUJO_CUOTAS") * pl.col("VALOR_CUOTA").round(0)).alias(
                "FLUJO_CUOTAS_PESOS"
            )
        )
    )

    # Asumo que está todo en pesos chilenos (así ha sido entiendo)

    return df


def get_flujo_by_agf(df: pl.DataFrame) -> pl.DataFrame:
    return df.group_by(["FECHA_INF", "RUN_ADM"]).agg(
        pl.col("FLUJO_CUOTAS_PESOS").sum().alias("FLUJO_CUOTAS_PESOS")
    )


def pivot_flujo_by_agf(df: pl.DataFrame) -> pl.DataFrame:
    # Primero, agregar nombres de administradoras para mejor legibilidad
    # Pivotear el DataFrame
    pivoted_df = df.pivot(
        index="FECHA_INF",
        columns="RUN_ADM",  # Usamos el nombre en lugar del RUN para mejor legibilidad
        values="FLUJO_CUOTAS_PESOS",
    )

    # Ordenar por fecha
    return pivoted_df.sort("FECHA_INF").fill_nan(0).fill_null(0)


def mediano_y_largo_plazo(df: pl.DataFrame) -> pl.DataFrame:
    RUNS = {8316: 42, 8319: 3, 8807: 15, 9291: 3}

    return df.filter(pl.col("RUN_FM").is_in(list(RUNS.keys()))).with_columns(
        pl.when(pl.col("RUN_FM").is_in(list(RUNS.keys())))
        .then(pl.col("RUN_FM").replace(RUNS))
        .otherwise(None)
        .alias("PLAZO")
    )


if __name__ == "__main__":
    df = transform_df_to_vivienda()
    print(df)
    df_myl = mediano_y_largo_plazo(df)

    print(df_myl)

    df_myl_grouped = (
        df_myl.group_by(["FECHA_INF", "RUN_ADM"])
        .agg(pl.col("FLUJO_CUOTAS_PESOS").sum().alias("FLUJO_CUOTAS_PESOS"))
        .sort("FECHA_INF")
        .with_columns(pl.col("FLUJO_CUOTAS_PESOS") / 0.63 / 1e6)
    )
    print(df_myl_grouped)
    # print(df.select(["MONEDA"]).unique())
    # grouped_df = get_flujo_by_agf(df)
    # print(grouped_df)
    # pivoted_df = pivot_flujo_by_agf(grouped_df)
    # print(pivoted_df)
    # pivoted_df.write_csv("flujo_vivienda_2.csv")
    # from datetime import datetime, date

    # data_date = date(2023, 10, 24)
    # print(
    #     df.filter(pl.col("FECHA_INF") == data_date)
    #     .group_by(["RUN_ADM"])
    #     .agg((pl.col("CUOTAS_EN_CIRCULACION").sum() / 1e6).alias("FLUJO_CUOTAS_PESOS"))
    # )
    # print(df.filter(pl.col("FECHA_INF") == data_date))

    # df_id = download_fund_identification()
    # print(df.schema)

    # print (df_id.head(1).to_pandas().to_string())
    # print (df_id.select("TIPO_FONDO").unique())
