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
from typing import Optional, List

# Lista de RUNs identificadores de los fondos SoyFocus
SOYFOCUS_RUNS: list[str] = list(SOYFOCUS_FUNDS.keys())
# Límite máximo permitido para los costos anuales (en porcentaje)
LIMITE_GASTOS_ANUAL: float = 0.5
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
        .with_columns(pl.col("PATRIMONIO_NETO_ANTERIOR").fill_null(0).fill_nan(0))
    )

    # Guarda los resultados en formato parquet
    save_lazyframe_to_parquet(lazy_df=lazy_df, filename=soyfocus_file, unique=True)

    # Retorna el DataFrame ordenado según los parámetros especificados
    return lazy_df.sort(by=sort_columns, descending=descending) if sorted else lazy_df


def soy_focus_by_run(
    lazy_df: pl.LazyFrame,
    soyfocus_by_run_file: Path = SOYFOCUS_BY_RUN_PARQUET_FILE_PATH,
    sorted: bool = True,
    sort_columns: Optional[List[str]] = None,
    descending: bool = False,
) -> pl.LazyFrame:
    """
    Agrupa y suma las métricas financieras por RUN de fondo y fecha.

    Esta función toma un LazyFrame con datos detallados de fondos y realiza una agregación
    a nivel de RUN y fecha, sumando todas las métricas financieras relevantes como patrimonio,
    cuotas, gastos y comisiones.

    Args:
        lazy_df (pl.LazyFrame): DataFrame diferido con los datos de los fondos
        soyfocus_by_run_file (Path): Ruta donde se guardará el archivo resultante.
            Por defecto usa SOYFOCUS_BY_RUN_PARQUET_FILE_PATH
        sorted (bool): Indica si el resultado debe ordenarse. Por defecto True
        sort_columns (Optional[List[str]]): Lista de columnas para ordenar el resultado.
            Si es None y sorted es True, se ordena por RUN_FM y FECHA_INF
        descending (bool): Indica si el ordenamiento debe ser descendente. Por defecto False

    Returns:
        pl.LazyFrame: LazyFrame agrupado por RUN_FM y FECHA_INF con las sumas de todas
            las métricas financieras

    Note:
        Las columnas que se agregan incluyen:
        - Métricas de cuotas (aportadas, rescatadas, en circulación)
        - Métricas de patrimonio (neto, ajustado)
        - Métricas de participantes
        - Métricas de gastos y comisiones
        - Métricas de flujos y efectos en patrimonio
    """
    # Definición de columnas a procesar
    columns = [
        "RUN_FM",  # Identificador único del fondo
        "FECHA_INF",  # Fecha de la información
        "CUOTAS_APORTADAS",  # Cuotas nuevas aportadas al fondo
        "CUOTAS_RESCATADAS",  # Cuotas retiradas del fondo
        "CUOTAS_EN_CIRCULACION",  # Total de cuotas vigentes
        "PATRIMONIO_NETO",  # Valor total del fondo
        "NUM_PARTICIPES",  # Número total de partícipes
        "NUM_PARTICIPES_INST",  # Número de partícipes institucionales
        "REM_FIJA",  # Remuneración fija
        "REM_VARIABLE",  # Remuneración variable
        "GASTOS_AFECTOS",  # Gastos afectos a límites
        "GASTOS_NO_AFECTOS",  # Gastos no afectos a límites
        "COMISION_INVERSION",  # Comisiones por inversión
        "COMISION_RESCATE",  # Comisiones por rescate
        "PATRIMONIO_AJUSTADO",  # Patrimonio con ajustes
        "GASTOS_TOTALES",  # Suma total de gastos
        "COSTOS_TOTALES",  # Suma total de costos
        "PATRIMONIO_AJUSTADO_GASTOS",  # Patrimonio ajustado por gastos
        "PATRIMONIO_AJUSTADO_COSTOS",  # Patrimonio ajustado por costos
        "CUOTAS_NETAS",  # Cuotas aportadas menos rescatadas
        "FLUJO_NETO",  # Flujo neto de recursos
        "PATRIMONIO_NETO_ANTERIOR",  # Patrimonio del período anterior
        "DELTA_PATRIMONIO_NETO",  # Variación del patrimonio
        "EFECTO_PRECIO_EN_DELTA_PATRIMONIO",  # Efecto del precio en la variación
    ]

    # Columnas para agrupación
    grouping_columns = ["RUN_FM", "FECHA_INF"]

    # Crear lista de agregaciones (suma para todas las columnas excepto las de agrupación)
    agg_list = [pl.col(x).sum() for x in columns if x not in grouping_columns]

    # Realizar la agrupación y agregación
    lazy_df = (
        lazy_df.select(columns)  # Seleccionar solo las columnas necesarias
        .group_by(grouping_columns)  # Agrupar por RUN y fecha
        .agg(agg_list)  # Sumar todas las métricas
        .sort(["RUN_FM", "FECHA_INF"])  # Ordenar el resultado
        .with_columns(
            (
                (pl.col("PATRIMONIO_NETO") / pl.col("CUOTAS_EN_CIRCULACION")).round(4)
            ).alias("PROXY_VALOR_CUOTA")
        )
    )

    # Guarda los resultados en formato parquet
    save_lazyframe_to_parquet(
        lazy_df=lazy_df, filename=soyfocus_by_run_file, unique=True
    )

    return lazy_df


