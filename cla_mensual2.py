"""
Script para generar el reporte mensual de análisis CLA con categorías personalizadas.

Este script es una variante de cla_mensual.py que permite comparar el fondo RUN 9810
(SoyFocus Conservador) con una categoría diferente a la asignada en el JSON de Elmer.

Diferencias con cla_mensual.py:
- El fondo RUN 9810 está en categoría 12 (BALANCEADO CONSERVADOR) según Elmer
- Este script lo compara con fondos de categoría 17
- NO modifica el JSON original de Elmer
- Usa un mapping personalizado de categorías

El reporte se guarda en un archivo Excel con la fecha del último día del mes anterior.
"""

from comparador.cla_monthly import generate_cla_data
from cartolas.update_by_year import update_parquet_by_year
from eco.bcentral import update_bcch_parquet
from datetime import date
from utiles.fechas import ultimo_dia_mes_anterior
from pathlib import Path

# Fecha del reporte: último día del mes anterior
REPORT_DATE = ultimo_dia_mes_anterior(date.today())

# Configuración de rutas y nombres de archivos
CLA_FOLDER = Path("cla_mensual2")  # Carpeta diferente para no sobrescribir el reporte original
CLA_EXCEL = CLA_FOLDER / f"cla2_{REPORT_DATE.strftime('%Y%m%d')}.xlsx"

# MAPPING PERSONALIZADO DE CATEGORÍAS
# Este mapping sobrescribe la asignación de categorías del JSON de Elmer
# para el fondo 9810, comparándolo con la categoría 17 en lugar de la 12
CUSTOM_CATEGORY_MAPPING = {
    9810: 17,  # SoyFocus Conservador: de categoría 12 a categoría 17
    # Aquí puedes agregar más fondos si necesitas cambiar sus categorías
    # Ejemplo:
    # 9809: 15,  # SoyFocus Moderado: cambiar a otra categoría
    # 9811: 18,  # SoyFocus Arriesgado: cambiar a otra categoría
}

def main():
    """
    Función principal que ejecuta el proceso completo de generación del reporte CLA
    con categorías personalizadas.

    El proceso incluye:
    1. Actualización de datos históricos de fondos mutuos
    2. Actualización de datos del Banco Central
    3. Generación del reporte CLA con mapping personalizado de categorías

    El reporte se guarda en un archivo Excel con la fecha del último día del mes anterior.
    """
    CLA_FOLDER.mkdir(exist_ok=True)
    print(f"📄 Generando reporte personalizado en: {CLA_EXCEL}")
    print(f"🔄 Mapping personalizado:")
    for run, categoria in CUSTOM_CATEGORY_MAPPING.items():
        print(f"   - RUN {run} → Categoría {categoria}")

    # Paso 1: Actualizar datos históricos de fondos mutuos
    print("\n📥 Paso 1/3: Actualizando datos de fondos mutuos...")
    update_parquet_by_year()

    # Paso 2: Actualizar datos del Banco Central
    print("📥 Paso 2/3: Actualizando datos del Banco Central...")
    update_bcch_parquet()

    # Paso 3: Generar reporte CLA mensual con categorías personalizadas
    print("📊 Paso 3/3: Generando reporte CLA con categorías personalizadas...")

    generate_cla_data(
        custom_mapping=CUSTOM_CATEGORY_MAPPING,
        save_xlsx=True,
        xlsx_name=str(CLA_EXCEL),
    )

    print(f"\n✅ Reporte generado exitosamente: {CLA_EXCEL}")
    print(f"✅ Mapeo personalizado aplicado correctamente:")
    for run, categoria in CUSTOM_CATEGORY_MAPPING.items():
        print(f"   - RUN {run} comparado con fondos de categoría {categoria}")


if __name__ == "__main__":
    main()
