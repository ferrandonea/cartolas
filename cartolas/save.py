import polars as pl
from pathlib import Path
from utiles.decorators import timer

@timer
def save_lazyframe_to_parquet(
    lazy_df: pl.LazyFrame, filename: str | Path, unique: bool = True
) -> None:
    """Graba un LazyFrame en un archivo Parquet.

    Args:
        lazy_df (pl.LazyFrame): DataFrame de Polars en modo lazy.
        filename (str | Path): Nombre del archivo o ruta donde se guardará el archivo Parquet.
        unique (bool, optional): Si se deben eliminar filas duplicadas antes de guardar. Defaults to True.
    """
    # Elimina filas duplicadas si es necesario
    lazy_df = lazy_df.unique() if unique else lazy_df
    # Colecta los datos y los guarda en un archivo Parquet
    lazy_df.collect().write_parquet(filename)
    # Imprime un mensaje de éxito
    print(f"Archivo parquet grabado con éxito en {filename}")