def create_tac_report(
    lazy_df: pl.LazyFrame,
    run_only: bool = False,
    soyfocus_tac_file: Path = SOYFOCUS_TAC_PARQUET_FILE_PATH,
) -> pl.LazyFrame:
    """
    Calcula las tasas anuales de costos (TAC) y gastos para los fondos.

    Esta función realiza los cálculos de tasas de gastos y costos según la normativa CMF,
    incluyendo las tasas diarias y anualizadas, así como la verificación de límites.

    Fórmulas principales:
    - TASA_GASTOS_DIARIA_% = 100 * GASTOS_TOTALES / PATRIMONIO_AJUSTADO_GASTOS
    - TASA_GASTOS_ANUALIZADA_% = TASA_GASTOS_DIARIA_% * DIAS_ANUAL
    - TDC_% (Tasa Diaria de Costos) = 100 * COSTOS_TOTALES / PATRIMONIO_AJUSTADO_COSTOS
    - TAC_% = TDC_% * DIAS_ANUAL
    - ESPACIO_GASTOS_ANUALIZADO = (LIMITE_GASTOS_ANUAL * PATRIMONIO_AJUSTADO_GASTOS) / (100 - LIMITE_GASTOS_ANUAL)

    Args:
        lazy_df (pl.LazyFrame): DataFrame con los datos de los fondos, debe incluir las columnas:
            - FECHA_INF: Fecha de la información
            - RUN_FM: Identificador del fondo
            - SERIE: Serie del fondo (opcional si run_only=True)
            - GASTOS_TOTALES: Suma de gastos afectos y no afectos
            - PATRIMONIO_AJUSTADO_GASTOS: Patrimonio ajustado incluyendo gastos
            - COSTOS_TOTALES: Suma de gastos y remuneraciones
            - PATRIMONIO_AJUSTADO_COSTOS: Patrimonio ajustado incluyendo todos los costos
            - PATRIMONIO_NETO_ANTERIOR: Patrimonio del período anterior
        run_only (bool): Si True, calcula las tasas a nivel de RUN sin considerar series.
            Por defecto False.
        soyfocus_tac_file (Path): Ruta donde se guardará el archivo con los cálculos.
            Por defecto usa SOYFOCUS_TAC_PARQUET_FILE_PATH.

    Returns:
        pl.LazyFrame: DataFrame con los cálculos de tasas y límites, incluye:
            - TASA_GASTOS_DIARIA_%: Tasa de gastos del día
            - TASA_GASTOS_ANUALIZADA_%: Tasa de gastos anualizada
            - TDC_%: Tasa diaria de costos
            - TAC_%: Tasa anual de costos
            - LIMITE_GASTOS_ANUALIZADO: Límite anual de gastos aplicable
            - ESPACIO_GASTOS_ANUALIZADO: Espacio disponible para gastos en el año
            - ESPACIO_GASTOS_DIARIO: Espacio disponible para gastos diarios
            - CUMPLE_LIMITE_GASTOS_ANUAL: Indicador de cumplimiento del límite

    Note:
        - Los cálculos siguen la metodología establecida por la CMF
        - Se aplican límites de gastos según la fecha definida en FECHA_INICIO_COSTOS
        - Los valores nulos o NaN en los cálculos se reemplazan por 0
        - Para patrimonios negativos o cero, la TDC se establece en 0
    """
    # Define las columnas necesarias para los cálculos
    columns = [
        "FECHA_INF",
        "RUN_FM",
        "SERIE",
        "GASTOS_TOTALES",
        "PATRIMONIO_AJUSTADO_GASTOS",
        "COSTOS_TOTALES",
        "PATRIMONIO_AJUSTADO_COSTOS",
        "PATRIMONIO_NETO_ANTERIOR",
    ]

    # Si solo se requiere análisis por RUN, elimina la columna SERIE
    if run_only:
        columns.remove("SERIE")

    lazy_df = (
        # Selecciona solo las columnas necesarias
        lazy_df.select(columns)
        # Calcula la tasa diaria de gastos como porcentaje
        .with_columns(
            (
                (100 * pl.col("GASTOS_TOTALES") / pl.col("PATRIMONIO_AJUSTADO_GASTOS"))
                .fill_nan(0)
                .fill_null(0)
            ).alias("TASA_GASTOS_DIARIA_%")
        )
        # Anualiza la tasa de gastos
        .with_columns(
            (pl.col("TASA_GASTOS_DIARIA_%") * DIAS_ANUAL).alias(
                "TASA_GASTOS_ANUALIZADA_%"
            )
        )
        # Calcula la tasa diaria de costos (TDC), considerando patrimonio negativo
        .with_columns(
            (
                pl.when(pl.col("PATRIMONIO_NETO_ANTERIOR") <= 0)
                .then(pl.lit(0))
                .otherwise(
                    (
                        100
                        * pl.col("COSTOS_TOTALES")
                        / pl.col("PATRIMONIO_AJUSTADO_COSTOS")
                    )
                    .fill_nan(0)
                    .fill_null(0)
                )
            ).alias("TDC_%")
        )
        # Calcula la tasa anual de costos (TAC)
        .with_columns((pl.col("TDC_%") * DIAS_ANUAL).alias("TAC_%"))
        # Establece el límite de gastos según la fecha
        .with_columns(
            pl.when(pl.col("FECHA_INF") > FECHA_INICIO_COSTOS)
            .then(pl.lit(LIMITE_GASTOS_ANUAL))
            .otherwise(pl.lit(0))
            .alias("LIMITE_GASTOS_ANUALIZADO")
        )
        # Calcula el espacio disponible para gastos en el año
        .with_columns(
            (
                (LIMITE_GASTOS_ANUAL * pl.col("PATRIMONIO_AJUSTADO_GASTOS"))
                / (100 - LIMITE_GASTOS_ANUAL)
            ).alias("ESPACIO_GASTOS_ANUALIZADO")
        )
        # Calcula el espacio diario disponible para gastos
        .with_columns(
            (pl.col("ESPACIO_GASTOS_ANUALIZADO") / DIAS_ANUAL).alias(
                "ESPACIO_GASTOS_DIARIO"
            )
        )
        # Verifica el cumplimiento del límite anual de gastos
        .with_columns(
            (pl.col("TASA_GASTOS_ANUALIZADA_%") < LIMITE_GASTOS_ANUAL).alias(
                "CUMPLE_LIMITE_GASTOS_ANUAL"
            )
        )
    )

    # Guarda los resultados en formato parquet
    save_lazyframe_to_parquet(lazy_df=lazy_df, filename=soyfocus_tac_file, unique=True)

    return lazy_df


if __name__ == "__main__":
    lazy_df = create_soyfocus_parquet()
    print(lazy_df.columns)
    tac = create_tac_report(lazy_df)
    lazy_df = soy_focus_by_run(lazy_df)
    tac = create_tac_report(lazy_df, run_only=True)
    # tac.collect().tail(10).write_csv("cartolas/csv/soyfocus.csv")
    df = pl.read_parquet(
        "/Users/franciscoerrandonea/code/cartolas/cartolas/data/parquet/soyfocus.parquet"
    )
    print(df.columns)
    print(
        df.write_csv(
            "/Users/franciscoerrandonea/code/cartolas/cartolas/data/csv/soyfocus.csv"
        )
    )
