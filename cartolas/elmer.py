import requests
from json import JSONDecodeError
from pprint import pprint
from datetime import datetime
from cartolas.config import ELMER_FOLDER
import json

CURRENT_DATE = datetime.now().strftime("%Y-%m")
UPDATE_DATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
JSON_FILE_NAME = ELMER_FOLDER /  f'{datetime.now().strftime("%Y%m%d%H%M%S")}.json'

# Es del estilo "https://www.elmercurio.com/inversiones/json/jsonTablaFull.aspx?idcategoria={category_id}"
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

COLUMNAS_RELEVANTES = ["Fondo", "FondoFull", "Moneda", "Run", "Tipoinv", "adm"]

MAX_NUMBER_OF_CATEGORIES = 30

def get_elmer_data(category_id: int, verbose: bool = False) -> dict:
    url = ELMER_URL_BASE + str(category_id)
    response = requests.get(url)

    try:
        datos = response.json()
        datos["num_categoria"] = category_id
    except JSONDecodeError:
        print(f"Error al obtener los datos de la categoría {category_id}") if verbose else None
        datos = None
    
    return datos


def filter_elmer_data(datos: dict) -> dict:
    categoria = datos["categoria"].upper()
    num_categoria = datos["num_categoria"]
    rows = datos["rows"]
    lista_fondos = []
    for row in rows:
        new_dict = {key.upper(): row[key].upper() for key in COLUMNAS_RELEVANTES}
        new_dict["CATEGORIA"] = categoria
        new_dict["NUM_CATEGORIA"] = int(num_categoria)
        new_dict["RUN"] = int(new_dict["RUN"])
        new_dict["SERIE"] = new_dict["FONDOFULL"].split("-", 1)[1]
        new_dict["FECHA"] = CURRENT_DATE
        new_dict["FECHA_ACTUALIZACION"] = UPDATE_DATE
        lista_fondos.append(new_dict)
    return lista_fondos

def get_all_elmer_data(max_number: int = MAX_NUMBER_OF_CATEGORIES):
    lista_fondos = []
    for i in range(1, max_number):
        datos = get_elmer_data(i)
        if datos:
            lista_fondos.extend(filter_elmer_data(datos))
    return lista_fondos

def save_elmer_data(lista_fondos: list, filename: str = JSON_FILE_NAME):
    with open(ELMER_FOLDER / f"{l['NUM_CATEGORIA']}.json", "w") as f:
        json.dump(l, f)

if __name__ == "__main__":
    lista = get_all_elmer_data()
    num_l = []
    for l in lista:
        num_l.append(l["NUM_CATEGORIA"])
    print(list(set(num_l)))
    print(JSON_FILE_NAME)