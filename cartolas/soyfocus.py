from cartolas.config import (
    SOYFOCUS_FUNDS,
    PARQUET_FILE_PATH,
    SOYFOCUS_PARQUET_FILE_PATH,
    SOYFOCUS_BY_RUN_PARQUET_FILE_PATH,
    SOYFOCUS_TAC_PARQUET_FILE_PATH,
)
from cartolas.read import read_parquet_cartolas_lazy
from cartolas.save import save_lazyframe_to_parquet
import polars as pl
from pathlib import Path
from datetime import date

# Lista de RUNs identificadores de los fondos SoyFocus
SOYFOCUS_RUNS: list[str] = list(SOYFOCUS_FUNDS.keys())
# Límite máximo permitido para los costos anuales (en porcentaje)
LIMITE_COSTOS_ANUAL: float = 0.5
# Fecha desde la cual se aplica el límite de costos
FECHA_INICIO_COSTOS: date = date(2024, 4, 1)
# Días en el año para cálculos anualizados
DIAS_ANUAL: int = 366


def create_soyfocus_parquet(
    allfunds_file: Path = PARQUET_FILE_PATH,
    soyfocus_file: Path = SOYFOCUS_PARQUET_FILE_PATH,
    sorted: bool = True,
    sort_columns: list[str] | None = None,
    descending: bool = False,
) -> pl.LazyFrame:
    """
    Crea un archivo parquet específico para los fondos SoyFocus con cálculos financieros.

    Esta función procesa los datos de los fondos SoyFocus realizando varios cálculos:
    - Filtra los fondos por RUN
    - Calcula patrimonios ajustados según circular CMF
    - Calcula gastos totales (afectos + no afectos)
    - Calcula costos totales (gastos + remuneraciones)
    - Calcula flujos netos de cuotas y monetarios
    - Obtiene valores históricos (valor cuota y patrimonio anterior)
    - Calcula rentabilidades y efectos en patrimonio

    Fórmulas principales:
    - PATRIMONIO_AJUSTADO = (CUOTAS_EN_CIRCULACION + CUOTAS_RESCATADAS - CUOTAS_APORTADAS) * VALOR_CUOTA
    - GASTOS_TOTALES = GASTOS_AFECTOS + GASTOS_NO_AFECTOS
    - COSTOS_TOTALES = REM_FIJA + REM_VARIABLE + GASTOS_TOTALES
    - FLUJO_NETO = CUOTAS_NETAS * VALOR_CUOTA
    - VALOR_CUOTA_AJUSTADO = VALOR_CUOTA * FACTOR_REPARTO * FACTOR_AJUSTE
    - RENTABILIDAD = VALOR_CUOTA_AJUSTADO / VALOR_CUOTA_ANTERIOR
    - EFECTO_PRECIO = DELTA_PATRIMONIO_NETO - FLUJO_NETO

    Args:
        allfunds_file (Path): Ruta al archivo parquet con datos de todos los fondos.
            Por defecto usa PARQUET_FILE_PATH.
        soyfocus_file (Path): Ruta donde se guardará el archivo filtrado.
            Por defecto usa SOYFOCUS_PARQUET_FILE_PATH.
        sorted (bool): Indica si se debe ordenar el resultado. Por defecto True.
        sort_columns (list[str] | None): Columnas para ordenar. Si es None y sorted=True,
            usa ["RUN_FM", "FECHA_INF"].
        descending (bool): Orden descendente (True) o ascendente (False).
            Por defecto False.

    Returns:
        pl.LazyFrame: DataFrame lazy con los datos procesados y calculados.
            Incluye todas las columnas originales más las calculadas:
            - PATRIMONIO_AJUSTADO: Patrimonio según circular CMF
            - GASTOS_TOTALES: Suma de gastos afectos y no afectos
            - COSTOS_TOTALES: Suma de gastos y remuneraciones
            - PATRIMONIO_AJUSTADO_GASTOS: Patrimonio ajustado incluyendo gastos
            - PATRIMONIO_AJUSTADO_COSTOS: Patrimonio ajustado incluyendo todos los costos
            - CUOTAS_NETAS: Diferencia entre cuotas aportadas y rescatadas
            - FLUJO_NETO: Valor monetario del flujo neto de cuotas
            - VALOR_CUOTA_ANTERIOR: Valor cuota del día anterior
            - PATRIMONIO_NETO_ANTERIOR: Patrimonio neto del día anterior
            - VALOR_CUOTA_AJUSTADO: Valor cuota ajustado por factores
            - RENTABILIDAD: Variación del valor cuota ajustado
            - DELTA_PATRIMONIO_NETO: Cambio en patrimonio neto
            - EFECTO_PRECIO_EN_DELTA_PATRIMONIO: Efecto precio en el cambio patrimonial
    """
    # Define las columnas de ordenamiento por defecto si no se especifican
    if sort_columns is None and sorted:
        sort_columns = ["RUN_FM", "FECHA_INF"]

    # Lee los datos y comienza el procesamiento
    lazy_df = read_parquet_cartolas_lazy(parquet_path=allfunds_file, sorted=False)
    lazy_df = (
        # Filtra solo los fondos SoyFocus
        lazy_df.filter(pl.col("RUN_FM").is_in(SOYFOCUS_RUNS))
        .drop("RUN_ADM")
        # Ordena para asegurar cálculos correctos de valores anteriores
        .sort(["RUN_FM", "SERIE", "FECHA_INF"])
        # Calcula el patrimonio ajustado según circular CMF
        .with_columns(
            (
                (
                    pl.col("CUOTAS_EN_CIRCULACION")
                    + pl.col("CUOTAS_RESCATADAS")
                    - pl.col("CUOTAS_APORTADAS")
                )
                * pl.col("VALOR_CUOTA")
            ).alias("PATRIMONIO_AJUSTADO")
        )
        # Calcula gastos totales sumando afectos y no afectos
        .with_columns(
            (pl.col("GASTOS_AFECTOS") + pl.col("GASTOS_NO_AFECTOS")).alias(
                "GASTOS_TOTALES"
            )
        )
        # Calcula costos totales incluyendo remuneraciones
        .with_columns(
            (
                pl.col("REM_FIJA") + pl.col("REM_VARIABLE") + pl.col("GASTOS_TOTALES")
            ).alias("COSTOS_TOTALES")
        )
        # Ajusta el patrimonio considerando gastos
        .with_columns(
            (pl.col("PATRIMONIO_AJUSTADO") + pl.col("GASTOS_TOTALES")).alias(
                "PATRIMONIO_AJUSTADO_GASTOS"
            )
        )
        # Ajusta el patrimonio considerando todos los costos
        .with_columns(
            (pl.col("PATRIMONIO_AJUSTADO") + pl.col("COSTOS_TOTALES")).alias(
                "PATRIMONIO_AJUSTADO_COSTOS"
            )
        )
        # Calcula el flujo neto de cuotas
        .with_columns(
            (pl.col("CUOTAS_APORTADAS") - pl.col("CUOTAS_RESCATADAS")).alias(
                "CUOTAS_NETAS"
            )
        )
        # Calcula el flujo neto en valor monetario
        .with_columns(
            (pl.col("CUOTAS_NETAS") * pl.col("VALOR_CUOTA").round(0)).alias(
                "FLUJO_NETO"
            )
        )
        # Obtiene el valor cuota del día anterior para cada fondo y serie
        .with_columns(
            pl.col("VALOR_CUOTA")
            .shift(1)
            .over(["RUN_FM", "SERIE"])
            .alias("VALOR_CUOTA_ANTERIOR")
        )
        # Obtiene el patrimonio neto del día anterior para cada fondo y serie
        .with_columns(
            pl.col("PATRIMONIO_NETO")
            .shift(1)
            .over(["RUN_FM", "SERIE"])
            .alias("PATRIMONIO_NETO_ANTERIOR")
        )
        # Calcula el valor cuota ajustado por factores
        .with_columns(
            (
                pl.col("VALOR_CUOTA")
                * pl.col("FACTOR DE REPARTO")
                * pl.col("FACTOR DE AJUSTE")
            ).alias("VALOR_CUOTA_AJUSTADO")
        )
        # Calcula la variación porcentual del valor cuota ajustado
        .with_columns(
            (pl.col("VALOR_CUOTA_AJUSTADO") / pl.col("VALOR_CUOTA_ANTERIOR")).alias(
                "RENTABILIDAD"
            )
        )
        .with_columns(
            (pl.col("PATRIMONIO_NETO") - pl.col("PATRIMONIO_NETO_ANTERIOR")).alias(
                "DELTA_PATRIMONIO_NETO"
            )
        )
        .with_columns(
            ((pl.col("DELTA_PATRIMONIO_NETO") - pl.col("FLUJO_NETO")).round(0)).alias(
                "EFECTO_PRECIO_EN_DELTA_PATRIMONIO"
            )
        )
    )

    # Guarda los resultados en formato parquet
    save_lazyframe_to_parquet(lazy_df=lazy_df, filename=soyfocus_file, unique=True)

    # Retorna el DataFrame ordenado según los parámetros especificados
    return lazy_df.sort(by=sort_columns, descending=descending) if sorted else lazy_df


