"""Descarga los valores cuota diarios de las series solicitadas desde 2020.

Extrae desde los parquets anuales locales (`cartolas/data/yearly/`) la serie
diaria de VALOR_CUOTA para los pares RUN_FM/SERIE solicitados y la exporta a
CSV en formato ancho (una columna por par RUN-SERIE).
"""

from datetime import date
from pathlib import Path

import polars as pl

from cartolas.config import PARQUET_FOLDER_YEAR

# Pares (RUN_FM, SERIE) a extraer. El orden define el orden de las columnas.
PARES_RUN_SERIE: list[tuple[int, str]] = [
    (8316, "VIVIENDA"),
    (8317, "VIVIENDA"),
    (8807, "VIVIENDA"),
    (9291, "VIVIENDA"),
    (8319, "VIVIENDA"),
    (9809, "B"),
    (9810, "VIVIENDA"),
    (9811, "B"),
    (8846, "VIVIENDA"),
    (8536, "VIVIENDA"),
]
FECHA_DESDE = date(2020, 1, 1)
OUTPUT_CSV = Path("valor_cuota_vivienda.csv")


def _filtro_pares(pares: list[tuple[int, str]]) -> pl.Expr:
    """Construye el OR de condiciones (RUN_FM, SERIE)."""
    condiciones = [
        (pl.col("RUN_FM") == run) & (pl.col("SERIE") == serie) for run, serie in pares
    ]
    return pl.any_horizontal(condiciones)


def get_valor_cuota(
    parquet_folder: str | Path = PARQUET_FOLDER_YEAR,
    pares: list[tuple[int, str]] = PARES_RUN_SERIE,
    fecha_desde: date = FECHA_DESDE,
) -> pl.DataFrame:
    """Retorna el valor cuota diario (formato largo) de los pares pedidos."""
    folder = Path(parquet_folder)
    # Solo los años relevantes: evita escanear 2007-2019.
    files = sorted(
        f
        for f in folder.glob("cartolas_*.parquet")
        if f.stem.split("_")[-1].isdigit() and int(f.stem.split("_")[-1]) >= fecha_desde.year
    )
    if not files:
        raise FileNotFoundError(f"No hay parquets desde {fecha_desde.year} en {folder}")

    return (
        pl.scan_parquet(files)
        .filter(_filtro_pares(pares) & (pl.col("FECHA_INF") >= fecha_desde))
        .select(["FECHA_INF", "RUN_FM", "SERIE", "MONEDA", "VALOR_CUOTA"])
        .with_columns(
            (pl.col("RUN_FM").cast(pl.String) + "-" + pl.col("SERIE")).alias("FONDO")
        )
        .sort(["FECHA_INF", "RUN_FM", "SERIE"])
        .collect()
    )


def pivot_valor_cuota(
    df: pl.DataFrame, pares: list[tuple[int, str]] = PARES_RUN_SERIE
) -> pl.DataFrame:
    """Pivotea a formato ancho: una fila por fecha, una columna por RUN-SERIE."""
    wide = df.pivot(index="FECHA_INF", on="FONDO", values="VALOR_CUOTA").sort("FECHA_INF")
    columnas = ["FECHA_INF"] + [
        f"{run}-{serie}" for run, serie in pares if f"{run}-{serie}" in wide.columns
    ]
    return wide.select(columnas)


if __name__ == "__main__":
    df = get_valor_cuota()
    print(f"Filas: {df.height}")
    print(
        df.group_by("FONDO")
        .agg(
            pl.len().alias("DIAS"),
            pl.col("FECHA_INF").min().alias("DESDE"),
            pl.col("FECHA_INF").max().alias("HASTA"),
        )
        .sort("FONDO")
    )

    wide = pivot_valor_cuota(df)
    print(wide)

    wide.write_csv(OUTPUT_CSV)
    print(f"Escrito: {OUTPUT_CSV.resolve()}")
