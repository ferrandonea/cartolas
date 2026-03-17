from comparador.merge import merge_cartolas_with_categories
import polars as pl
from datetime import date
import numpy as np
from utiles.polars_utils import add_cumulative_returns
from utiles.fechas import (
    date_n_months_ago,
    date_n_years_ago,
    ultimo_dia_mes_anterior,
    ultimo_dia_año_anterior,
)


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
        "1M": ultimo_dia_mes_anterior(max_date),
        "3M": ultimo_dia_mes_anterior(date_n_months_ago(2, max_date)),
        "6M": ultimo_dia_mes_anterior(date_n_months_ago(5, max_date)),
        "1Y": date_n_years_ago(1, max_date),
        "3Y": date_n_years_ago(3, max_date),
        "5Y": date_n_years_ago(5, max_date),
        "YTD": ultimo_dia_año_anterior(max_date),
    }

    unique_dates = set(selected_dates.values())
    filtered = pivot_df.filter(pl.col("FECHA_INF").is_in(list(unique_dates)))
    rows = []
    for label, d in selected_dates.items():
        match = filtered.filter(pl.col("FECHA_INF") == d)
        if match.height > 0:
            rows.append(match.with_columns(pl.lit(label).alias("PERIODO")))
    return pl.concat(rows)


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

    # Obtener las columnas numéricas (excluyendo FECHA_INF)
    numeric_cols = [col for col in relative_returns.columns if col != "FECHA_INF"]

    # Crear un nuevo DataFrame con solo las columnas numéricas
    numeric_df = relative_returns.select(numeric_cols)

    # Convertir a numpy para calcular estadísticas por fila
    numeric_array = numeric_df.to_numpy()

    # Calcular estadísticas por fila (ignorando NaN)
    mean_values = np.nanmean(numeric_array, axis=1)
    max_values = np.nanmax(numeric_array, axis=1)
    min_values = np.nanmin(numeric_array, axis=1)

    # Contar valores no nulos por fila
    non_null_counts = np.sum(~np.isnan(numeric_array), axis=1)

    # Agregar las estadísticas al DataFrame original
    result_df = relative_returns.with_columns(
        [
            pl.Series("PROMEDIO_RENTABILIDAD", mean_values),
            pl.Series("MAX_RENTABILIDAD", max_values),
            pl.Series("MIN_RENTABILIDAD", min_values),
            pl.Series("CANTIDAD_NO_NULOS", non_null_counts),
        ]
    )

    return result_df


