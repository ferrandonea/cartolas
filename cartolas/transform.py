"""Transforma y ordena los datos de las cartolas descargadas."""

import polars as pl
from .polars import map_s_n_to_bool, replace_null_with_one
from pathlib import Path
from .config import (
    SCHEMA,
    COLUMNAS_BOOLEAN,
    COLUMNAS_NULL,
    SORTING_ORDER,
    CARTOLAS_FOLDER,
    WILDCARD_CARTOLAS_TXT,
)

# Tipos de datos de Polars, es para simplificar la escritura
PolarsTypes = pl.UInt16 | pl.UInt32 | pl.String | pl.Float64


def transform_single_cartola(
    txt_cartola: Path,
    schema: dict[str, PolarsTypes] = SCHEMA,
    boolean_columns: list[str] = COLUMNAS_BOOLEAN,
    null_columns: list[str] = COLUMNAS_NULL,
) -> pl.LazyFrame:
    """Lee una cartola en formato txt y la transforma a un DataFrame de Polars.

    Args:
        txt_cartola (Path): Ruta del archivo de la cartola en formato txt.
        schema (dict[str, PolarsTypes], optional): Esquema de los datos. Defaults to SCHEMA.
        boolean_columns (list[str], optional): Columnas que deben ser convertidas a booleanas. Defaults to COLUMNAS_BOOLEAN.
        null_columns (list[str], optional): Columnas donde los valores nulos deben ser reemplazados por uno. Defaults to COLUMNAS_NULL.

    Raises:
        FileNotFoundError: Si el archivo de la cartola no existe.

    Returns:
        pl.LazyFrame: DataFrame de Polars en modo lazy.
    """
    # Verifica si el archivo de la cartola existe
    if not Path(txt_cartola).exists():
        raise FileNotFoundError(f"El archivo {txt_cartola} no existe")

    # Lee el archivo CSV y aplica las transformaciones necesarias
    lazy_df = pl.scan_csv(
        txt_cartola, separator=";", schema_overrides=schema
    ).with_columns(
        # Convierte la columna FECHA_INF a tipo Date
        pl.col("FECHA_INF").str.strptime(pl.Date, "%Y%m%d", strict=False),
        # Convierte las columnas booleanas
        *[map_s_n_to_bool(col) for col in boolean_columns],
        # Reemplaza los valores nulos con uno en las columnas especificadas
        *[replace_null_with_one(col) for col in null_columns],
        # Concatena las columnas RUN_FM y SERIE en una nueva columna RUN_FM_SERIE
        pl.concat_str(
            [pl.col("RUN_FM").cast(pl.Utf8), pl.lit("-"), pl.col("SERIE")]
        ).alias("RUN_FM_SERIE"),
    ).drop(["NOM_ADM"])
    return lazy_df


def transform_cartola_folder(
    cartola_folder: Path = CARTOLAS_FOLDER,
    wildcard: str = WILDCARD_CARTOLAS_TXT,
    sorting_order: list[str] = SORTING_ORDER,
    unique: bool = True,
) -> pl.LazyFrame:
    """Lee todas las cartolas de una carpeta y las concatena en un DataFrame de Polars (lazy).

    Args:
        cartola_folder (Path, optional): Carpeta que contiene las cartolas. Defaults to CARTOLAS_FOLDER.
        wildcard (str, optional): Patrón para buscar archivos de cartolas. Defaults to WILDCARD_CARTOLAS_TXT.
        sorting_order (list[str], optional): Orden de clasificación para el DataFrame resultante. Defaults to SORTING_ORDER.
        unique (bool, optional): Si se deben eliminar filas duplicadas. Defaults to True.

    Returns:
        pl.LazyFrame: DataFrame de Polars en modo lazy.
    """
    # Obtiene la lista de archivos de cartolas en la carpeta especificada
    list_txts = [txt_file for txt_file in cartola_folder.glob(wildcard)]

    # Concatena los DataFrames de todas las cartolas
    lazy_df = pl.concat(
        [transform_single_cartola(txt_cartola=txt_file) for txt_file in list_txts]
    )

    # Elimina filas duplicadas y ordena el DataFrame si es necesario
    return (
        lazy_df.unique().sort(sorting_order) if unique else lazy_df.sort(sorting_order)
    )


if __name__ == "__main__":
    # Ruta del archivo de la cartola de ejemplo
    txt_cartola = "/Users/franciscoerrandonea/code/cartolas/cartolas/txt/ffmm_todos_20210531_20210622.txt"

    # Transforma una única cartola y la imprime
    df = transform_single_cartola(txt_cartola=txt_cartola)
    print(df)

    # Transforma todas las cartolas en la carpeta y las imprime
    print(transform_cartola_folder().collect())