def soy_focus_by_run(
    lazy_df: pl.LazyFrame,
    soyfocus_by_run_file: Path = SOYFOCUS_BY_RUN_PARQUET_FILE_PATH,
    sorted: bool = True,
    sort_columns: list[str] | None = None,
    descending: bool = False,
) -> pl.LazyFrame:
    # TODO: Sacar de la función y hacer variables globales
    # TODO: Ver la lógica del efecto de los factores de reparto y ajuste a nivel de fondo
    columns = [
        "RUN_FM",
        "FECHA_INF",
        "CUOTAS_APORTADAS",
        "CUOTAS_RESCATADAS",
        "CUOTAS_EN_CIRCULACION",
        "PATRIMONIO_NETO",
        "NUM_PARTICIPES",
        "NUM_PARTICIPES_INST",
        "REM_FIJA",
        "REM_VARIABLE",
        "GASTOS_AFECTOS",
        "GASTOS_NO_AFECTOS",
        "COMISION_INVERSION",
        "COMISION_RESCATE",
        "PATRIMONIO_AJUSTADO",
        "GASTOS_TOTALES",
        "COSTOS_TOTALES",
        "PATRIMONIO_AJUSTADO_GASTOS",
        "PATRIMONIO_AJUSTADO_COSTOS",
        "CUOTAS_NETAS",
        "FLUJO_NETO",
        "PATRIMONIO_NETO_ANTERIOR",
        "DELTA_PATRIMONIO_NETO",
        "EFECTO_PRECIO_EN_DELTA_PATRIMONIO",
    ]
    grouping_columns = ["RUN_FM", "FECHA_INF"]
    agg_list = [pl.col(x).sum() for x in columns if x not in grouping_columns]
    print(agg_list)
    lazy_df = (
        lazy_df.select(columns)
        .group_by(grouping_columns)
        .agg(agg_list)
        .sort(["RUN_FM", "FECHA_INF"])
    )
    return lazy_df


