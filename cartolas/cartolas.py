import time
from datetime import date
from typing import Callable, TypeVar
from pathlib import Path
from captchapass import predict
from config import DEFAULT_HEADLESS, URL_CARTOLAS
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PWTimeOut

class FolderPaths:
    TEMP = Path("/path/to/temp")
    CORRECT = Path("/path/to/correct")
    WRONG = Path("/path/to/wrong")
    DOWNLOAD = Path("/path/to/download")
    
# Constante para el formato de fechas
DATE_FORMAT = "%d/%m/%Y"
T = TypeVar("T")


def retry_function(
    func: Callable[..., T], max_attempts: int = 5, delay: int = 10
) -> Callable[..., T]:
    """
    Decorador que intenta ejecutar una función varias veces en caso de excepción.

    Este decorador envuelve la función objetivo y la reintenta un número especificado
    de veces si ocurre una excepción, con un retraso entre cada intento.

    Args:
        func (Callable[..., T]): La función a ser decorada.
        max_attempts (int): Número máximo de intentos antes de propagar la excepción.
                            Por defecto es 5.
        delay (int): Tiempo de espera en segundos entre intentos. Por defecto es 10.

    Returns:
        Callable[..., T]: La función envuelta que incluye la lógica de reintento.

    Raises:
        Exception: Propaga la última excepción si se agotan todos los intentos.

    Ejemplo:
        >>> @retry_function(max_attempts=3, delay=2)
        ... def unstable_function():
        ...     import random
        ...     if random.random() < 0.7:
        ...         raise ValueError("Operación fallida")
        ...     return "Éxito"
        ...
        >>> result = unstable_function()
        Attempt 1 failed: Operación fallida
        Waiting 2 seconds
        Attempt 2 failed: Operación fallida
        Waiting 2 seconds
        >>> print(result)
        Éxito
    """

    def wrapper(*args: Any, **kwargs: Any) -> T:
        """
        Función envoltorio que ejecuta la función decorada con lógica de reintento.

        Args:
            *args: Argumentos posicionales para la función decorada.
            **kwargs: Argumentos de palabra clave para la función decorada.

        Returns:
            T: El resultado de la función decorada.

        Raises:
            Exception: La última excepción capturada si se agotan todos los intentos.
        """
        attempts = 0
        while attempts < max_attempts:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                print(f"Intento {attempts} fallido: {str(e)}")
                if attempts < max_attempts:
                    print(f"Esperando {delay} segundos")
                    time.sleep(delay)
                else:
                    print(
                        f"Se alcanzó el máximo de intentos ({max_attempts}). Propagando la excepción."
                    )
                    raise

    return wrapper


@retry_function
def goto_with_retry(page: Page, url: str, timeout: int = TIMEOUT) -> Any:
    """
    Navega a una URL específica con un mecanismo de reintento.

    Esta función intenta navegar a la URL proporcionada utilizando el método goto de Playwright.
    Si falla, el decorador retry_function intentará la operación nuevamente.

    Args:
        page (Page): Objeto Page de Playwright en el que se realizará la navegación.
        url (str): La URL a la que se desea navegar.
        timeout (int): Tiempo máximo de espera en milisegundos para la navegación.
                       Por defecto es 500,000 ms (500 segundos).

    Returns:
        Any: El resultado de la operación de navegación de Playwright.

    Raises:
        Exception: Si la navegación falla después de todos los intentos definidos en retry_function.

    Nota:
        Esta función está decorada con @retry_function, lo que significa que se reintentará
        automáticamente en caso de fallo según la configuración del decorador.

    Ejemplo:
        >>> from playwright.sync_api import sync_playwright
        >>> with sync_playwright() as p:
        ...     browser = p.chromium.launch()
        ...     page = browser.new_page()
        ...     response = goto_with_retry(page, "https://www.ejemplo.com")
        ...     print(response.status)
        ...     browser.close()
        200
    """
    return page.goto(url, timeout=timeout)


