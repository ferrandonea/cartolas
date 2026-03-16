from datetime import datetime, date

import polars as pl

from cartolas.config import PARQUET_FOLDER_YEAR
from cartolas.read import read_parquet_cartolas_lazy
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
        pl.col("TIPO_CAMBIO").forward_fill().over(["RUN_FM", "SERIE"]).fill_null(1)
    )  # Forward fill por fondo/serie, luego 1 para pesos chilenos

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
            pl.when(pl.col("VALOR_CUOTA_ANTERIOR_PESOS").is_null())
            .then(pl.lit(1.0))  # Primer día del fondo: rentabilidad neutral
            .when(pl.col("VALOR_CUOTA_ANTERIOR_PESOS") == 0)
            .then(pl.lit(1.0))  # Valor anterior cero: rentabilidad neutral
            .otherwise(
                pl.col("VALOR_CUOTA_PESOS_AJUSTADO")
                / pl.col("VALOR_CUOTA_ANTERIOR_PESOS")
            )
            .alias("RENTABILIDAD_DIARIA_PESOS")
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


def _validate_custom_mapping(
    custom_mapping: dict[int, int],
    custom_categories: list[int],
    categories_mapping: dict[str, int],
    elmer_df: pl.LazyFrame,
) -> dict[int, str]:
    """
    Valida el custom_mapping y retorna el mapeo NUM_CATEGORIA → nombre de categoría.

    Verifica:
    - No haya dos fondos mapeados a la misma categoría
    - No haya conflictos con categorías default de otros fondos Focus

    Args:
        custom_mapping: {RUN_FM: NUM_CATEGORIA}
        custom_categories: Lista de NUM_CATEGORIA únicos del mapping
        categories_mapping: Mapeo default categoría → RUN_FM
        elmer_df: LazyFrame con datos de Elmer

    Returns:
        dict[int, str]: Mapeo NUM_CATEGORIA → nombre de categoría

    Raises:
        ValueError: Si el mapping tiene duplicados o conflictos
    """
    # Validar que no haya dos fondos mapeados a la misma categoría
    target_cats = list(custom_mapping.values())
    if len(target_cats) != len(set(target_cats)):
        dupes = [c for c in target_cats if target_cats.count(c) > 1]
        raise ValueError(
            f"custom_mapping tiene múltiples fondos apuntando a la misma "
            f"NUM_CATEGORIA: {set(dupes)}. Cada categoría solo puede tener "
            f"un fondo SoyFocus de referencia."
        )

    # Obtener mapeo NUM_CATEGORIA → nombre de categoría para reasignar
    num_to_cat_name = dict(
        elmer_df.select("NUM_CATEGORIA", "CATEGORIA")
        .unique()
        .filter(pl.col("NUM_CATEGORIA").is_in(custom_categories))
        .collect()
        .iter_rows()
    )

    # Validar que ningún mapping apunte a una categoría default de otro fondo Focus activo
    default_cat_to_fund = {
        cat: run for cat, run in categories_mapping.items()
        if cat.startswith("BALANCEADO")
    }
    for run_fm, num_categoria in custom_mapping.items():
        target_cat = num_to_cat_name.get(num_categoria)
        if target_cat and target_cat in default_cat_to_fund:
            other_fund = default_cat_to_fund[target_cat]
            # Solo es conflicto si el otro fondo NO está siendo remapeado también
            if other_fund != run_fm and other_fund not in custom_mapping:
                raise ValueError(
                    f"custom_mapping mapea RUN_FM {run_fm} a categoría "
                    f"'{target_cat}', que ya es la categoría default del fondo "
                    f"Focus {other_fund}. Esto produciría dos fondos Focus en "
                    f"la misma categoría. Incluya {other_fund} en custom_mapping "
                    f"para remapearlo también."
                )

    return num_to_cat_name


