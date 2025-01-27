"""Esto son modulos para bajar una cartola de la CMF"""

from datetime import date, datetime, timedelta
from captchapass import predict
from playwright.sync_api import Page, sync_playwright
from utiles.decorators import retry_function, exp_retry_function
from utiles.file_tools import generate_hash_image_name
from utiles.fechas import format_date_cmf
from typing import Any
from pathlib import Path

DEFAULT_HEADLESS = True
URL_CARTOLAS = (
    "https://www.cmfchile.cl/institucional/estadisticas/fondos_cartola_diaria.php"
)
VERBOSE = True
TIMEOUT = 500_000

# Carpeta de este módulo
CURRENT_FOLDER = Path(__file__).parent

# Este es la carpeta donde se guardan los archivos temporales
TEMP_FOLDER_NAME = "temp"
TEMP_FOLDER = CURRENT_FOLDER / TEMP_FOLDER_NAME
TEMP_FILE_NAME = generate_hash_image_name()
TEMP_FILE_PWD = TEMP_FOLDER / TEMP_FILE_NAME

# Carpeta donde se guardan los errores
ERROR_FOLDER_NAME = "errors"
ERROR_FOLDER = CURRENT_FOLDER / ERROR_FOLDER_NAME

# Carpeta donde se guardan los correctosuv r
CORRECT_FOLDER_NAME = "correct"
CORRECT_FOLDER = CURRENT_FOLDER / CORRECT_FOLDER_NAME

# Carpeta donde se guardan los txt de las cartolas
CARTOLAS_FOLDER_NAME = "cartolas_txt"
CARTOLAS_FOLDER = CURRENT_FOLDER / CARTOLAS_FOLDER_NAME

@retry_function
def goto_with_retry(page: Page, url_str: str, timeout: int = TIMEOUT) -> Any:
    return page.goto(url_str, timeout=timeout)


@exp_retry_function
@retry_function
def download_cartolas(
    start_date: date | datetime,
    end_date: date | datetime,
    headless: bool = DEFAULT_HEADLESS,
    url: str = URL_CARTOLAS,
    verbose: bool = VERBOSE,
    temp_file_path: Path = TEMP_FILE_PWD,
    error_folder: Path = ERROR_FOLDER,
    correct_folder: Path = CORRECT_FOLDER,
    cartolas_txt_folder: Path = CARTOLAS_FOLDER,
):
    """Descarga cartolas desde la CMF en unas fechas determinadas"""

    # Aplica la función de formato a las fechas de inicio y fin
    start_date, end_date = map(format_date_cmf, [start_date, end_date])

    print(
        f"Descargando cartolas desde {start_date} hasta {end_date}"
    ) if verbose else None

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        
        # Alternativamente page.goto(url, timeout=TIMEOUT)
        goto_with_retry(page, url)
        
        captcha_img = page.query_selector("img#captcha_img")
        src = captcha_img.get_attribute("src")
        # Acá usamos JS para obtener una representación de la imagen en bytes
        image_data = page.evaluate(
            """async (url) => {
            const response = await fetch(url);
            const buffer = await response.arrayBuffer();
            return Array.from(new Uint8Array(buffer));
        }""",
            src,
        )
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(bytearray(image_data))

        prediction = predict(temp_file_path)

        print(f"Predicción del captcha: {prediction}") if verbose else None

        if len(prediction) != 6:
            temp_file_path.rename(error_folder / f"{prediction}.png")
            raise ValueError("El captcha no tiene 6 caracteres")

        # Llenamos el formulario
        page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
        page.evaluate(f"document.querySelector('#txt_termino').value = '{end_date}';")
        page.get_by_label("Ingrese los caracteres de la").fill(prediction)

        fetch_cartola_data(
            verbose,
            temp_file_path,
            error_folder,
            correct_folder,
            cartolas_txt_folder,
            page,
            prediction,
        )


def fetch_cartola_data(
    verbose,
    temp_file_path,
    error_folder,
    correct_folder,
    cartolas_txt_folder,
    page,
    prediction,
):
    """Es la función que hace la baja de la cartola"""
    try:
        with page.expect_download() as download_info:
            page.get_by_role("button", name="GENERAR ARCHIVO").click(timeout=TIMEOUT)
            download = download_info.value
            if download:
                temp_file_path.rename(correct_folder / f"{prediction}.png")
                download_path = cartolas_txt_folder / download.suggested_filename
                download.save_as(download_path)
                print(f"Archivo descargado como: {download_path}") if verbose else None
                # ACA FALTA CHEQUEAR EL TAMAÑO
    except Exception as e:
        print("Error en la descarga") if verbose else None
        print(f"Detalles: {e}") if verbose else None
        temp_file_path.rename(error_folder / f"{prediction}.png")
        raise e


def main(VERBOSE, download_cartolas):
    """ESTO ES TEMPORAL, ES EL MAIN"""
    start_date = date(2021, 1, 1)
    end_date = date(2021, 1, 22)
    import time
    from random import randint

    start = time.perf_counter()
    corridas = 1
    for _ in range(corridas):
        sleep = randint(1, 10)
        print("*" * 80) if VERBOSE else None
        print(f"Iteración {_}") if VERBOSE else None
        download_cartolas(start_date, end_date, headless=True)
        print(f"Esperando {sleep} segundos") if VERBOSE else None
        time.sleep(sleep)
    print(f"Tiempo total: {time.perf_counter() - start:.2f}") if VERBOSE else None


if __name__ == "__main__":
    main(VERBOSE, download_cartolas)

