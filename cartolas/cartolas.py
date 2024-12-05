from datetime import date
from pathlib import Path

from config import DEFAULT_HEADLESS, URL_CARTOLAS

def download_cartola(
        start_date: date,
        end_date : date,
        headless : bool = DEFAULT_HEADLESS,
        url: str = URL_CARTOLAS

):
    """ Este baja la cartola de un día en específico"""
    pass