def create_tac_report(lazy_df: pl.LazyFrame):
    pass


if __name__ == "__main__":
    # Ejecuta el procesamiento y guarda los resultados
    lazy_df = create_soyfocus_parquet()
    print(lazy_df.collect().head())
    # Exporta los resultados a CSV para revisión
    lazy_df.collect().write_csv("cartolas/csv/soyfocus.csv")
    df2 = soy_focus_by_run(lazy_df)
    print(df2.collect().tail())
    print(df2.collect().columns)


# def create_soy_focus_by_run(lazy_df: pl.LazyFrame, soy_focus_by_run_file: Path = SOYFOCUS_BY_RUN_PARQUET_FILE_PATH, sorted: bool = True, sort_columns: list[str] = None) -> pl.LazyFrame:

#     sorted_columns = ["RUN_FM", "FECHA_INF"] if sort_columns is None else sort_columns
#     print ([x for x in lazy_df.columns if "FACTOR" not in x and "RUN_FM" not in x and "FECHA_INF" not in x])
#     lazy_df = lazy_df.group_by(["RUN_FM", "FECHA_INF"]).agg(
#         pl.col("CUOTAS_APORTADAS").sum(),
#         pl.col("CUOTAS_RESCATADAS").sum(),
#         pl.col("CUOTAS_EN_CIRCULACION").sum(),
#         pl.col("VALOR_CUOTA").sum(),
#         pl.col("PATRIMONIO_NETO").sum(),
#         pl.col("NUM_PARTICIPES").sum(),
#         pl.col("REM_FIJA").sum(),
#         pl.col("REM_VARIABLE").sum(),
#         pl.col("GASTOS_AFECTOS").sum(),
#         pl.col("GASTOS_NO_AFECTOS").sum(),
#         pl.col("COMISION_INVERSION").sum(),
#         pl.col("COMISION_RESCATE").sum(),
#     )

#     #other_df = lazy_df.group_by(["RUN_FM", "FECHA_INF"]).agg()
#     return lazy_df.sort(sorted_columns) if sorted else lazy_df


# def create_soyfocus_by_run(gfgfgthht
#     soyfocus_file: Path = SOYFOCUS_PARQUET_FILE_PATH,
#     soyfocus_by_run_file: Path = SOYFOCUS_BY_RUN_PARQUET_FILE_PATH,
# ) -> pl.LazyFrame:
#     """
#     Crea un archivo parquet con datos agregados por RUN de los fondos SoyFocus.

