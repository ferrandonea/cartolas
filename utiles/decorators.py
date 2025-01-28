"""Decoradores"""

from typing import Callable, TypeVar
import time
from functools import wraps
from typing import Any

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
                print(
                    f"Intento {attempts}/{max_attempts}. Esperando {pow(2, attempts)} segundos"
                )
                time.sleep(pow(2, attempts))
        raise Exception(
            f"No se pudo ejecutar {func.__name__} después de {max_attempts} intentos"
        )

    return wrapper


def timer(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorador que mide y muestra el tiempo de ejecución de una función.

    Este decorador envuelve la función objetivo, registra el tiempo antes y después
    de su ejecución, y muestra el tiempo transcurrido en segundos.

    Args:
        func (Callable[..., Any]): La función a ser decorada.

    Returns:
        Callable[..., Any]: La función envuelta que incluye la medición del tiempo.

    Ejemplo:
        >>> @timer
        ... def example_function(n: int) -> int:
        ...     return sum(range(n))
        ...
        >>> result = example_function(1000000)
        Función example_function ejecutada en 0.0521 segundos
        >>> print(result)
        499999500000
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """
        Función envoltorio que ejecuta la función decorada y mide su tiempo de ejecución.

        Args:
            *args: Argumentos posicionales para la función decorada.
            **kwargs: Argumentos de palabra clave para la función decorada.

        Returns:
            Any: El resultado de la función decorada.
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"\nFunción {func.__name__} ejecutada en {execution_time:.4f} segundos")
        return result

    return wrapper
