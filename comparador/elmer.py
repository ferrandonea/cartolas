from pathlib import Path
import requests
from json import JSONDecodeError
from datetime import datetime
from cartolas.config import ELMER_FOLDER
import json
import logging
import time

logger = logging.getLogger(__name__)
from utiles.file_tools import (
    obtener_archivo_mas_reciente,
    obtener_fecha_creacion,
    leer_json,
)
from utiles.fechas import es_mismo_mes
import polars as pl

# Constantes para el manejo de fechas y archivos
# Formato YYYY-MM para el mes actual
CURRENT_DATE = datetime.now().strftime("%Y-%m")
# Timestamp completo para registro de actualizaciones
UPDATE_DATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# Nombre del archivo JSON basado en timestamp actual para garantizar unicidad
JSON_FILE_NAME = ELMER_FOLDER / f"{datetime.now().strftime('%Y%m%d%H%M%S')}.json"

# URL base para las consultas a El Mercurio Inversiones
ELMER_URL_BASE = (
    "https://www.elmercurio.com/inversiones/json/jsonTablaFull.aspx?idcategoria="
)

# ESTRUCTURA DE LOS DATOS
#
# "total_rows": int  = con el número de fondos
# "categoria": str = nombre de la categoría
# "cols": list(str) = nombres de las columnas
# "rows": list(dict[str, float|str]) = lista de diccionarios con los datos de cada fondo, por ejemplo
# {'Aratio': '-0,04',
#  'Fondo': 'Latam Equity B',
#  'FondoFull': '8098-B',
#  'M2': '0,05%',
#  'MminInv': '1',
#  'Moneda': '$',
#  'PlpagoD': '10',
#  'Rentb1 mes': '4,76%',
#  'Rentb12m': '-14,90%',
#  'Rentb1d': '1,13%',
#  'Rentb3m': '-0,24%',
#  'RentbY': '9,90%',
#  'Run': '8098',
#  'TAC': '2,27%',
#  'Tipoinv': 'APV / Ahorro Previsional Voluntario',
#  'adm': 'Principal',
#  'ajensen': '-0,05%',
#  'invNet1m': '-63.786.915',
#  'invNet1y': '-322.778.348',
#  'numParInst': '0',
#  'par': '2.099',
#  'patrim': '3.423.842.125',
#  'sharpe': '-0,97',
#  'treynor': '-0,01',
#  'varParInst1m': '',
#  'varParInst1y': '',
#  'varpar1Y': '-5,37%',
#  'varpar1m': '-0,62%',
#  'varpatrim1Y': '-21,81%',
#  'varpatrim1m': '2,80%',
#  'vcuota': '5.193,80',
#  'vol1Y': '0,95'}

# Columnas que queremos extraer de los datos
# Solo extraemos las columnas relevantes para nuestro análisis
COLUMNAS_RELEVANTES = ["Fondo", "FondoFull", "Moneda", "Run", "Tipoinv", "adm"]

# Número máximo de categorías a consultar en El Mercurio
MAX_NUMBER_OF_CATEGORIES = 30


def get_elmer_data(category_id: int, retries: int = 3) -> dict | None:
    """
    Obtiene los datos de una categoría específica desde El Mercurio Inversiones.

    Args:
        category_id (int): ID de la categoría a consultar
        retries (int): Número máximo de reintentos ante errores

    Returns:
        dict: Datos de la categoría o None si hay error
    """
    url = ELMER_URL_BASE + str(category_id)
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            datos = response.json()
            datos["num_categoria"] = category_id
            return datos
        except (requests.RequestException, JSONDecodeError) as e:
            logger.warning(
                "Categoría %d: intento %d/%d falló: %s",
                category_id, attempt, retries, e,
            )
            if attempt < retries:
                time.sleep(2 ** attempt)
    logger.error("Categoría %d: falló tras %d intentos", category_id, retries)
    return None


