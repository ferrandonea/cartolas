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


def generate_cla_dates(input_date: date = date.today()) -> dict[int, date]:
    """
    Genera un diccionario de fechas clave (CLA) a partir de una fecha base.

    Args:
        input_date (date): Fecha base desde la cual calcular las fechas CLA.

    Returns:
        dict[int, date]: Diccionario con claves en meses/años y fechas correspondientes.
    """
    current_report_date = ultimo_dia_mes_anterior(input_date)
    print (f"{current_report_date = }")
    cla_dates = {
        **{mes: date_n_months_ago(mes, current_report_date) for mes in MESES_CLA},
        **{año * 12: date_n_years_ago(año, current_report_date) for año in AÑOS_CLA},
        -1: ultimo_dia_año_anterior(current_report_date),
        0: current_report_date,
    }

    return cla_dates


def generate_cla_data(input_date: date = date.today()) ->pl.DataFrame:
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
        pl.col("FECHA_INF").is_in(list(generate_cla_dates(input_date=input_date).values()))
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


    # Esto genera las rentabilidades de cada fondo por período
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

    df.write_csv("cla_data.csv")
    #Hasta acá está bien
    
    promedios = (
    df.group_by(["FECHA_INF", "CATEGORIA"])
      .agg([
            pl.col("RENTABILIDAD_HASTA_FECHA").mean().alias("PROMEDIO_RENTABILIDAD_HASTA_FECHA")
        ])
        .sort(["CATEGORIA", "FECHA_INF"])
    )
    print(promedios)
    

    promedios = (
    df.group_by(["FECHA_INF", "CATEGORIA"])
      .agg([
          pl.col("RENTABILIDAD_HASTA_FECHA").mean().alias("PROMEDIO_RENTABILIDAD_HASTA_FECHA"),
            pl.struct(["RUN_FM", "SERIE"]).n_unique().alias("NUM_FONDOS_SERIES")
        ]
    ))
    print(promedios)
    promedios.write_csv("promedios.csv")
    
    # Mapping de benchmarks: categoría -> (RUN_FM, SERIE)
    categories_mapping = {
        "BALANCEADO CONSERVADO": (9810, "B"),
        "BALANCEADO MODERADO": (9809, "B"),
        "BALANCEADO AGRESIVO": (9811, "B"),
    }

    # Crear un DataFrame con los benchmarks
    bench_df = pl.DataFrame([
        {"RUN_FM": run, "SERIE": serie, "CATEGORIA": categoria}
        for categoria, (run, serie) in categories_mapping.items()
    ])

    # Asegurar que RUN_FM tenga el mismo tipo en ambos DataFrames
    df = df.with_columns([
        pl.col("RUN_FM").cast(pl.Int64)
    ])
    bench_df = bench_df.with_columns([
        pl.col("RUN_FM").cast(pl.Int64)
    ])

    # Calcular el ranking dentro de cada CATEGORIA y FECHA_INF
    df_ranked = (
        df.sort("RENTABILIDAD_HASTA_FECHA", descending=True)
        .with_columns([
            pl.col("RENTABILIDAD_HASTA_FECHA")
                .rank("dense", descending=True)
                .over(["CATEGORIA", "FECHA_INF"])
                .alias("RANK_EN_CATEGORIA"),
            pl.count()
                .over(["CATEGORIA", "FECHA_INF"])
                .alias("TOTAL_FONDOS_EN_CATEGORIA")
        ])
    )

    # Filtrar benchmarks y obtener su posición
    bench_ranks = (
        df_ranked.join(bench_df, on=["RUN_FM", "SERIE", "CATEGORIA"], how="inner")
                .select([
                    "FECHA_INF", 
                    "CATEGORIA", 
                    "RUN_FM", 
                    "SERIE", 
                    "RANK_EN_CATEGORIA", 
                    "TOTAL_FONDOS_EN_CATEGORIA"
                ])
                .sort(["CATEGORIA", "FECHA_INF"])
    )
    print (bench_ranks)
    
    # Unir promedios con los rankings de benchmark
    promedios_completo = (
        promedios.join(
            bench_ranks, 
            on=["CATEGORIA", "FECHA_INF"], 
            how="left"
        )
    )
    print(promedios_completo)