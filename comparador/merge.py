from datetime import datetime, date

import polars as pl

from cartolas.config import PARQUET_FOLDER_YEAR
from cartolas.soyfocus import read_parquet_cartolas_lazy
from comparador.elmer import last_elmer_data_as_polars
from eco.bcentral import update_bcch_for_cartolas
from utiles.listas import multiply_list

MAX_YEARS = 6
MIN_DATE = date(2019, 1, 1)
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


def prepare_cartolas_in_pesos(
    min_date: datetime = MIN_DATE, relevant_columns: list[str] = COLUMNAS_RELEVANTES
) -> pl.LazyFrame:
    """
    Prepara los datos de cartolas convirtiendo todos los valores monetarios a pesos chilenos.

    Esta función carga los datos de cartolas, los filtra por fecha, y realiza la conversión
    de monedas extranjeras a pesos chilenos utilizando datos del Banco Central.
    También calcula métricas adicionales como gastos totales, comisiones y rentabilidad.

    Args:
        min_date: Fecha mínima para filtrar los datos (por defecto, 10 años atrás)
        relevant_columns: Lista de columnas a seleccionar del dataset original

    Returns:
        pl.LazyFrame: DataFrame lazy con los datos procesados y convertidos a pesos
    """
    cartola_df = (
        read_parquet_cartolas_lazy(PARQUET_FOLDER_YEAR)
        .filter(pl.col("FECHA_INF") >= min_date)
        .select(relevant_columns)
        .filter(
            ~pl.col("MONEDA").is_in(["MONEDA NO DEF."])
        )  # Excluye registros con moneda no definida
    )

    eco_df = (
        update_bcch_for_cartolas()
    )  # Datos del banco central, el euro y el dolar, se actualiza al ejecutarse

    # Une los datos de cartolas con los tipos de cambio
    merged_df = cartola_df.join(
        eco_df, on=["MONEDA", "FECHA_INF"], how="left"
    ).with_columns(
        pl.col("TIPO_CAMBIO").fill_null(1)
    )  # Asume tipo de cambio 1 para valores nulos

    merged_df = (
        merged_df.with_columns(
            (SUMA_GASTOS * pl.col("TIPO_CAMBIO")).alias(
                "GASTOS_TOTALES_PESOS"
            )  # Convierte gastos a pesos
        )
        .with_columns(
            (SUMA_COMISIONES * pl.col("TIPO_CAMBIO")).alias(
                "COMISIONES_TOTALES_PESOS"
            )  # Convierte comisiones a pesos
        )
        .with_columns(
            PRODUCTO_FACTORES.alias("PRODUCTO_FACTORES")
        )  # Calcula el producto de los factores de ajuste
        .with_columns(
            (pl.col("VALOR_CUOTA") * pl.col("TIPO_CAMBIO")).alias(
                "VALOR_CUOTA_PESOS"
            )  # Convierte valor cuota a pesos
        )
        .sort(
            ["RUN_FM", "SERIE", "FECHA_INF"]
        )  # Ordena para cálculos de cambios diarios
        .with_columns(
            [
                pl.col("VALOR_CUOTA_PESOS")
                .shift(1)
                .over(["RUN_FM", "SERIE"])
                .alias(
                    "VALOR_CUOTA_ANTERIOR_PESOS"
                )  # Obtiene el valor de cuota del día anterior
            ]
        )
        .with_columns(
            (pl.col("VALOR_CUOTA_PESOS") * pl.col("PRODUCTO_FACTORES")).alias(
                "VALOR_CUOTA_PESOS_AJUSTADO"  # Ajusta el valor de cuota con los factores
            )
        )
        .with_columns(
            (
                (
                    pl.col("VALOR_CUOTA_PESOS_AJUSTADO")
                    / pl.col("VALOR_CUOTA_ANTERIOR_PESOS")
                )
                .fill_nan(1)
                .fill_null(1)
            ).alias("RENTABILIDAD_DIARIA_PESOS")  # Calcula la rentabilidad diaria
        )
        .with_columns(
            (pl.col("CUOTAS_APORTADAS") - pl.col("CUOTAS_RESCATADAS")).alias(
                "DELTA_CUOTAS"
            )
        )
        .with_columns(
            (pl.col("DELTA_CUOTAS") * pl.col("VALOR_CUOTA_PESOS_AJUSTADO")).alias(
                "FLUJO_PESOS"
            )
        )
        .with_columns(
            (
                pl.col("CUOTAS_EN_CIRCULACION") * pl.col("VALOR_CUOTA_PESOS_AJUSTADO")
            ).alias("PATRIMONIO_PESOS")
        )
        .with_columns(
            [
                pl.col("PATRIMONIO_PESOS")
                .shift(1)
                .over(["RUN_FM", "SERIE"])
                .fill_nan(0)
                .fill_null(0)
                .alias(
                    "PATRIMONIO_ANTERIOR_PESOS"
                )  # Obtiene el valor de cuota del día anterior
            ]
        )
        .with_columns(
            (pl.col("PATRIMONIO_PESOS") - pl.col("PATRIMONIO_ANTERIOR_PESOS")).alias(
                "DELTA_PATRIMONIO_PESOS"
            )
        )
        .with_columns(
            (pl.col("DELTA_PATRIMONIO_PESOS") - pl.col("FLUJO_PESOS")).alias(
                "UTILIDAD_PESOS"
            )
        )
    )
    return merged_df


