"""Baja la identifiación de fondos mutuos desde la CMF"""

import polars as pl
import requests
import io


def get_fund_identification() -> str:
    """Baja la identifiación de fondos mutuos desde la CMF

    Returns:
        str: Texto con la información de identificación de fondos mutuos
    """
    url = "https://www.cmfchile.cl/institucional/estadisticas/fm_ident2.php"

    # Definir headers con referrer para simular una solicitud desde un navegador
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.cmfchile.cl/institucional/estadisticas/fm_estadisticas.php",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Connection": "keep-alive",
    }

    # Realizar la solicitud con los headers
    response = requests.get(url, headers=headers)

    return response.text


def cmf_text_to_df(text: str) -> pl.DataFrame:
    """
    Convierte el texto de la identificación de fondos mutuos desde la CMF a un DataFrame de Polars

    Args:
        text: Texto con los datos de la CMF

    Returns:
        pl.DataFrame: DataFrame con los datos procesados y tipos correctos
    """
    # Eliminar los $$ al final de cada línea
    clean_text = "\n".join(
        [line.replace("$$", "") for line in text.split("\n") if line.strip()]
    )

    # Leer el CSV con nombres de columnas
    df = pl.read_csv(
        io.StringIO(clean_text),
        separator=";",
        has_header=True,
        new_columns=[
            "RUN_ADM",
            "NOMBRE_ADM",
            "RUN_FM",
            "NOMBRE_FM",
            "NOMBRE_CORTO",
            "FECHA_DEPOSITO",
            "NUMERO_REGISTRO",
            "TIPO_FONDO",
            "FECHA_INICIO",
            "FECHA_TERMINO",
        ],
    )

    # Convertir las columnas de fechas
    date_columns = ["FECHA_DEPOSITO", "FECHA_INICIO", "FECHA_TERMINO"]

    # Convertir cada columna de fecha usando str.strptime
    for col in date_columns:
        df = df.with_columns(
            pl.col(col)
            .str.strptime(pl.Date, format="%d/%m/%Y", strict=False)
            .alias(col)
        )

    # Convertir otras columnas a tipos apropiados
    df = df.with_columns(
        [
            pl.col("RUN_ADM").cast(pl.Utf8),
            pl.col("RUN_FM").cast(pl.Utf8),
            pl.col("NUMERO_REGISTRO").cast(pl.Utf8),
            # pl.col("TIPO_FONDO").cast(pl.Int8)
        ]
    )

    return df


def download_fund_identification() -> pl.DataFrame:
    """Descarga el texto de la identificación de fondos mutuos desde la CMF"""
    text_cmf = get_fund_identification()
    df = cmf_text_to_df(text_cmf)
    columnas = {
        "RUN_ADM": pl.UInt32,
        "NOMBRE_ADM": pl.Utf8,
        "RUN_FM": pl.UInt16,
        "NOMBRE_FM": pl.Utf8,
        "NOMBRE_CORTO": pl.Utf8,
        "FECHA_DEPOSITO": pl.Date,
        "NUMERO_REGISTRO": pl.UInt16,
        "TIPO_FONDO": pl.UInt8,
        "FECHA_INICIO": pl.Date,
        "FECHA_TERMINO": pl.Date,
        "MONEDA": pl.Utf8,
    }

    df.columns = [
        "RUN_ADM",
        "NOMBRE_ADM",
        "RUN_FM",
        "NOMBRE_FM",
        "NOMBRE_CORTO",
        "FECHA_DEPOSITO",
        "NUMERO_REGISTRO",
        "TIPO_FONDO",
        "FECHA_INICIO",
        "FECHA_TERMINO",
        "MONEDA",
    ]
    # df.dtypes = [pl.Utf8, pl.Utf8, pl.Utf8, pl.Utf8, pl.Utf8, pl.Date, pl.Utf8, pl.Utf8, pl.Date, pl.Date, pl.Utf8]
    return df


