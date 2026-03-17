"""Esto son modulos para bajar una cartola de la CMF"""

from datetime import date, datetime
from cartolas.captcha import predict
from playwright.sync_api import Page, sync_playwright
from pathlib import PurePosixPath
from utiles.decorators import retry_function
from utiles.file_tools import clean_txt_folder, MIN_FILE_SIZE
from utiles.fechas import format_date_cmf, consecutive_date_ranges, date_range
from typing import Any
from pathlib import Path
from utiles.file_tools import generate_hash_image_name
from .config import (
    DEFAULT_HEADLESS,
    URL_CARTOLAS,
    TIMEOUT,
    DOWNLOAD_TIMEOUT,
    TEMP_FOLDER,
    ERROR_FOLDER,
    CORRECT_FOLDER,
    CARTOLAS_FOLDER,
)
from time import sleep
import logging
import time

logger = logging.getLogger(__name__)


@retry_function
def goto_with_retry(page: Page, url_str: str, timeout: int = TIMEOUT) -> Any:
    return page.goto(url_str, timeout=timeout)


def get_cartola_from_cmf(
    start_date: date | datetime,
    end_date: date | datetime,
    headless: bool = DEFAULT_HEADLESS,
    url: str = URL_CARTOLAS,
    temp_file_path: Path = None,
    error_folder: Path = ERROR_FOLDER,
    correct_folder: Path = CORRECT_FOLDER,
    cartolas_txt_folder: Path = CARTOLAS_FOLDER,
    max_retries: int = 5,
):
    """Descarga cartolas desde la CMF en unas fechas determinadas"""

    for folder in (error_folder, correct_folder, cartolas_txt_folder):
        folder.mkdir(parents=True, exist_ok=True)

    if temp_file_path is None:
        TEMP_FOLDER.mkdir(parents=True, exist_ok=True)
        temp_file_path = TEMP_FOLDER / generate_hash_image_name()

    start_date, end_date = map(format_date_cmf, [start_date, end_date])

    for attempt in range(1, max_retries + 1):
        try:
            _do_cartola_download(
                start_date, end_date, headless, url,
                temp_file_path, error_folder, correct_folder,
                cartolas_txt_folder,
            )
            return
        except Exception as e:
            logger.warning(
                "Descarga %s→%s: intento %d/%d falló: %s",
                start_date, end_date, attempt, max_retries, e,
            )
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    raise RuntimeError(
        f"Descarga {start_date}→{end_date} falló tras {max_retries} intentos"
    )


def _do_cartola_download(
    start_date, end_date, headless, url,
    temp_file_path, error_folder, correct_folder,
    cartolas_txt_folder,
):
    """Ejecuta un intento de descarga de cartola desde la CMF."""

    logger.info("Descargando cartolas desde %s hasta %s", start_date, end_date)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()

        goto_with_retry(page, url)

        captcha_img = page.query_selector("img#captcha_img")
        src = captcha_img.get_attribute("src")
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

        logger.info("Predicción del captcha: %s", prediction)

        if len(prediction) != 6:
            temp_file_path.rename(error_folder / f"{prediction}.png")
            raise ValueError("El captcha no tiene 6 caracteres")

        # Llenamos el formulario (evaluate para evitar eventos de datepicker)
        page.locator("#txt_inicio").evaluate("(el, val) => el.value = val", start_date)
        page.locator("#txt_termino").evaluate("(el, val) => el.value = val", end_date)
        page.get_by_label("Ingrese los caracteres de la").fill(prediction)

        fetch_cartola_data(
            temp_file_path,
            error_folder,
            correct_folder,
            cartolas_txt_folder,
            page,
            prediction,
        )


def fetch_cartola_data(
    temp_file_path,
    error_folder,
    correct_folder,
    cartolas_txt_folder,
    page,
    prediction,
):
    """Es la función que hace la baja de la cartola"""
    try:
        with page.expect_download(timeout=DOWNLOAD_TIMEOUT) as download_info:
            page.get_by_role("button", name="GENERAR ARCHIVO").click(timeout=TIMEOUT)
            download = download_info.value
            if download:
                safe_filename = PurePosixPath(download.suggested_filename).name
                download_path = cartolas_txt_folder / safe_filename
                download.save_as(download_path)
                file_size = download_path.stat().st_size
                if file_size < MIN_FILE_SIZE:
                    logger.warning(
                        "Archivo %s muy pequeño (%d bytes), descartando",
                        download_path.name, file_size,
                    )
                    download_path.unlink()
                    raise ValueError(
                        f"Archivo descargado vacío o muy pequeño ({file_size} bytes)"
                    )
                temp_file_path.rename(correct_folder / f"{prediction}.png")
                logger.info("Descargado: %s (%d bytes)", download_path.name, file_size)
    except Exception as e:
        logger.warning("Error en la descarga: %s", e)
        if temp_file_path.exists():
            temp_file_path.rename(error_folder / f"{prediction}.png")
        raise


def download_cartolas_range(input_date_range: list[date], sleep_time: int = 1):
    """Esta es una función que hace todo el proceso de bajada, incluyendo calcular los rangos de fechas
    con las restricciones de la CMF (30 días máximo), también elimina las cartolas que no tienen información
    """
    # Establezco conjunto de rango de fechas
    date_range_set = consecutive_date_ranges(input_date_range)
    # Número de subconjuntos de rangos de fechas
    num_range_set = len(date_range_set)

    for i, (start_date, end_date) in enumerate(date_range_set):
        logger.info("Descargando rango %d de %d: %s → %s", i + 1, num_range_set, start_date, end_date)
        get_cartola_from_cmf(start_date, end_date)
        sleep(sleep_time)

    # Limpia archivos txt que son más chicos que el mínimo definido en kb
    clean_txt_folder()


def main():
    """ESTO ES TEMPORAL, ES EL MAIN"""
    start_date = date(2021, 1, 1)
    end_date = date(2021, 2, 22)
    rango = date_range(start_date, end_date)
    download_cartolas_range(rango)


if __name__ == "__main__":
    main()
