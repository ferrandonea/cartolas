"""Utilidades de manejo de archivos"""

import json
import logging
import secrets
from pathlib import Path
from datetime import datetime
from typing import Union, Any, Optional


logger = logging.getLogger(__name__)

HASH_LENGTH = 12
# Tamaño mínimo de las cartolas
MIN_FILE_SIZE = 1000  # 1 KB
WILDCARD_CARTOLAS_TXT = "ffmm*.txt"


def generate_hash_name(length=HASH_LENGTH) -> str:
    """
    Genera un nombre de archivo hash aleatorio.

    Args:
        length (int, opcional): Longitud del hash generado. Por defecto es 12.

    Returns:
        str: Los primeros 'length' caracteres de un token hexadecimal aleatorio seguro.
    """
    return secrets.token_hex(length)[:length]


def generate_hash_image_name(length=HASH_LENGTH) -> str:
    """
    Genera un nombre de archivo hash aleatorio con extensión .png.

    Args:
        length (int, opcional): Longitud del hash generado. Por defecto es 12.

    Returns:
        str: Nombre de archivo hash con extensión .png.
    """
    return generate_hash_name(length=length) + ".png"


def clean_txt_folder(
    folder: str | Path,
    wildcard: str = WILDCARD_CARTOLAS_TXT,
    delete_all: bool = False,
    min_file_size: int = MIN_FILE_SIZE,
) -> None:
    """
    Elimina archivos de una carpeta basándose en su tamaño o elimina todos los archivos.

    Args:
        folder (str | Path): Ruta de la carpeta donde buscar los archivos.
        wildcard (str): Patrón de los archivos a procesar. Por defecto, "ffmm*.txt".
        delete_all (bool): Si es True, elimina todos los archivos que coincidan con el patrón.
                           Si es False, solo elimina archivos menores a min_file_size.
        min_file_size (int): Tamaño mínimo de archivo en bytes. Archivos menores a este
                             tamaño serán eliminados si delete_all es False.

    Returns:
        None: No retorna ningún valor.

    Note:
        - Si delete_all es False, se asume que los archivos menores a min_file_size no tienen
          información útil y son eliminados.
    Example:
        >>> clean_txt_folder(Path("data/txt"), delete_all=True)
        Archivo ffmm_20230101 borrado
        Archivo ffmm_20230102 borrado
        >>> clean_txt_folder(Path("data/txt"))
        Archivo ffmm_20230101 borrado porque es menor a 1.00 KB
    """
    folder_path = Path(folder)

    for file in folder_path.glob(wildcard):
        if file.stat().st_size < min_file_size or delete_all:
            file.unlink()
            if delete_all:
                logger.debug(f"Archivo {file.stem} borrado")
            else:
                logger.debug(
                    f"Archivo {file.stem} borrado porque es menor a {min_file_size / 1000:.2f} KB"
                )

    return None


def obtener_archivo_mas_reciente(directorio: Path) -> Optional[Path]:
    """
    Encuentra el archivo más recientemente creado en el directorio especificado.

    Args:
        directorio (Path): Ruta al directorio donde buscar

    Returns:
        Optional[Path]: Ruta al archivo más reciente, o None si el directorio está vacío

    Examples:
        >>> directorio = Path("data/parquet")
        >>> archivo_reciente = obtener_archivo_mas_reciente(directorio)
        >>> if archivo_reciente:
        ...     print(f"Archivo más reciente: {archivo_reciente.name}")
    """
    try:
        # Obtener todos los archivos del directorio (no directorios)
        archivos = [f for f in directorio.iterdir() if f.is_file()]

        if not archivos:
            return None

        # Encontrar el archivo con la fecha de modificación más reciente
        archivo_reciente = max(archivos, key=lambda x: x.stat().st_mtime)

        return archivo_reciente

    except Exception as e:
        logger.error(f"Error al buscar archivo más reciente: {e}")
        return None


def obtener_fecha_creacion(archivo: Path) -> Optional[datetime]:
    """
    Obtiene la fecha de creación de un archivo.

    Args:
        archivo (Path): Ruta al archivo del cual queremos obtener la fecha de creación

    Returns:
        Optional[datetime]: Fecha de creación del archivo, o None si hay error

    Examples:
        >>> archivo = Path("data/parquet/ejemplo.parquet")
        >>> fecha = obtener_fecha_creacion(archivo)
        >>> if fecha:
        ...     print(f"Archivo creado el: {fecha.strftime('%Y-%m-%d %H:%M:%S')}")
    """
    try:
        # Obtener timestamp de creación y convertirlo a datetime
        timestamp = archivo.stat().st_ctime
        fecha_creacion = datetime.fromtimestamp(timestamp)

        return fecha_creacion

    except Exception as e:
        logger.error(f"Error al obtener fecha de creación de {archivo.name}: {e}")
        return None


def leer_json(ruta_archivo: Union[str, Path]) -> Optional[dict[str, Any]]:
    """
    Lee un archivo JSON y retorna su contenido.

    Args:
        ruta_archivo (Union[str, Path]): Ruta al archivo JSON

    Returns:
        Optional[Dict[str, Any]]: Contenido del archivo JSON como diccionario,
            o None si hay error

    Examples:
        >>> datos = leer_json('config.json')
        >>> if datos:
        ...     print(datos['nombre'])
    """
    try:
        # Convertir a Path si es string
        ruta = Path(ruta_archivo)

        # Verificar que el archivo existe
        if not ruta.exists():
            logger.error(f"El archivo {ruta} no existe")
            return None

        # Leer el archivo JSON
        with ruta.open("r", encoding="utf-8") as archivo:
            datos = json.load(archivo)

        return datos

    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Error al leer archivo: {e}")
        return None


if __name__ == "__main__":
    from cartolas.config import CARTOLAS_FOLDER

    # Genera un nombre de archivo hash de 10 caracteres
    file_name = generate_hash_name() + ".png"

    print(file_name)
    print(generate_hash_image_name())
    clean_txt_folder(folder=CARTOLAS_FOLDER)
    print(CARTOLAS_FOLDER)
    for archivo in CARTOLAS_FOLDER.glob(WILDCARD_CARTOLAS_TXT):
        print(archivo.stat().st_size)
