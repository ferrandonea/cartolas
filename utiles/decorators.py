""" Decoradores """
from typing import Callable, TypeVar
import time

# Tipo de dato genérico
T = TypeVar("T")


def retry_function(
    func: Callable[..., T], max_attempts: int = 10, delay: int = 10
) -> Callable[..., T]:
    """Decorador que intenta ejecutar una función varias veces si hay una excepción"""

    def wrapper(*args, **kwargs) -> T:
        attempts = 0
        while attempts < max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                print(f"Error en {func.__name__}: {e}")
                print(f"Intento {attempts}/{max_attempts}. Esperando {delay} segundos")
                time.sleep(delay)
        raise Exception(
            f"No se pudo ejecutar {func.__name__} después de {max_attempts} intentos"
        )

    return wrapper

def exp_retry_function(
    func: Callable[..., T], max_attempts: int = 12
) -> Callable[..., T]:
    """Decorador que intenta ejecutar una función varias veces si hay una excepción
    con un crecimiento exponencial en el delay"""

    def wrapper(*args, **kwargs) -> T:
        attempts = 0
        while attempts < max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                print(f"Error en {func.__name__}: {e}")
                print(f"Intento {attempts}/{max_attempts}. Esperando {pow(2, attempts)} segundos")
                time.sleep(pow(2, attempts))
        raise Exception(
            f"No se pudo ejecutar {func.__name__} después de {max_attempts} intentos"
        )

    return wrapper