def prepare_relevant_categories(
    custom_mapping: dict[int, int] | None = None,
) -> pl.LazyFrame:
    """
    Prepara un DataFrame con las categorías relevantes de fondos desde Elmer.

    Esta función obtiene los datos más recientes de Elmer, filtra por tipo de inversión
    retail y categorías específicas, y mapea estas categorías a los RUN_FM de SoyFocus.

    Args:
        custom_mapping: Diccionario {RUN_FM: NUM_CATEGORIA} para sobrescribir
                       las categorías asignadas en el JSON de Elmer.
                       Ejemplo: {9810: 17} compara el fondo 9810 con categoría 17

    Returns:
        pl.LazyFrame: DataFrame lazy con las categorías relevantes mapeadas
    """
    columns_to_select = ["RUN_FM", "FONDO", "ADM", "SERIE", "CATEGORIA", "NUM_CATEGORIA", "TIPOINV"]
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
    )

    # Filtrar por categorías relevantes, incluyendo las custom si existen
    if custom_mapping is not None:
        custom_categories = list(set(custom_mapping.values()))
        elmer_df = elmer_df.filter(
            pl.col("CATEGORIA").is_in(categories_to_select)
            | pl.col("NUM_CATEGORIA").is_in(custom_categories)
        )
    else:
        elmer_df = elmer_df.filter(pl.col("CATEGORIA").is_in(categories_to_select))

    # Mapea categorías a RUN_FM de SoyFocus
    elmer_df = elmer_df.with_columns(
        pl.col("CATEGORIA")
        .replace(categories_mapping)
        .alias("RUN_SOYFOCUS")
    )

    # Aplica overrides del custom_mapping con when/then/otherwise
    if custom_mapping is not None:
        num_to_cat_name = _validate_custom_mapping(
            custom_mapping, custom_categories, categories_mapping, elmer_df
        )

        # Construir expresión RUN_SOYFOCUS en una sola pasada
        soyfocus_expr = pl.col("RUN_SOYFOCUS")
        for run_fm, num_categoria in custom_mapping.items():
            soyfocus_expr = (
                pl.when(pl.col("NUM_CATEGORIA") == num_categoria)
                .then(pl.lit(run_fm))
                .otherwise(soyfocus_expr)
            )
        elmer_df = elmer_df.with_columns(soyfocus_expr.alias("RUN_SOYFOCUS"))

        # Construir expresiones CATEGORIA y NUM_CATEGORIA en una sola pasada
        cat_expr = pl.col("CATEGORIA")
        num_cat_expr = pl.col("NUM_CATEGORIA")
        for run_fm, num_categoria in custom_mapping.items():
            if num_categoria in num_to_cat_name:
                cat_expr = (
                    pl.when(pl.col("RUN_FM") == run_fm)
                    .then(pl.lit(num_to_cat_name[num_categoria]))
                    .otherwise(cat_expr)
                )
                num_cat_expr = (
                    pl.when(pl.col("RUN_FM") == run_fm)
                    .then(pl.lit(num_categoria))
                    .otherwise(num_cat_expr)
                )
        elmer_df = elmer_df.with_columns(
            cat_expr.alias("CATEGORIA"),
            num_cat_expr.alias("NUM_CATEGORIA"),
        )

    elmer_df = elmer_df.with_columns(
        pl.lit("B").alias(
            "SERIE_SOYFOCUS"
        )  # Porque en este caso se va a comparar con la B, esto se puede mejorar para APV y otros
    ).drop("TIPOINV")

    return elmer_df


def merge_cartolas_with_categories(
    custom_mapping: dict[int, int] | None = None,
) -> pl.LazyFrame:
    """
    Combina los datos de cartolas en pesos con las categorías de Elmer.

    Esta función une los datos procesados de cartolas con las categorías relevantes
    de Elmer, y filtra para mantener solo los registros que tienen una categoría asignada.

    Args:
        custom_mapping: Diccionario {RUN_FM: NUM_CATEGORIA} para sobrescribir
                       las categorías asignadas en el JSON de Elmer.

    Returns:
        pl.LazyFrame: DataFrame lazy con los datos de cartolas enriquecidos con categorías
    """
    elmer_df = prepare_relevant_categories(custom_mapping=custom_mapping)
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
