from utiles.fechas import (
    date_n_months_ago,
    date_n_years_ago,
    ultimo_dia_año_anterior,
    ultimo_dia_mes_anterior,
)
from datetime import date
from comparador.merge import merge_cartolas_with_categories
import polars as pl

MESES_CLA = [1, 3, 6]
AÑOS_CLA = [1, 3, 5]
CATEGORIAS_CLA = ["CONSERVADOR", "MODERADO", "AGRESIVO"]
CATEGORIAS_EM = [f"BALANCEADO {categoria}" for categoria in CATEGORIAS_CLA]


def generate_cla_dates(input_date: date) -> dict[int, date]:
    """
    Genera un diccionario de fechas clave (CLA) a partir de una fecha base.

    Args:
        input_date (date): Fecha base desde la cual calcular las fechas CLA.

    Returns:
        dict[int, date]: Diccionario con claves en meses/años y fechas correspondientes.
    """
    current_report_date = ultimo_dia_mes_anterior(input_date)

    cla_dates = {
        **{mes: date_n_months_ago(mes, current_report_date) for mes in MESES_CLA},
        **{año * 12: date_n_years_ago(año, current_report_date) for año in AÑOS_CLA},
        -1: ultimo_dia_año_anterior(current_report_date),
        0: current_report_date,
    }

    return cla_dates


print(generate_cla_dates(date(2025, 4, 15)))


def generate_cla_data():
    RELEVANT_COLUMNS = [
        "RUN_FM",
        "SERIE",
        "FECHA_INF",
        "CATEGORIA",
        "RENTABILIDAD_ACUMULADA",
    ]
    # Generar los datos de CLA
    df = merge_cartolas_with_categories()
    # Agregar las rentabilidades acumuladas
    df = add_cumulative_returns(df)
    # Filtrar las categorías relevantes
    df = df.filter(pl.col("CATEGORIA").is_in(CATEGORIAS_EM))
    # Filtrar las columnas relevantes
    df = df.collect().select(RELEVANT_COLUMNS)
    # filtro las fechas relevantes
    df = df.filter(
        pl.col("FECHA_INF").is_in(list(generate_cla_dates(date(2025, 4, 15)).values()))
    )
    return df


def add_cumulative_returns(df: pl.DataFrame):
    # Ordenar el DataFrame por RUN_FM, SERIE y FECHA_INF
    sorted_df = df.sort(["RUN_FM", "SERIE", "FECHA_INF"])

    # Agrupar por RUN_FM y SERIE, y calcular la rentabilidad acumulada
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


if __name__ == "__main__":
    input_date = date(2025, 4, 15)
    print(f"{input_date = }")
    print(f"{date_n_months_ago(1, input_date) = }")
    print(f"{ultimo_dia_año_anterior(input_date) = }")
    print(f"{ultimo_dia_mes_anterior(input_date) = }")
    print()
    current_report_date = ultimo_dia_mes_anterior(input_date)
    print(f"{current_report_date = }")
    print(f"{date_n_months_ago(1, current_report_date) = }")
    print(f"{ultimo_dia_año_anterior(current_report_date) = }")
    print(f"{ultimo_dia_mes_anterior(current_report_date) = }")
    print("No input date")
    print(f"{ultimo_dia_mes_anterior() = }")
    print()
    import pprint

    pprint.pprint(generate_cla_dates(input_date))
    df = generate_cla_data()
    print(df.filter(pl.col("RUN_FM") == 9811))


