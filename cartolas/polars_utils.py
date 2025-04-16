import polars as pl


def map_s_n_to_bool(column_name: str) -> pl.Expr:
    """
    Crea una expresión para mapear los valores 'S' y 'N' de una columna a valores booleanos.

    Args:
        column_name (str): Nombre de la columna que contiene los valores 'S' y 'N'.

    Returns:
        pl.Expr: Expresión de Polars que convierte 'S' a True, 'N' a False, y otros valores a None.

    Note:
        - 'S' se mapea a True
        - 'N' se mapea a False
        - Cualquier otro valor se convierte en None
        - La columna resultante mantiene el nombre original

    Example:
        >>> df = pl.DataFrame({"columna": ["S", "N", "S", "X"]})
        >>> df = df.with_columns(map_s_n_to_bool("columna"))
        >>> print(df)
        shape: (4, 1)
        ┌─────────┐
        │ columna │
        │ bool    │
        ╞═════════╡
        │ true    │
        │ false   │
        │ true    │
        │ null    │
        └─────────┘
    """
    return (
        pl.when(pl.col(column_name).eq("S"))
        .then(True)
        .when(pl.col(column_name).eq("N"))
        .then(False)
        .otherwise(None)
        .alias(column_name)
    )


def replace_null_with_one(column_name: str) -> pl.Expr:
    """
    Crea una expresión que reemplaza los valores nulos en una columna por el valor 1.

    Args:
        column_name (str): Nombre de la columna en la que se reemplazarán los valores nulos.

    Returns:
        pl.Expr: Expresión de Polars que reemplaza los valores nulos por 1 en la columna especificada.

    Note:
        - La columna resultante mantiene el nombre original.
        - Esta función es útil para columnas numéricas donde 1 es un valor neutro apropiado.

    Example:
        >>> df = pl.DataFrame({"FACTOR_DE_AJUSTE": [1.5, None, 2.0, None]})
        >>> df = df.with_columns(replace_null_with_one("FACTOR_DE_AJUSTE"))
        >>> print(df)
        shape: (4, 1)
        ┌──────────────────┐
        │ FACTOR_DE_AJUSTE │
        │ f64              │
        ╞══════════════════╡
        │ 1.5              │
        │ 1.0              │
        │ 2.0              │
        │ 1.0              │
        └──────────────────┘
    """
    return pl.col(column_name).fill_null(1).alias(column_name)