def filter_elmer_data(datos: dict) -> list[dict]:
    """
    Filtra y procesa los datos obtenidos de El Mercurio.

    Args:
        datos (dict): Diccionario con los datos crudos de El Mercurio

    Returns:
        list[dict]: Lista de diccionarios con los datos filtrados y procesados
    """
    # Extraemos y normalizamos los datos básicos
    # Convertimos la categoría a mayúsculas para consistencia
    categoria = datos["categoria"].upper()
    num_categoria = datos["num_categoria"]
    # Obtenemos la lista de fondos
    rows = datos["rows"]

    lista_fondos = []
    for row in rows:
        # Creamos un nuevo diccionario con las columnas relevantes en mayúsculas
        # Esto asegura consistencia en el formato de los datos
        new_dict = {key.upper(): row[key].upper() for key in COLUMNAS_RELEVANTES}
        # Agregamos información adicional
        new_dict["CATEGORIA"] = categoria
        new_dict["NUM_CATEGORIA"] = int(num_categoria)
        # Convertimos RUN a entero para facilitar operaciones numéricas
        new_dict["RUN_FM"] = int(new_dict.pop("RUN"))
        # Extraemos la serie del código completo del fondo
        new_dict["SERIE"] = new_dict["FONDOFULL"].split("-", 1)[1]
        # Agregamos fechas de referencia
        new_dict["FECHA"] = CURRENT_DATE
        new_dict["FECHA_ACTUALIZACION"] = UPDATE_DATE
        lista_fondos.append(new_dict)
    return lista_fondos


def get_all_elmer_data(max_number: int = MAX_NUMBER_OF_CATEGORIES) -> list[dict]:
    """
    Obtiene los datos de todas las categorías disponibles.

    Args:
        max_number (int): Número máximo de categorías a consultar

    Returns:
        list[dict]: Lista con todos los fondos de todas las categorías
    """
    lista_fondos = []
    failed = []
    for i in range(1, max_number):
        datos = get_elmer_data(i)
        if datos:
            lista_fondos.extend(filter_elmer_data(datos))
        else:
            failed.append(i)
    if failed:
        logger.warning("Categorías sin datos: %s", failed)
    logger.info(
        "Elmer: %d fondos de %d categorías",
        len(lista_fondos), max_number - 1 - len(failed),
    )
    return lista_fondos


def save_elmer_data(
    lista_fondos: list, filename: str = JSON_FILE_NAME,
):
    """
    Guarda la lista de fondos en un archivo JSON.

    Args:
        lista_fondos (list): Lista de diccionarios con los datos de los fondos
        filename (str): Ruta donde guardar el archivo
    """
    with open(filename, "w") as f:
        json.dump(lista_fondos, f)
    logger.info("Archivo %s grabado", filename)


def get_and_save_elmer_data(
    max_number: int = MAX_NUMBER_OF_CATEGORIES,
    filename: str = JSON_FILE_NAME,
) -> list[dict]:
    """
    Obtiene y guarda los datos de El Mercurio en un solo paso.

    Args:
        max_number (int): Número máximo de categorías a consultar
        filename (str): Ruta donde guardar el archivo

    Returns:
        list[dict]: Lista con todos los fondos procesados
    """
    lista_fondos = get_all_elmer_data(max_number=max_number)
    save_elmer_data(lista_fondos=lista_fondos, filename=filename)
    return lista_fondos


def last_elmer_data(
    elmerfolder: Path = ELMER_FOLDER,
) -> list[dict]:
    """
    Obtiene los datos más recientes, ya sea de archivo o descargándolos.

    Verifica si existe un archivo del mes actual y lo usa si está disponible.
    Si no existe o no es del mes actual, descarga datos nuevos.

    Args:
        elmerfolder (Path): Carpeta donde se almacenan los archivos

    Returns:
        list[dict]: Lista con los datos de los fondos más recientes
    """
    # Buscamos el archivo más reciente en la carpeta
    last_archivo = obtener_archivo_mas_reciente(elmerfolder)

    if not last_archivo:
        logger.info("EMOL: Bajando archivo nuevo")
        return get_and_save_elmer_data()

    last_archivo_date = obtener_fecha_creacion(last_archivo)
    if es_mismo_mes(last_archivo_date):
        logger.info("EMOL: Usando archivo histórico %s", last_archivo.stem)
        return leer_json(last_archivo)

    logger.info("EMOL: Bajando archivo nuevo")
    return get_and_save_elmer_data()


def last_elmer_data_as_polars(
    elmerfolder: Path = ELMER_FOLDER,
) -> pl.LazyFrame:
    return pl.LazyFrame(last_elmer_data(elmerfolder=elmerfolder)).with_columns(
        pl.col("RUN_FM").cast(pl.UInt16)
    )


if __name__ == "__main__":
    # Ejecuta la función principal si se corre el script directamente
    print(last_elmer_data())
    df = last_elmer_data_as_polars()
    print(df.columns)
    print(df.tail())
    print(df.select("TIPOINV").unique())