def validate_and_format_dates(
    start_date: date, end_date: date, verbose: bool = False
) -> tuple[str, str]:
    """
    Valida y formatea las fechas para el rango de búsqueda.

    Args:
        start_date (date): Fecha inicial.
        end_date (date): Fecha final.
        verbose (bool): Si es True, imprime información adicional.

    Returns:
        tuple[str, str]: Fechas formateadas como cadenas.
    """
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValueError(
            "start_date y end_date deben ser objetos de tipo datetime.date"
        )

    if start_date > end_date:
        start_date, end_date = end_date, start_date
        if verbose:
            print("INFO: Las fechas se intercambiaron porque estaban en orden inverso.")

    return start_date.strftime(DATE_FORMAT), end_date.strftime(DATE_FORMAT)


def verbose_print(message: str, verbose: bool) -> None:
    """
    Imprime un mensaje si verbose es True.

    Args:
        message (str): Mensaje a imprimir.
        verbose (bool): Si es True, imprime el mensaje.
    """
    if verbose:
        print(message)


def download_cartola(
    start_date: date,
    end_date: date,
    headless: bool = DEFAULT_HEADLESS,
    url: str = URL_CARTOLAS,
    verbose: bool = False,
):
    """
    Descarga la cartola para un rango de fechas especificado.

    Args:
        start_date (date): Fecha inicial del rango.
        end_date (date): Fecha final del rango.
        headless (bool): Indica si el navegador debe ejecutarse en modo sin interfaz gráfica.
        url (str): URL base de la página para descargar cartolas.
        verbose (bool): Si es True, imprime información adicional durante la ejecución.

    Returns:
        None: Aún no implementa la descarga, solo muestra información básica.
    """
    # Validar y formatear fechas
    formatted_start_date, formatted_end_date = validate_and_format_dates(
        start_date, end_date, verbose
    )

    # Mostrar información si verbose está habilitado
    verbose_print("*" * 40, verbose)
    verbose_print(
        f"Rango de fechas: [{formatted_start_date} - {formatted_end_date}]", verbose
    )

    # Debugging opcional
    verbose_print(f"{formatted_start_date = } {formatted_end_date = }", verbose)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()

        try:
            goto_with_retry(page, url)
            captcha_img = page.query_selector("img#captcha_img")

            if not captcha_img:
                raise ValueError("No se pudo encontrar la imagen del CAPTCHA")

            src = captcha_img.get_attribute("src")

            if verbose:
                print(f"Imagen en: {src:<30}")

            image_data = page.evaluate(
                """async (url) => {
                const response = await fetch(url);
                const buffer = await response.arrayBuffer();
                return Array.from(new Uint8Array(buffer));
            }""",
                src,
            )

            temp_file_name = "temp_image.png"
            temp_file_path = folder["TEMP"] / temp_file_name

            if verbose:
                print(f"Archivo temporal: {str(temp_file_path):<30}")

            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(bytearray(image_data))

            prediction = predict(temp_file_path)

            print(f"Predicción: {prediction}")

            if len(prediction) != 6:
                temp_file_path.rename(folder["WRONG"] / f"{prediction}.png")
                print("Error en predicción, largo distinto de 6")
                return

            # Llenar formulario
            page.evaluate(
                f"document.querySelector('#txt_inicio').value = '{formatted_start_date}';"
            )
            page.evaluate(
                f"document.querySelector('#txt_termino').value = '{formatted_end_date}';"
            )
            page.get_by_label("Ingrese los caracteres de la").fill(prediction)

            try:
                with page.expect_download() as download_info:
                    page.get_by_role("button", name="GENERAR ARCHIVO").click()
                    download = download_info.value
                    if download:
                        temp_file_path.rename(folder["CORRECT"] / f"{prediction}.png")
                        download_path = folder["DOWNLOAD"] / download.suggested_filename
                        download.save_as(download_path)
                        check_file_size(download_path)
            except PWTimeOut:
                print("ERROR: Tiempo de espera agotado al intentar descargar")
                temp_file_path.rename(folder["WRONG"] / f"{prediction}.png")
            except Exception as e:
                print(f"Error inesperado: {e}")
                temp_file_path.rename(folder["WRONG"] / f"{prediction}.png")

        finally:
            browser.close()
