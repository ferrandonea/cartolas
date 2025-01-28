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
    """Este lee una cartola en formato txt y la transforma a un DataFrame de Polars."""
    # TODO: Esto se puede hacer con un wildcard para evitar iterar y hacer concat, pero no quiero meter esa lógica ahora
    # principalmente por comptibilidad con pandas

    if not Path(txt_cartola).exists():
        raise FileNotFoundError(f"El archivo {txt_cartola} no existe")

    lazy_df = pl.scan_csv(
        txt_cartola, separator=";", schema_overrides=schema
    ).with_columns(
        pl.col("FECHA_INF").str.strptime(pl.Date, "%Y%m%d", strict=False),
        *[map_s_n_to_bool(col) for col in boolean_columns],
        *[replace_null_with_one(col) for col in null_columns],
        pl.concat_str(
            [pl.col("RUN_FM").cast(pl.Utf8), pl.lit("-"), pl.col("SERIE")]
        ).alias("RUN_FM_SERIE"),
    )

    return lazy_df


def transform_cartola_folder(
    cartola_folder: Path = CARTOLAS_FOLDER,
    wildcard: str = WILDCARD_CARTOLAS_TXT,
    sorting_order: list[str] = SORTING_ORDER,
    unique: bool = True,
) -> pl.LazyFrame:
    """Lee todas las cartolas de una carpeta y las concatena en un DataFrame de Polars (lazy)."""
    list_txts = [txt_file for txt_file in cartola_folder.glob(wildcard)]
    

    lazy_df = pl.concat(
        [transform_single_cartola(txt_cartola=txt_file) for txt_file in list_txts]
    )

    return (
        lazy_df.unique().sort(sorting_order) if unique else lazy_df.sort(sorting_order)
    )


if __name__ == "__main__":
    txt_cartola = "/Users/franciscoerrandonea/code/cartolas/cartolas/txt/ffmm_todos_20210531_20210622.txt"

    df = transform_single_cartola(txt_cartola=txt_cartola)
    print(df)

    print(transform_cartola_folder().collect())
