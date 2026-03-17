import polars as pl


def add_cumulative_returns(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calcula las rentabilidades acumuladas para cada fondo y serie.

    Esta función procesa el DataFrame para calcular la rentabilidad acumulada
    utilizando el producto acumulativo de las rentabilidades diarias.

    Args:
        df (pl.DataFrame): DataFrame con las rentabilidades diarias por fondo y serie

    Returns:
        pl.DataFrame: DataFrame original con una nueva columna 'RENTABILIDAD_ACUMULADA'
            que contiene el producto acumulativo de las rentabilidades diarias
    """
    sorted_df = df.sort(["RUN_FM", "SERIE", "FECHA_INF"])

    return sorted_df.with_columns(
        [
            pl.col("RENTABILIDAD_DIARIA_PESOS")
            .cum_prod()
            .over(["RUN_FM", "SERIE"])
            .fill_nan(1)
            .fill_null(1)
            .alias("RENTABILIDAD_ACUMULADA")
        ]
    )
