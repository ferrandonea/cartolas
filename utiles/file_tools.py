"""Utilidades de manejo de archivos"""

import hashlib
import random
import string

HASH_LENGHT = 12


def generate_hash_name(length=HASH_LENGHT):
    # Genera una cadena aleatoria
    random_string = "".join(
        random.choices(string.ascii_letters + string.digits, k=length)
    )
    # Crea un hash de la cadena aleatoria
    hash_object = hashlib.sha256(random_string.encode())
    # Devuelve los primeros 'length' caracteres del hash
    return hash_object.hexdigest()[:length]


def generate_hash_image_name(lenght=HASH_LENGHT):
    return generate_hash_name(length=lenght) + ".png"




if __name__ == "__main__":
    # Genera un nombre de archivo hash de 10 caracteres
    file_name = generate_hash_name() + ".png"

    print(file_name)
    print(generate_hash_image_name())
