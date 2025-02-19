from pathlib import Path
import requests
from json import JSONDecodeError
from datetime import datetime
from cartolas.config import ELMER_FOLDER
import json
from utiles.file_tools import (
    obtener_archivo_mas_reciente,
    obtener_fecha_creacion,
    leer_json,
)
from utiles.fechas import es_mismo_mes

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


def get_elmer_data(category_id: int, verbose: bool = False) -> dict:
    """
    Obtiene los datos de una categoría específica desde El Mercurio Inversiones.

    Args:
        category_id (int): ID de la categoría a consultar
        verbose (bool): Si True, muestra mensajes de error. Por defecto False

    Returns:
        dict: Datos de la categoría o None si hay error
    """
    # Construye la URL completa para la categoría específica
    url = ELMER_URL_BASE + str(category_id)
    # Realiza la petición HTTP GET
    response = requests.get(url)

    try:
        # Intenta parsear la respuesta como JSON
        datos = response.json()
        # Agrega el ID de categoría a los datos para referencia
        datos["num_categoria"] = category_id
    except JSONDecodeError:
        # Si hay error en el parseo JSON, muestra mensaje si verbose es True
        print(
            f"Error al obtener los datos de la categoría {category_id}"
        ) if verbose else None
        datos = None

    return datos


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
        new_dict["RUN"] = int(new_dict["RUN"])
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
    # Iteramos sobre todas las categorías posibles
    for i in range(1, max_number):
        # Obtenemos datos de cada categoría
        datos = get_elmer_data(i)
        if datos:
            # Si hay datos, los procesamos y agregamos a la lista
            lista_fondos.extend(filter_elmer_data(datos))
    return lista_fondos


def save_elmer_data(
    lista_fondos: list, filename: str = JSON_FILE_NAME, verbose: bool = False
):
    """
    Guarda la lista de fondos en un archivo JSON.

    Args:
        lista_fondos (list): Lista de diccionarios con los datos de los fondos
        filename (str): Ruta donde guardar el archivo
        verbose (bool): Si True, muestra mensaje de confirmación
    """
    # Abrimos el archivo en modo escritura
    with open(filename, "w") as f:
        # Guardamos la lista como JSON
        json.dump(lista_fondos, f)
    # Mostramos mensaje de confirmación si verbose es True
    print(f"Archivo {filename} grabado") if verbose else None


def get_and_save_elmer_data(
    max_number: int = MAX_NUMBER_OF_CATEGORIES,
    filename: str = JSON_FILE_NAME,
    verbose: bool = False,
) -> list[dict]:
    """
    Obtiene y guarda los datos de El Mercurio en un solo paso.

    Args:
        max_number (int): Número máximo de categorías a consultar
        filename (str): Ruta donde guardar el archivo
        verbose (bool): Si True, muestra mensajes de progreso

    Returns:
        list[dict]: Lista con todos los fondos procesados
    """
    # Obtenemos todos los datos
    lista_fondos = get_all_elmer_data(max_number=max_number)
    # Guardamos los datos en archivo
    save_elmer_data(lista_fondos=lista_fondos, filename=filename, verbose=verbose)
    return lista_fondos


def last_elmer_data(
    elmerfolder: Path = ELMER_FOLDER, verbose: bool = True
) -> list[dict]:
    """
    Obtiene los datos más recientes, ya sea de archivo o descargándolos.

    Verifica si existe un archivo del mes actual y lo usa si está disponible.
    Si no existe o no es del mes actual, descarga datos nuevos.

    Args:
        elmerfolder (Path): Carpeta donde se almacenan los archivos
        verbose (bool): Si True, muestra mensajes de progreso

    Returns:
        list[dict]: Lista con los datos de los fondos más recientes
    """
    # Buscamos el archivo más reciente en la carpeta
    last_archivo = obtener_archivo_mas_reciente(elmerfolder)

    # Si no hay archivo, descargamos datos nuevos
    if not last_archivo:
        print("Bajando archivo nuevo")
        return get_and_save_elmer_data()

    # Verificamos si el archivo es del mes actual
    last_archivo_date = obtener_fecha_creacion(last_archivo)
    # Si es del mes actual, usamos el archivo existente
    if es_mismo_mes(last_archivo_date):
        print(f"Usando archivo histórico {last_archivo.stem}")
        return leer_json(last_archivo)

    # Si el archivo no es del mes actual, descargamos datos nuevos
    print("Bajando archivo nuevo")
    return get_and_save_elmer_data()


if __name__ == "__main__":
    # Ejecuta la función principal si se corre el script directamente
    last_elmer_data()