#     Esta función lee los datos de los fondos SoyFocus y los agrupa por RUN y fecha,
#     calculando las sumas de varios indicadores financieros.

#     Args:
#         soyfocus_file (Path): Ruta al archivo parquet de SoyFocus.
#             Por defecto usa SOYFOCUS_PARQUET_FILE_PATH desde config.
#         soyfocus_by_run_file (Path): Ruta donde se guardará el archivo agregado.
#             Por defecto usa SOYFOCUS_BY_RUN_PARQUET_FILE_PATH desde config.

#     Returns:
#         pl.LazyFrame: DataFrame lazy con los datos agregados por RUN.
#     """
#     lazy_df = read_parquet_cartolas_lazy(parquet_path=soyfocus_file)

#     # Selecciona las columnas relevantes y realiza la agregación por RUN y fecha
#     lazy_df = (
#         lazy_df.select(
#             [
#                 "RUN_FM",
#                 "FECHA_INF",
#                 "SERIE",
#                 "CUOTAS_APORTADAS",
#                 "CUOTAS_RESCATADAS",
#                 "CUOTAS_EN_CIRCULACION",
#                 "VALOR_CUOTA",
#                 "PATRIMONIO_NETO",
#                 "NUM_PARTICIPES",
#                 "REM_FIJA",
#                 "REM_VARIABLE",
#                 "GASTOS_AFECTOS",
#                 "GASTOS_NO_AFECTOS",
#                 "COMISION_INVERSION",
#                 "COMISION_RESCATE",
#                 "FACTOR DE AJUSTE",
#                 "FACTOR DE REPARTO",
#             ]
#         )
#         .group_by(["RUN_FM", "FECHA_INF"])
#         .agg(
#             # Calcula la suma de cada indicador financiero
#             pl.col("CUOTAS_APORTADAS").sum(),
#             pl.col("CUOTAS_RESCATADAS").sum(),
#             pl.col("CUOTAS_EN_CIRCULACION").sum(),
#             pl.col("VALOR_CUOTA").sum(),
#             pl.col("PATRIMONIO_NETO").sum(),
#             pl.col("NUM_PARTICIPES").sum(),
#             pl.col("REM_FIJA").sum(),
#             pl.col("REM_VARIABLE").sum(),
#             pl.col("GASTOS_AFECTOS").sum(),
#             pl.col("GASTOS_NO_AFECTOS").sum(),
#             pl.col("COMISION_INVERSION").sum(),
#             pl.col("COMISION_RESCATE").sum(),
#             pl.col("FACTOR DE AJUSTE").sum(),
#             pl.col("FACTOR DE REPARTO").sum(),
#         )
#         .sort(["RUN_FM", "FECHA_INF"])
#     )

#     save_lazyframe_to_parquet(
#         lazy_df=lazy_df, filename=soyfocus_by_run_file, unique=True
#     )

#     return lazy_df


# def create_soyfocus_tac(
#     soyfocus_by_run_file: Path = SOYFOCUS_BY_RUN_PARQUET_FILE_PATH,
#     soyfocus_tac_file: Path = SOYFOCUS_TAC_PARQUET_FILE_PATH,
# ):
#     """
#     Calcula las tasas anuales de costos (TAC) para los fondos SoyFocus.

#     Esta función realiza cálculos detallados de costos y tasas según la circular 1738 CMF,
#     incluyendo ajustes de patrimonio y límites de costos anuales.

