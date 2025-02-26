"""
Módulo para obtener y procesar datos del Banco Central de Chile.

Este módulo proporciona funciones para descargar, transformar y almacenar
datos económicos del Banco Central de Chile, como tipos de cambio y otras
series temporales económicas.
"""

# Importamos las bibliotecas necesarias
from dotenv import dotenv_values  # Para cargar variables de entorno
import bcchapi  # API oficial del Banco Central de Chile
from datetime import datetime, timedelta
import polars as pl  # Biblioteca para procesamiento de datos
from cartolas.config import BCCH_FOLDER  # Configuración de carpetas
import json 
from pathlib import Path  # Manejo de rutas de archivos
env_variables = dotenv_values(".env")  # Cargamos variables de entorno desde .env

# Definimos la fecha hasta la cual queremos datos (ayer)
LAST_DATE = datetime.now() - timedelta(days=1)

# Credenciales para la API del Banco Central
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]

# Rutas para guardar y leer datos
PARQUET_PATH = BCCH_FOLDER / "bcch.parquet"  # Datos en formato Parquet
JSON_PATH = BCCH_FOLDER / "bcentral_tickers.json"  # Metadatos de series temporales

# Hacemos login
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)  # Inicializamos la API del BCCh

def read_bcentral_tickers(path: Path = JSON_PATH):
    """
    Lee el archivo JSON que contiene los tickers del Banco Central de Chile.
    
    Args:
        path (Path, opcional): Ruta al archivo JSON. Por defecto es JSON_PATH.
        
    Returns:
        dict: Diccionario con los tickers y sus metadatos.
    """
    # Abrimos el archivo JSON y lo cargamos como diccionario
    with open(path, "r") as f:
        return json.load(f)

# Cargamos los datos de tickers y preparamos listas de nombres y códigos
DATOS_JSON = read_bcentral_tickers()  # Diccionario con metadatos de series
NOMBRES = list(DATOS_JSON.keys())  # Lista de nombres de series (ej: "DOLAR", "EURO")
TICKERS = [DATOS_JSON[nombre]["TICKER"] for nombre in NOMBRES]  # Lista de códigos de series


def baja_datos_bcch(
    tickers: str = TICKERS,
    nombres: str = NOMBRES,
    bfill: bool = True,
    last_date: datetime = LAST_DATE,
):
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
        return BCCh.cuadro(series=tickers, nombres=nombres, hasta=last_date).ffill()
    else:
        return BCCh.cuadro(series=tickers, nombres=nombres, hasta=last_date)


def baja_bcch_as_polars(
    tickers: str = TICKERS,
    nombres: str = NOMBRES,
    bfill: bool = True,
    last_date: datetime = LAST_DATE,
    df_index_name: str = "FECHA_INF",
    as_lazy: bool = False,
):
    """
    Descarga datos del Banco Central de Chile y los convierte a formato Polars.

    Args:
        tickers (str, opcional): Lista de códigos de series temporales del BCCh. Por defecto usa TICKERS.
        nombres (str, opcional): Lista de nombres descriptivos para las series. Por defecto usa NOMBRES.
        bfill (bool, opcional): Si es True, rellena datos faltantes hacia adelante. Por defecto es True.
        last_date (datetime, opcional): Fecha final para la descarga de datos. Por defecto es LAST_DATE.
        df_index_name (str, opcional): Nombre para el índice del DataFrame. Por defecto es "FECHA_INF".
        as_lazy (bool, opcional): Si es True, retorna un LazyFrame en lugar de un DataFrame. Por defecto es False.

    Returns:
        polars.DataFrame o polars.LazyFrame: DataFrame de Polars con las series temporales solicitadas.
    """
    # Obtiene los datos usando la función baja_datos_bcch
    df = baja_datos_bcch(tickers, nombres, bfill, last_date)
    # Asigna nombre al índice del DataFrame
    df.index.name = df_index_name
    # Convierte el DataFrame de pandas a Polars manteniendo el índice
    bcch_df = pl.from_pandas(df, include_index=True)
    # Convierte la columna FECHA_INF a tipo Date
    bcch_df = bcch_df.with_columns(pl.col(df_index_name).cast(pl.Date))
    
    # Retorna un LazyFrame si as_lazy es True, de lo contrario retorna un DataFrame
    return bcch_df.lazy() if as_lazy else bcch_df

def baja_dolar_observado_as_polars(as_lazy: bool = False):
    """
    Descarga datos del dólar observado desde el Banco Central de Chile.
    
    Args:
        as_lazy (bool, opcional): Si es True, retorna un LazyFrame en lugar de un DataFrame. Por defecto es False.
        
    Returns:
        polars.DataFrame o polars.LazyFrame: DataFrame con los datos del dólar observado.
    """
    # Descarga solo la serie del dólar observado
    df = baja_bcch_as_polars([DATOS_JSON["DOLAR"]["TICKER"]], ["DOLAR"], as_lazy=as_lazy)
    return df

