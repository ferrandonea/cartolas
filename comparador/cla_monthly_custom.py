"""
Módulo para generar reportes CLA con mapeo personalizado de categorías.

Este módulo extiende la funcionalidad de cla_monthly.py permitiendo sobrescribir
las categorías asignadas por el JSON de Elmer con un mapeo personalizado.

Esto es útil cuando se quiere comparar un fondo con una categoría diferente a la
asignada en el JSON sin modificar el archivo JSON original.
"""

import polars as pl
from comparador.merge import prepare_cartolas_in_pesos
from comparador.elmer import last_elmer_data_as_polars
from comparador.cla_monthly import generate_cla_data as original_generate_cla_data
from pathlib import Path


def prepare_relevant_categories_with_custom_mapping(
    custom_mapping: dict[int, int] = None
) -> pl.LazyFrame:
    """
    Prepara un DataFrame con las categorías relevantes de fondos desde Elmer,
    permitiendo sobrescribir categorías con un mapeo personalizado.

    Esta función es similar a prepare_relevant_categories() de merge.py, pero
    permite aplicar un mapeo personalizado de RUN_FM a NUM_CATEGORIA después
    de cargar los datos de Elmer.

    Args:
        custom_mapping: Diccionario {RUN_FM: NUM_CATEGORIA} para sobrescribir
                       las categorías asignadas en el JSON de Elmer.
                       Ejemplo: {9810: 17} cambia el fondo 9810 a categoría 17

    Returns:
        pl.LazyFrame: DataFrame lazy con las categorías relevantes mapeadas
    """
    columns_to_select = [
        "RUN_FM", "FONDO", "ADM", "SERIE", "CATEGORIA", "NUM_CATEGORIA", "TIPOINV"
    ]
    tipoinv_filter = "RETAIL / PEQUEÑO INVERSOR"

    # Este es un mapping de categorias de elmer a los RUN_FM de cartolas de soyfocus
    categories_mapping = {
        "BALANCEADO CONSERVADOR": 9810,
        "BALANCEADO MODERADO": 9809,
        "BALANCEADO AGRESIVO": 9811,
        "DEUDA CORTO PLAZO NACIONAL": 9810,
    }
    categories_to_select = list(categories_mapping.keys())

    # Obtiene los datos de Elmer
    elmer_df = last_elmer_data_as_polars().select(columns_to_select)

    # Si hay un mapeo personalizado, primero obtenemos TODOS los fondos
    # para poder incluir los de las categorías personalizadas
    if custom_mapping:
        # Obtenemos los números de categoría personalizados
        custom_categories = set(custom_mapping.values())

        # Filtramos por TIPOINV retail y obtenemos los fondos de las categorías relevantes
        # INCLUYENDO las categorías personalizadas
        elmer_df = elmer_df.filter(pl.col("TIPOINV") == tipoinv_filter)

        # Necesitamos incluir fondos de dos grupos:
        # 1. Los de las categorías originales (para el mapping original)
        # 2. Los de las categorías personalizadas (para comparar)
        elmer_df = elmer_df.filter(
            pl.col("CATEGORIA").is_in(categories_to_select) |
            pl.col("NUM_CATEGORIA").is_in(list(custom_categories))
        )
    else:
        # Si no hay mapeo personalizado, usamos la lógica original
        elmer_df = elmer_df.filter(pl.col("TIPOINV") == tipoinv_filter).filter(
            pl.col("CATEGORIA").is_in(categories_to_select)
        )

    # Aplicamos el mapping original de categorías a RUN_SOYFOCUS
    elmer_df = elmer_df.with_columns(
        pl.col("CATEGORIA").replace(categories_mapping).alias("RUN_SOYFOCUS")
    )

    # Si hay un mapeo personalizado, lo aplicamos SOBRESCRIBIENDO el RUN_SOYFOCUS
    # para los fondos especificados
    if custom_mapping:
        # Para cada RUN_FM en el mapeo personalizado, buscamos fondos de la categoría
        # especificada y les asignamos ese RUN_FM como RUN_SOYFOCUS
        for run_fm, num_categoria in custom_mapping.items():
            # Actualizamos el RUN_SOYFOCUS: donde NUM_CATEGORIA coincida con el mapeo,
            # asignamos el run_fm correspondiente
            elmer_df = elmer_df.with_columns(
                pl.when(pl.col("NUM_CATEGORIA") == num_categoria)
                .then(pl.lit(run_fm))
                .otherwise(pl.col("RUN_SOYFOCUS"))
                .alias("RUN_SOYFOCUS")
            )

    # Agregamos la serie SOYFOCUS (siempre B para este caso)
    elmer_df = elmer_df.with_columns(
        pl.lit("B").alias("SERIE_SOYFOCUS")
    ).drop("TIPOINV")

    return elmer_df


