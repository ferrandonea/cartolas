from dotenv import dotenv_values
import bcchapi
from datetime import datetime, timedelta
import polars as pl

env_variables = dotenv_values(".env")

LAST_DATE = datetime.now() - timedelta(days = 1)

BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]

# TODO: Esto debiera venir de un archivo de configuración y además podría esto ser su propio módulo

UF = "F073.UFF.PRE.Z.D"	# Unidad de fomento (UF)
DOLAR_OBSERVADO = "F073.TCO.PRE.Z.D"	# Tipo de cambio del dólar observado diario
ORO = "F019.PPB.PRE.44.D"	# Precio del oro, dólares la onza troy  
TPM = "F022.TPM.TIN.D001.NO.Z.D"	# Tasa de política monetaria (TPM) (porcentaje)
UTM = "F073.UTR.PRE.Z.M"	# Unidad tributaria mensual (UTM)

TICKERS = [UF, DOLAR_OBSERVADO, ORO, TPM, UTM]
NOMBRES = ["UF", "Dolar observado", "Oro", "TPM", "UTM"]

# Hacemos login
BCCh = bcchapi.Siete(usr = BCCH_USER, pwd = BCCH_PASS)

def baja_datos_bcch(tickers: str = TICKERS, nombres: str = NOMBRES, bfill: bool = True, last_date: datetime = LAST_DATE):  
    """
    Descarga datos históricos del Banco Central de Chile para los tickers especificados.

    Args:
        tickers (str, opcional): Lista de códigos de series temporales del BCCh. Por defecto usa TICKERS.
        nombres (str, opcional): Lista de nombres descriptivos para las series. Por defecto usa NOMBRES.
        bfill (bool, opcional): Si es True, rellena datos faltantes hacia adelante. Por defecto es True.
        last_date (datetime, opcional): Fecha final para la descarga de datos. Por defecto es LAST_DATE.

    Returns:
        pandas.DataFrame: DataFrame con las series temporales solicitadas, indexado por fecha.
    """
    # Si bfill es True, rellena datos faltantes hacia adelante
    if bfill:
        return BCCh.cuadro(series = tickers, nombres = nombres, hasta = last_date).ffill()
    else:
        return BCCh.cuadro(series = tickers, nombres = nombres, hasta = last_date)

def baja_bcch_as_polars(tickers: str = TICKERS, nombres: str = NOMBRES, bfill: bool = True, last_date: datetime = LAST_DATE, df_index_name: str = "FECHA_INF"):
    """
    Descarga datos del Banco Central de Chile y los convierte a formato Polars.

    Args:
        tickers (str, opcional): Lista de códigos de series temporales del BCCh. Por defecto usa TICKERS.
        nombres (str, opcional): Lista de nombres descriptivos para las series. Por defecto usa NOMBRES.
        bfill (bool, opcional): Si es True, rellena datos faltantes hacia adelante. Por defecto es True.
        last_date (datetime, opcional): Fecha final para la descarga de datos. Por defecto es LAST_DATE.
        df_index_name (str, opcional): Nombre para el índice del DataFrame. Por defecto es "FECHA_INF".

    Returns:
        polars.DataFrame: DataFrame de Polars con las series temporales solicitadas.
    """
    # Obtiene los datos usando la función baja_datos_bcch
    df = baja_datos_bcch(tickers, nombres, bfill, last_date)
    # Asigna nombre al índice del DataFrame
    df.index.name = df_index_name
    # Convierte el DataFrame de pandas a Polars manteniendo el índice
    return pl.from_pandas(df, include_index = True)

if __name__ == "__main__":
    df_polars = baja_bcch_as_polars()
    print (df_polars.tail(20))  