def baja_dolar_y_euro_as_polars(as_lazy: bool = False):
    """
    Descarga datos del dólar y euro desde el Banco Central de Chile.
    
    Args:
        as_lazy (bool, opcional): Si es True, retorna un LazyFrame en lugar de un DataFrame. Por defecto es False.
        
    Returns:
        polars.DataFrame o polars.LazyFrame: DataFrame con los datos del dólar y euro.
    """
    # Descarga las series del dólar y euro
    df = baja_bcch_as_polars([DATOS_JSON["DOLAR"]["TICKER"], DATOS_JSON["EURO"]["TICKER"]], ["DOLAR", "EUR"], as_lazy=as_lazy)
    return df

def save_bcch_as_parquet(path: str = PARQUET_PATH):
    """
    Descarga datos del Banco Central y los guarda en formato Parquet.
    
    Args:
        path (str, opcional): Ruta donde se guardará el archivo Parquet. Por defecto es PARQUET_PATH.
    """
    # Descarga todos los datos en formato lazy
    df = baja_bcch_as_polars(as_lazy=True)
    # Materializa y guarda en formato Parquet
    df.collect().write_parquet(path)
    
def load_bcch_from_parquet(path: str = PARQUET_PATH):
    """
    Carga datos del Banco Central desde un archivo Parquet.
    
    Args:
        path (str, opcional): Ruta del archivo Parquet a cargar. Por defecto es PARQUET_PATH.
        
    Returns:
        polars.LazyFrame: LazyFrame con los datos cargados.
    """
    # Carga el archivo Parquet como LazyFrame (sin materializar en memoria)
    return pl.scan_parquet(path)

def get_last_date_from_parquet(df: pl.LazyFrame, date_field: str = "FECHA_INF"):
    """
    Obtiene la fecha más reciente de un DataFrame.
    
    Args:
        df (pl.LazyFrame): DataFrame del cual obtener la fecha más reciente.
        date_field (str, opcional): Nombre del campo de fecha. Por defecto es "FECHA_INF".
        
    Returns:
        date: La fecha más reciente encontrada en el DataFrame.
    """    
    # Materializa el DataFrame, selecciona el valor máximo de la columna de fecha y lo convierte a lista
    return df.collect().select(pl.col(date_field).max()).to_series().to_list()[0]

def update_bcch_parquet(path: str = PARQUET_PATH) -> pl.LazyFrame:
    """
    Actualiza el archivo Parquet con datos del Banco Central si hay datos nuevos disponibles.
    
    Args:
        path (str, opcional): Ruta del archivo Parquet. Por defecto es PARQUET_PATH.
        
    Returns:
        polars.LazyFrame: LazyFrame con los datos actualizados.
    """
    try:
        # Intenta cargar el archivo Parquet existente
        df = load_bcch_from_parquet()
        # Obtiene la fecha más reciente en los datos
        last_date = get_last_date_from_parquet(df)        
    except FileNotFoundError:   
        # Si el archivo no existe, establece una fecha muy antigua para forzar la descarga
        last_date = datetime(1970, 1, 1).date() # una fecha muy antigua
        print("BCCH: No se encontró el archivo de datos del BCCh")

    # Compara la fecha más reciente con la fecha hasta la cual queremos datos
    if last_date >= LAST_DATE.date():
        # Si ya tenemos datos actualizados, no hacemos nada
        print("BCCH: No hay datos nuevos del BCCh")
        return df
    else:
        # Si necesitamos datos más recientes, descargamos y guardamos
        print(f"BCCH: Última fecha en el archivo: {last_date}")
        print("BCCH: Actualizando datos del BCCh")
        df = baja_bcch_as_polars(as_lazy=True)
        df.collect().write_parquet(path)
    return df

def update_bcch_for_cartolas(path: str = PARQUET_PATH):
    """
    Actualiza y prepara los datos del Banco Central para su uso con cartolas.
    
    Esta función actualiza los datos del Banco Central, selecciona las columnas relevantes
    (FECHA_INF, DOLAR, EURO) y transforma los datos para tener una columna de moneda y valor.
    
    Args:
        path (str, opcional): Ruta del archivo Parquet. Por defecto es PARQUET_PATH.
        
    Returns:
        polars.LazyFrame: LazyFrame con los datos transformados para uso con cartolas.
    """
    df = (update_bcch_parquet()
          # Seleccionamos solo las columnas que nos interesan
          .select(pl.col("FECHA_INF"), pl.col("DOLAR"), pl.col("EURO"))
          # Renombramos las columnas para mantener consistencia con otros datos
          .rename({"DOLAR":"PROM", "EURO":"EUR"})
          # Transformamos de formato ancho a largo (unpivot)
          .unpivot(
              index=["FECHA_INF"], 
              on=["PROM", "EUR"], 
              variable_name="MONEDA", 
              value_name="TIPO_CAMBIO"
          ))
    
    # TODO: Unir esto con el json de los tickers
    return df
    
if __name__ == "__main__":
    """
    Punto de entrada principal cuando se ejecuta el módulo directamente.
    Actualiza los datos del Banco Central y muestra los resultados.
    """
    # Actualiza los datos y los muestra en consola
    df = update_bcch_for_cartolas()
    print(df.collect())
