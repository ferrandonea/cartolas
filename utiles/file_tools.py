"""Utilidades de manejo de archivos"""

import hashlib
import random
import string
from pathlib import Path

HASH_LENGTH = 12
# Tamaño mínimo de las cartolas
MIN_FILE_SIZE = 1000  # 1 KB
WILDCARD_CARTOLAS_TXT = "ffmm*.txt"


def generate_hash_name(length=HASH_LENGTH):
    # Genera una cadena aleatoria
    random_string = "".join(
        random.choices(string.ascii_letters + string.digits, k=length)
    )
    # Crea un hash de la cadena aleatoria
    hash_object = hashlib.sha256(random_string.encode())
    # Devuelve los primeros 'length' caracteres del hash
    return hash_object.hexdigest()[:length]


def generate_hash_image_name(lenght=HASH_LENGTH):
    return generate_hash_name(length=lenght) + ".png"


# Este import debe estar acá sino hay un error de importación circular
# El comentario de noqa es para que no huevee con el orden de los imports ruff
from cartolas.config import CARTOLAS_FOLDER # noqa: E402


def clean_txt_folder(
    folder: str | Path = CARTOLAS_FOLDER,
    wildcard: str = WILDCARD_CARTOLAS_TXT,
    delete_all: bool = False,
    min_file_size: int = MIN_FILE_SIZE,
) -> None | bool:
    """
    Elimina archivos de una carpeta basándose en su tamaño o elimina todos los archivos.

    Args:
        folder (str | Path): Ruta de la carpeta donde buscar los archivos.
                             Por defecto, CURRENT_FOLDER/DOWNLOAD_FOLDER.
        wildcard (str): Patrón de los archivos a procesar. Por defecto, "ffmm*.txt".
        delete_all (bool): Si es True, elimina todos los archivos que coincidan con el patrón.
                           Si es False, solo elimina archivos menores a min_file_size.
        min_file_size (int): Tamaño mínimo de archivo en bytes. Archivos menores a este
                             tamaño serán eliminados si delete_all es False.

    Returns:
        None | bool: None cuando se eliminan archivos, o True/False si check_len está activado.

    Note:
        - Si delete_all es False, se asume que los archivos menores a min_file_size no tienen
          información útil y son eliminados.
        - La función imprime mensajes indicando qué archivos han sido eliminados.

    Example:
        >>> clean_txt_folder(delete_all=True)
        Archivo ffmm_20230101 borrado
        Archivo ffmm_20230102 borrado
        >>> clean_txt_folder(check_len=True)
        False
    """
    folder_path = Path(folder)

    for file in folder_path.glob(wildcard):
        if file.stat().st_size < min_file_size or delete_all:
            file.unlink()
            if delete_all:
                print(f"Archivo {file.stem} borrado")
            else:
                print(
                    f"Archivo {file.stem} borrado porque es menor a {min_file_size / 1000:.2f} KB"
                )

    return None


if __name__ == "__main__":
    # Genera un nombre de archivo hash de 10 caracteres
    file_name = generate_hash_name() + ".png"

    print(file_name)
    print(generate_hash_image_name())
    clean_txt_folder()
    print(CARTOLAS_FOLDER)
    for archivo in CARTOLAS_FOLDER.glob(WILDCARD_CARTOLAS_TXT):
        print(archivo.stat().st_size)