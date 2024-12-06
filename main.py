from cartolas.cartolas import download_cartola
from datetime import date

fecha_inicio = date(2024, 1, 1)
fecha_fin = date(2023, 1, 1)

download_cartola(fecha_inicio, fecha_fin, verbose=True)
