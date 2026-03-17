from comparador.merge import merge_cartolas_with_categories
import polars as pl
from datetime import date
from utiles.polars_utils import add_cumulative_returns


def create_returns_pivot_table(
    df: pl.DataFrame, pivot_values: str = "RENTABILIDAD_ACUMULADA"
) -> pl.DataFrame:
    """
    Crea una tabla dinámica con fechas como filas y combinaciones de RUN_FM y SERIE como columnas,
    mostrando la rentabilidad acumulada.

    Args:
        df: DataFrame con las columnas RUN_FM, SERIE, FECHA_INF y RENTABILIDAD_ACUMULADA

    Returns:
        DataFrame pivotado con fechas como índice
    """
    # Asegurarse de que estamos trabajando con un DataFrame regular, no un LazyFrame
    if isinstance(df, pl.LazyFrame):
        df = df.collect()

    # Crear una columna combinada de RUN_FM y SERIE para usar como columnas en el pivot
    df_with_id = df.with_columns(
        pl.concat_str([pl.col("RUN_FM"), pl.col("SERIE")], separator=" - ").alias(
            "FONDO_SERIE"
        )
    )

    # Crear la tabla pivotada
    pivot_df = df_with_id.pivot(
        index="FECHA_INF", on="FONDO_SERIE", values=pivot_values
    )

    columnas_numericas = [col for col in pivot_df.columns if col not in ["FECHA_INF"]]
    # pivot_df = pivot_df.with_columns((pl.col(columnas_numericas).fill_nan(1).fill_null(1)).mul(1000))
    pivot_df = pivot_df.with_columns((pl.col(columnas_numericas)))

    # Ordenar por fecha
    return pivot_df.sort("FECHA_INF")


def filter_pivot_by_selected_dates(pivot_df: pl.DataFrame):
    max_date_pl = pivot_df.select("FECHA_INF").max()
    max_date = max_date_pl.to_series().to_list()[0]

    selected_dates = {
        "OM": max_date,
        "1M": date(2025, 2, 28),
        "3M": date(2024, 12, 31),
        "6M": date(2024, 9, 30),
        "1Y": date(2024, 3, 31),
        "3Y": date(2022, 3, 31),
        "5Y": date(2020, 3, 31),
        "YTD": date(2024, 12, 31),
    }

    # selected_dates = {
    #     "OM": max_date,
    #     "1M": last_day_n_months_ago(max_date, 1),
    #     "3M": last_day_n_months_ago(max_date, 3),
    #     "6M": last_day_n_months_ago(max_date, 6),
    #     "1Y": last_day_n_months_ago_by_year(max_date, 1),
    #     "3Y": last_day_n_months_ago_by_year(max_date, 3),
    #     "5Y": last_day_n_months_ago_by_year(max_date, 5),
    # }
    selected_dates_list = list(selected_dates.values())
    pivot_df = pivot_df.filter(pl.col("FECHA_INF").is_in(selected_dates_list))
    print(pivot_df)
    return pivot_df


def calculate_relative_returns(pivot_df: pl.DataFrame) -> pl.DataFrame:
    """
    Calcula los retornos relativos para cada fecha en la tabla pivotada.
    Para cada fila, divide el valor más reciente por el valor de esa fila.

    Args:
        pivot_df: DataFrame pivotado con fechas como índice y fondos-series como columnas

    Returns:
        DataFrame con los retornos relativos calculados
    """
    # Asegurarse de que estamos trabajando con un DataFrame regular
    if isinstance(pivot_df, pl.LazyFrame):
        pivot_df = pivot_df.collect()

    # Ordenar por fecha para asegurar que la última fecha está al final
    pivot_df = pivot_df.sort("FECHA_INF")

    # Obtener la última fila (valores más recientes)
    last_row = pivot_df.tail(1)

    # Obtener las columnas numéricas (excluyendo FECHA_INF)
    numeric_cols = [col for col in pivot_df.columns if col != "FECHA_INF"]

    # Para cada columna numérica, dividir el valor más reciente por el valor de cada fila
    result_exprs = [pl.col("FECHA_INF")]

    for col in numeric_cols:
        # Obtener el valor más reciente para esta columna
        last_value = last_row.select(col).item()

        # Crear una expresión para dividir el valor más reciente por el valor de cada fila
        result_exprs.append((last_value / pl.col(col) - 1).alias(f"{col}"))

    # Aplicar las expresiones al DataFrame
    return pivot_df.select(result_exprs)


def add_row_statistics(relative_returns: pl.DataFrame) -> pl.DataFrame:
    """
    Agrega columnas de estadísticas por fila al DataFrame de retornos relativos.

    Args:
        relative_returns: DataFrame con retornos relativos calculados

    Returns:
        DataFrame con columnas adicionales de promedio, máximo y mínimo por fila
    """
    # Asegurarse de que estamos trabajando con un DataFrame regular
    if isinstance(relative_returns, pl.LazyFrame):
        relative_returns = relative_returns.collect()

    numeric_cols = [col for col in relative_returns.columns if col != "FECHA_INF"]

    return relative_returns.with_columns(
        pl.mean_horizontal(numeric_cols).alias("PROMEDIO_RENTABILIDAD"),
        pl.max_horizontal(numeric_cols).alias("MAX_RENTABILIDAD"),
        pl.min_horizontal(numeric_cols).alias("MIN_RENTABILIDAD"),
        pl.sum_horizontal(pl.col(c).is_not_null() for c in numeric_cols).alias("CANTIDAD_NO_NULOS"),
    )