#     Args:
#         soyfocus_by_run_file (Path): Ruta al archivo parquet con datos agregados por RUN.
#             Por defecto usa SOYFOCUS_BY_RUN_PARQUET_FILE_PATH desde config.
#     """
#     lazy_df = (
#         create_soyfocus_by_run(soyfocus_by_run_file)
#         # Calcula el patrimonio ajustado según la circular 1738 CMF
#         .with_columns(
#             (
#                 (
#                     pl.col("CUOTAS_EN_CIRCULACION")
#                     + pl.col("CUOTAS_RESCATADAS")
#                     - pl.col("CUOTAS_APORTADAS")
#                 )
#                 * pl.col("VALOR_CUOTA")
#             ).alias("PATRIMONIO_AJUSTADO")
#         )
#         # Calcula los costos totales sumando gastos afectos y no afectos
#         .with_columns(
#             (+pl.col("GASTOS_AFECTOS") + pl.col("GASTOS_NO_AFECTOS")).alias(
#                 "COSTOS_TOTALES"
#             )
#         )
#         .with_columns(
#             (
#                 +pl.col("COSTOS_TOTALES") + pl.col("REM_FIJA") + pl.col("REM_VARIABLE")
#             ).alias("COSTOS_Y_REMUNERACIONES_TOTALES")
#         )
#         .with_columns(
#             (pl.col("PATRIMONIO_AJUSTADO") + pl.col("COSTOS_TOTALES")).alias(
#                 "PATRIMONIO_AJUSTADO_COSTOS"
#             )
#         )
#         .with_columns(
#             (
#                 pl.col("PATRIMONIO_AJUSTADO")
#                 + pl.col("COSTOS_Y_REMUNERACIONES_TOTALES")
#             ).alias("PATRIMONIO_AJUSTADO_COSTOS_Y_REMUNERACIONES")
#         )
#         .with_columns(
#             (
#                 (100 * pl.col("COSTOS_TOTALES") / pl.col("PATRIMONIO_AJUSTADO_COSTOS"))
#                 .fill_nan(0)
#                 .fill_null(0)
#             ).alias("TASA_COSTOS_DIARIA_%")
#         )
#         .with_columns(
#             (
#                 (
#                     100
#                     * pl.col("COSTOS_Y_REMUNERACIONES_TOTALES")
#                     / pl.col("PATRIMONIO_AJUSTADO_COSTOS_Y_REMUNERACIONES")
#                 )
#                 .fill_nan(0)
#                 .fill_null(0)
#             ).alias("TASA_COSTOS_DIARIA_%")
#         )
#         .with_columns(
#             (pl.col("TASA_COSTOS_DIARIA_%") * DIAS_ANUAL).alias(
#                 "TASA_COSTOS_ANUALIZADA_%"
#             )
#         )
#         .with_columns(
#             (pl.col("TASA_COSTOS_Y_REMUNERACIONES_DIARIA_%") * DIAS_ANUAL).alias(
#                 "TASA_COSTOS_Y_REMUNERACIONES_ANUALIZADA_%"
#             )
#         )
#         .with_columns(
#             pl.when(pl.col("FECHA_INF") > FECHA_INICIO_COSTOS)
#             .then(pl.lit(LIMITE_COSTOS_ANUAL))
#             .otherwise(pl.lit(0))
#             .alias("LIMITE_COSTOS_ANUAL")
#         )
#         .with_columns(
#             (
#                 (LIMITE_COSTOS_ANUAL * pl.col("PATRIMONIO_AJUSTADO"))
#                 / (DIAS_ANUAL - LIMITE_COSTOS_ANUAL)
#             ).alias("LIMITE_COSTOS_ANUAL_PATRIMONIO")
#         )
#         .with_columns(
#             (pl.col("LIMITE_COSTOS_ANUAL_PATRIMONIO") / DIAS_ANUAL).alias(
#                 "LIMITE_COSTOS_DIARIO_CLP"
#             )
#         )
#         .with_columns(
#             (pl.col("TASA_COSTOS_ANUALIZADA_%") < LIMITE_COSTOS_ANUAL).alias(
#                 "CUMPLE_LIMITE_COSTOS_ANUAL"
#             )
#         )
#     )
#     save_lazyframe_to_parquet(lazy_df=lazy_df, filename=soyfocus_tac_file, unique=True)
#     return lazy_df


# def create_soyfocus_returns():
#     pass


# def read_soyfocus_parquet(
#     parquet_path: Path = SOYFOCUS_PARQUET_FILE_PATH, include_series: bool = True
# ):
#     """
#     Lee un archivo parquet que contiene datos de los fondos SoyFocus.

#     Esta función lee un archivo parquet que contiene datos de los fondos SoyFocus y lo devuelve
#     como un DataFrame Polars.

#     Args:
#         parquet_path (Path): Ruta al archivo parquet que contiene los datos de los fondos SoyFocus.
#             Por defecto usa SOYFOCUS_PARQUET_FILE_PATH desde config.

#     Returns:
#         pl.DataFrame: DataFrame Polars que contiene los datos de los fondos SoyFocus.
#     """
#     orden_columnas = (
#         ["FECHA_INF", "RUN_FM", "SERIE"] if include_series else ["FECHA_INF", "RUN_FM"]
#     )
#     return read_parquet_cartolas_lazy(parquet_path=parquet_path, sorted=False).sort(
#         orden_columnas
#     )


# if __name__ == "__main__":
#     #create_soyfocus_parquet()
#     create_soyfocus_by_run()
#     #create_soyfocus_tac()
#     #create_soyfocus_returns()
