from datetime import date

import polars as pl

from comparador.merge import merge_cartolas_with_categories
from utiles.fechas import (date_n_months_ago, date_n_years_ago,
                           ultimo_dia_año_anterior, ultimo_dia_mes_anterior)

# Constantes para los períodos de análisis
MESES_CLA = [1, 3, 6]  # Períodos mensuales a analizar
AÑOS_CLA = [1, 3, 5]  # Períodos anuales a analizar
CATEGORIAS_CLA = ["CONSERVADOR", "MODERADO", "AGRESIVO"]  # Categorías base de fondos
# Genera las categorías completas agregando el prefijo "BALANCEADO"
CATEGORIAS_ELMER = [f"BALANCEADO {categoria}" for categoria in CATEGORIAS_CLA]
RELEVANT_COLUMNS = ["RUN_FM", "SERIE", "FECHA_INF", "CATEGORIA", "RENTABILIDAD_ACUMULADA", "RUN_SOYFOCUS", "SERIE_SOYFOCUS"]


def generate_cla_dates(input_date: date = date.today()) -> dict[int, date]:
    """
    Genera un diccionario con las fechas relevantes para el análisis CLA.

    Esta función calcula las fechas para diferentes períodos de análisis:
    - Fechas para períodos mensuales (1, 3, 6 meses)
    - Fechas para períodos anuales (1, 3, 5 años)
    - Fecha del último día del año anterior
    - Fecha actual del reporte

    Args:
        input_date (date): Fecha base para realizar los cálculos. Por defecto usa la fecha actual.

    Returns:
        dict[int, date]: Diccionario donde:
            - Las claves son los períodos en meses (ej: 1, 3, 6, 12, 36, 60)
            - -1 representa el último día del año anterior
            - 0 representa la fecha actual del reporte
            - Los valores son las fechas correspondientes
    """
    # Obtener el último día del mes anterior como fecha base del reporte
    current_report_date = ultimo_dia_mes_anterior(input_date)
    print(f"{current_report_date = }")

    # Construir el diccionario de fechas combinando:
    cla_dates = {
        # Fechas para períodos mensuales
        **{mes: date_n_months_ago(mes, current_report_date) for mes in MESES_CLA},
        # Fechas para períodos anuales (convertidos a meses)
        **{año * 12: date_n_years_ago(año, current_report_date) for año in AÑOS_CLA},
        # Fechas especiales
        -1: ultimo_dia_año_anterior(current_report_date),  # Último día del año anterior
        0: current_report_date,  # Fecha actual del reporte
    }

    return cla_dates


def generate_cla_data(input_date: date = date.today()) -> pl.DataFrame:
    """
    Genera un DataFrame con los datos necesarios para el análisis CLA.

    Esta función procesa los datos de las cartolas, aplicando filtros y transformaciones
    necesarias para obtener la información relevante para el análisis CLA.

    Args:
        input_date (date): Fecha base para el análisis. Por defecto usa la fecha actual.

    Returns:
        pl.DataFrame: DataFrame con las columnas relevantes filtradas y procesadas
    """
    # Obtener y procesar los datos base
    df = merge_cartolas_with_categories()

    # Calcular rentabilidades acumuladas
    df = add_cumulative_returns(df)

    # Filtrar solo las categorías que nos interesan (BALANCEADO CONSERVADOR, etc)
    df = df.filter(pl.col("CATEGORIA").is_in(CATEGORIAS_ELMER))

    # Seleccionar solo las columnas relevantes
    df = df.collect().select(RELEVANT_COLUMNS)

    # Filtrar solo las fechas necesarias para el análisis CLA
    df = df.filter(
        pl.col("FECHA_INF").is_in(
            list(generate_cla_dates(input_date=input_date).values())
        )
    )
    df = add_soyfocus_returns(df)

    return df


def add_cumulative_returns(df: pl.DataFrame):
    """
    Calcula las rentabilidades acumuladas para cada fondo y serie.

    Esta función procesa el DataFrame para calcular la rentabilidad acumulada
    utilizando el producto acumulativo de las rentabilidades diarias.

    Args:
        df (pl.DataFrame): DataFrame con las rentabilidades diarias por fondo y serie

    Returns:
        pl.DataFrame: DataFrame original con una nueva columna de rentabilidad acumulada
    """
    # Ordenar el DataFrame para asegurar el cálculo correcto de acumulados
    sorted_df = df.sort(["RUN_FM", "SERIE", "FECHA_INF"])

    # Calcular la rentabilidad acumulada por fondo y serie
    return sorted_df.with_columns(
        [
            pl.col("RENTABILIDAD_DIARIA_PESOS")
            .cum_prod()  # Producto acumulativo
            .over(["RUN_FM", "SERIE"])  # Agrupado por fondo y serie
            .fill_nan(1)  # Reemplazar NaN por 1
            .fill_null(1)  # Reemplazar valores nulos por 1
            .alias("RENTABILIDAD_ACUMULADA")
        ]
    )


def add_soyfocus_returns(df: pl.DataFrame) -> pl.DataFrame:
    """
    Agrega la rentabilidad acumulada del fondo SoyFocus correspondiente.
    """
    # Primero convertimos RUN_SOYFOCUS a u16 para que coincida con RUN_FM
    df = df.with_columns([
        pl.col("RUN_SOYFOCUS").cast(pl.UInt16)
    ])

    # Hacemos el join solo para obtener la rentabilidad del fondo SoyFocus
    return df.join(
        df.select(["RUN_FM", "SERIE", "FECHA_INF", "RENTABILIDAD_ACUMULADA"]),
        left_on=["RUN_SOYFOCUS", "SERIE_SOYFOCUS", "FECHA_INF"],
        right_on=["RUN_FM", "SERIE", "FECHA_INF"],
        how="left"
    ).rename({
        "RENTABILIDAD_ACUMULADA_right": "RENTABILIDAD_AC_SOYFOCUS"
    })




def main():
    df = generate_cla_data()    
    print(df)    # Esto genera las rentabilidades de cada fondo por período
    df = (
        df.sort(["RUN_FM", "SERIE", "FECHA_INF"])
        .with_columns([
            pl.col("RENTABILIDAD_ACUMULADA")
                .reverse()
                .first()
                .over(["RUN_FM", "SERIE"])
                .alias("RENT_ACUM_ULTIMA")
        ])
        .with_columns([
            (pl.col("RENT_ACUM_ULTIMA") / pl.col("RENTABILIDAD_ACUMULADA"))
                .alias("RENTABILIDAD_HASTA_FECHA")
        ])
    )
    print (df)
    df.write_csv("cla_data.csv")

if __name__ == "__main__":
    main()