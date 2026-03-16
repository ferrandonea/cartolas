"""
Módulo para generar y analizar datos de rentabilidad de fondos mutuos.

Este módulo proporciona funciones para:
1. Calcular rentabilidades acumuladas y por período
2. Comparar fondos con sus pares de categoría
3. Generar estadísticas y rankings
4. Exportar resultados a Excel con formato visual

Las funciones principales incluyen:
- generate_cla_dates: Genera fechas para diferentes períodos de análisis
- add_cumulative_returns: Calcula rentabilidades acumuladas
- add_period_returns: Calcula rentabilidades por período
- add_soyfocus_returns: Agrega rentabilidades del fondo SoyFocus
- generate_cla_data: Función principal que orquesta todo el proceso
"""

from datetime import date
from typing import Literal

import polars as pl
import pandas as pd
import numpy as np

from comparador.merge import merge_cartolas_with_categories
from utiles.fechas import (
    date_n_months_ago,
    date_n_years_ago,
    ultimo_dia_año_anterior,
    ultimo_dia_mes_anterior,
)
from utiles.decorators import timer

# Constantes para los períodos de análisis
MESES_CLA = [1, 3, 6]  # Períodos mensuales a analizar (1, 3 y 6 meses)
AÑOS_CLA = [1, 3, 5]  # Períodos anuales a analizar (1, 3 y 5 años)
CATEGORIAS_CLA = ["CONSERVADOR", "MODERADO", "AGRESIVO"]  # Categorías base de fondos
# Genera las categorías completas agregando el prefijo "BALANCEADO"
CATEGORIAS_ELMER = [f"BALANCEADO {categoria}" for categoria in CATEGORIAS_CLA]

# Columnas relevantes para el análisis final
RELEVANT_COLUMNS = [
    "RUN_FM",  # Identificador único del fondo
    "SERIE",  # Serie del fondo
    "FECHA_INF",  # Fecha de la información
    "CATEGORIA",  # Categoría del fondo
    "RENTABILIDAD_ACUMULADA",  # Rentabilidad acumulada desde el inicio
    "RUN_SOYFOCUS",  # Identificador del fondo SoyFocus correspondiente
    "SERIE_SOYFOCUS",  # Serie del fondo SoyFocus correspondiente
]

# Nombres de las hojas para el archivo Excel
EXCEL_SHEETS = {
    "datos_base": "1 Base",  # Datos base sin procesar
    "rentabilidades": "2 Acumuladas",  # Rentabilidades acumuladas
    "categorias": "3 Categoría",  # Datos filtrados por categoría
    "columnas": "4 Seleccionadas",  # Columnas seleccionadas
    "fechas": "5 Fecha",  # Datos filtrados por fechas relevantes
    "rentabilidad_periodo": "6 Rentabilidad Período",  # Rentabilidades por período
    "final": "7 SoyFocus",  # Datos finales con comparación SoyFocus
    "estadisticas": "8 Estadísticas",  # Estadísticas resumidas
}

# Opciones para guardar pasos intermedios en Excel
EXCEL_STEPS = Literal["all", "minimal", "none"]


@timer
def generate_cla_dates(input_date: date = date.today()) -> dict[int, date]:
    """
    Genera un diccionario con las fechas relevantes para el análisis CLA.

    Esta función calcula las fechas para diferentes períodos de análisis:
    - Fechas para períodos mensuales (1, 3, 6 meses)
    - Fechas para períodos anuales (1, 3, 5 años)
    - Fecha del último día del año anterior
    - Fecha actual del reporte

    Args:
        input_date (date): Fecha base para realizar los cálculos. Por defecto usa la fecha actual.

    Returns:
        dict[int, date]: Diccionario donde:
            - Las claves son los períodos en meses (ej: 1, 3, 6, 12, 36, 60)
            - -1 representa el último día del año anterior
            - 0 representa la fecha actual del reporte
            - Los valores son las fechas correspondientes
    """
    # Obtener el último día del mes anterior como fecha base del reporte
    current_report_date = ultimo_dia_mes_anterior(input_date)
    print(f"{current_report_date = }")

    # Construir el diccionario de fechas combinando:
    cla_dates = {
        # Fechas para períodos mensuales (1, 3, 6 meses)
        **{mes: date_n_months_ago(mes, current_report_date) for mes in MESES_CLA},
        # Fechas para períodos anuales (convertidos a meses: 12, 36, 60)
        **{año * 12: date_n_years_ago(año, current_report_date) for año in AÑOS_CLA},
        # Fechas especiales
        -1: ultimo_dia_año_anterior(current_report_date),  # Último día del año anterior
        0: current_report_date,  # Fecha actual del reporte
    }

    return cla_dates

@timer
def add_cumulative_returns(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calcula las rentabilidades acumuladas para cada fondo y serie.

    Esta función procesa el DataFrame para calcular la rentabilidad acumulada
    utilizando el producto acumulativo de las rentabilidades diarias.

    Args:
        df (pl.DataFrame): DataFrame con las rentabilidades diarias por fondo y serie

    Returns:
        pl.DataFrame: DataFrame original con una nueva columna 'RENTABILIDAD_ACUMULADA'
            que contiene el producto acumulativo de las rentabilidades diarias
    """
    # Ordenar el DataFrame para asegurar el cálculo correcto de acumulados
    sorted_df = df.sort(["RUN_FM", "SERIE", "FECHA_INF"])

    # Calcular la rentabilidad acumulada por fondo y serie
    return sorted_df.with_columns(
        [
            pl.col("RENTABILIDAD_DIARIA_PESOS")
            .cum_prod()  # Producto acumulativo de rentabilidades diarias
            .over(["RUN_FM", "SERIE"])  # Agrupado por fondo y serie
            .fill_nan(1)  # Reemplazar NaN por 1 (rentabilidad neutral)
            .fill_null(1)  # Reemplazar valores nulos por 1
            .alias("RENTABILIDAD_ACUMULADA")
        ]
    )

if __name__ == "__main__":
    fechas_cla = generate_cla_dates()
    print (f"{fechas_cla = }")
    fecha_a_periodo = {v: k for k, v in fechas_cla.items()}
    print (f"{fecha_a_periodo = }")