def prepare_relevant_categories() -> pl.LazyFrame:
    """
    Prepara un DataFrame con las categorías relevantes de fondos desde Elmer.

    Esta función obtiene los datos más recientes de Elmer, filtra por tipo de inversión
    retail y categorías específicas, y mapea estas categorías a los RUN_FM de SoyFocus.

    Returns:
        pl.LazyFrame: DataFrame lazy con las categorías relevantes mapeadas
    """
    columns_to_select = ["RUN_FM", "FONDO", "ADM", "SERIE", "CATEGORIA", "TIPOINV"]
    tipoinv_filter = (
        "RETAIL / PEQUEÑO INVERSOR"  # Filtro para seleccionar solo inversiones retail
    )

    # Este es un mapping de categorias de elmer a los RUN_FM de cartolas de soyfocus
    categories_mapping = {
        "BALANCEADO CONSERVADOR": 9810,
        "BALANCEADO MODERADO": 9809,
        "BALANCEADO AGRESIVO": 9811,
        "DEUDA CORTO PLAZO NACIONAL": 9810,
    }
    categories_to_select = list(categories_mapping.keys())

    # Obtiene los datos de Elmer y aplica los filtros necesarios
    elmer_df = (
        last_elmer_data_as_polars()
        .select(columns_to_select)
        .filter(pl.col("TIPOINV") == tipoinv_filter)
        .filter(pl.col("CATEGORIA").is_in(categories_to_select))
        .with_columns(
            pl.col("CATEGORIA")
            .replace(categories_mapping)
            .alias("RUN_SOYFOCUS")  # Mapea categorías a RUN_FM
        )
        .with_columns(
            pl.lit("B").alias("SERIE_SOYFOCUS") #Porque en este caso se va a comparar con la B, esto se puede mejorar para APV y otros
        )
        .drop("TIPOINV")
    )
    return elmer_df


def merge_cartolas_with_categories() -> pl.LazyFrame:
    """
    Combina los datos de cartolas en pesos con las categorías de Elmer.

    Esta función une los datos procesados de cartolas con las categorías relevantes
    de Elmer, y filtra para mantener solo los registros que tienen una categoría asignada.

    Returns:
        pl.LazyFrame: DataFrame lazy con los datos de cartolas enriquecidos con categorías
    """
    elmer_df = prepare_relevant_categories()
    merged_df = prepare_cartolas_in_pesos()

    # Une los datos de cartolas con las categorías por RUN_FM y SERIE
    merged_df = merged_df.join(elmer_df, on=["RUN_FM", "SERIE"], how="left")
    # TODO: Filtrar por categoria no nula en el join

    # Filtra para mantener solo registros con categoría asignada
    # return merged_df.filter(pl.col("CATEGORIA").is_not_null()).filter(pl.col("FECHA_INF") <= MAX_DATE)
    return merged_df.filter(pl.col("CATEGORIA").is_not_null())


if __name__ == "__main__":
    df = merge_cartolas_with_categories()
    print(df.collect())  # Materializa el DataFrame lazy y muestra los resultados
    print(df.collect().columns)
    df.collect().write_csv("cartolas.csv")
