"""
Script para generar el reporte mensual de análisis CLA (Comparación de Rentabilidades).

Este script automatiza el proceso de generación del reporte mensual de análisis CLA, que incluye:
1. Actualización de datos históricos de fondos mutuos
2. Actualización de datos del Banco Central
3. Generación del reporte CLA con comparativas de rentabilidad

El reporte se guarda en un archivo Excel con la fecha del último día del mes anterior.
"""

import logging
from comparador.cla_monthly import generate_cla_data
from cartolas.update_by_year import update_parquet_by_year
from eco.bcentral import update_bcch_parquet
from datetime import date
from utiles.fechas import ultimo_dia_mes_anterior
from pathlib import Path
from utiles.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Fecha del reporte: último día del mes anterior
REPORT_DATE = ultimo_dia_mes_anterior(date.today())

# Configuración de rutas y nombres de archivos
CLA_FOLDER = "cla_mensual"  # Carpeta donde se guardarán los reportes
CLA_EXCEL = Path(CLA_FOLDER) / f"cla_{REPORT_DATE.strftime('%Y%m%d')}.xlsx"  # Nombre del archivo Excel


def main():
    """
    Función principal que ejecuta el proceso completo de generación del reporte CLA.
    
    El proceso incluye:
    1. Actualización de datos históricos de fondos mutuos
    2. Actualización de datos del Banco Central
    3. Generación del reporte CLA con comparativas de rentabilidad
    
    El reporte se guarda en un archivo Excel con la fecha del último día del mes anterior.
    """
    logger.info(f"Reporte CLA: {CLA_EXCEL}")

    # Paso 1: Actualizar datos históricos de fondos mutuos
    logger.info("Actualizando parquet por año")
    update_parquet_by_year()

    # Paso 2: Actualizar datos del Banco Central
    logger.info("Actualizando bcch parquet")
    update_bcch_parquet()

    # Paso 3: Generar reporte CLA mensual
    logger.info("Generando cla mensual")
    generate_cla_data(
        save_xlsx=True,
        xlsx_name=CLA_EXCEL,
    )


if __name__ == "__main__":
    setup_logging()
    main()