def merge_cartolas_with_custom_categories(
    custom_mapping: dict[int, int] = None
) -> pl.LazyFrame:
    """
    Combina los datos de cartolas en pesos con las categorías de Elmer,
    aplicando un mapeo personalizado de categorías.

    Args:
        custom_mapping: Diccionario {RUN_FM: NUM_CATEGORIA} para sobrescribir
                       las categorías asignadas en el JSON de Elmer

    Returns:
        pl.LazyFrame: DataFrame lazy con los datos de cartolas enriquecidos con categorías
    """
    elmer_df = prepare_relevant_categories_with_custom_mapping(custom_mapping)
    merged_df = prepare_cartolas_in_pesos()

    # Une los datos de cartolas con las categorías por RUN_FM y SERIE
    merged_df = merged_df.join(elmer_df, on=["RUN_FM", "SERIE"], how="left")

    # Filtra para mantener solo registros con categoría asignada
    return merged_df.filter(pl.col("CATEGORIA").is_not_null())


def generate_cla_data_with_custom_mapping(
    custom_mapping: dict[int, int] = None,
    save_xlsx: bool = True,
    xlsx_name: str | Path = "cla_mensual_custom.xlsx",
    excel_steps: str = "all"
):
    """
    Genera el reporte CLA con un mapeo personalizado de categorías.

    Esta función es un wrapper de generate_cla_data() que permite aplicar
    un mapeo personalizado de categorías antes de generar el reporte.

    Args:
        custom_mapping: Diccionario {RUN_FM: NUM_CATEGORIA} para sobrescribir
                       las categorías asignadas en el JSON de Elmer.
                       Ejemplo: {9810: 17} cambia el fondo 9810 a categoría 17
        save_xlsx: Si True, guarda el resultado en un archivo Excel
        xlsx_name: Nombre del archivo Excel a generar
        excel_steps: Qué pasos guardar en Excel ("all" para todos)
    """
    # Temporalmente reemplazamos la función merge_cartolas_with_categories
    # en el módulo comparador.cla_monthly con nuestra versión custom
    import comparador.cla_monthly as cla_monthly_module
    import comparador.merge as merge_module

    # Guardamos las funciones originales
    original_merge_function = merge_module.merge_cartolas_with_categories

    # Creamos una función wrapper que usa nuestro custom_mapping
    def custom_merge_wrapper():
        return merge_cartolas_with_custom_categories(custom_mapping)

    # Reemplazamos temporalmente la función
    merge_module.merge_cartolas_with_categories = custom_merge_wrapper

    try:
        # Llamamos a la función original de generación de CLA
        original_generate_cla_data(
            save_xlsx=save_xlsx,
            xlsx_name=xlsx_name,
            excel_steps=excel_steps
        )
    finally:
        # Restauramos la función original
        merge_module.merge_cartolas_with_categories = original_merge_function


if __name__ == "__main__":
    # Ejemplo de uso: comparar el fondo 9810 con la categoría 17
    custom_mapping = {
        9810: 17,  # SoyFocus Conservador: comparar con categoría 17
    }

    df = merge_cartolas_with_custom_categories(custom_mapping)
    print(df.collect())
