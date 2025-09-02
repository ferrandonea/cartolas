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
CATEGORIAS_ELMER[0] = "DEUDA CORTO PLAZO NACIONAL"

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


@timer
def add_soyfocus_returns(df: pl.DataFrame) -> pl.DataFrame:
    """
    Agrega la rentabilidad acumulada y del período del fondo SoyFocus correspondiente.

    Esta función realiza un join entre el DataFrame original y una selección de datos
    para obtener la rentabilidad acumulada y del período del fondo SoyFocus asociado a cada registro.

    Args:
        df (pl.DataFrame): DataFrame con los datos de rentabilidad de los fondos

    Returns:
        pl.DataFrame: DataFrame original con dos nuevas columnas:
            - 'RENTABILIDAD_AC_SOYFOCUS': rentabilidad acumulada del fondo SoyFocus
            - 'RENTABILIDAD_PERIODO_SOYFOCUS': rentabilidad del período del fondo SoyFocus
    """
    # Convertir RUN_SOYFOCUS a u16 para que coincida con el tipo de RUN_FM
    df = df.with_columns([pl.col("RUN_SOYFOCUS").cast(pl.UInt16)])

    # Hacemos el join para obtener la rentabilidad del fondo SoyFocus
    df_joined = df.join(
        df.select(
            [
                "RUN_FM",
                "SERIE",
                "FECHA_INF",
                "RENTABILIDAD_ACUMULADA",
                "RENTABILIDAD_PERIODO",
            ]
        ),
        left_on=["RUN_SOYFOCUS", "SERIE_SOYFOCUS", "FECHA_INF"],
        right_on=["RUN_FM", "SERIE", "FECHA_INF"],
        how="left",
    ).rename(
        {
            "RENTABILIDAD_ACUMULADA_right": "RENTABILIDAD_AC_SOYFOCUS",
            "RENTABILIDAD_PERIODO_right": "RENTABILIDAD_PERIODO_SOYFOCUS",
        }
    )

    # Calcular la rentabilidad relativa del período de SoyFocus
    return df_joined.with_columns(
        [
            (
                pl.col("RENTABILIDAD_PERIODO_SOYFOCUS") / pl.col("RENTABILIDAD_PERIODO")
            ).alias("RENTABILIDAD_PERIODO_SOYFOCUS_REL")
        ]
    )


@timer
def add_period_returns(df: pl.DataFrame, cla_dates: dict[int, date]) -> pl.DataFrame:
    """
    Calcula la rentabilidad del período dividiendo la rentabilidad acumulada de la fecha más reciente
    por la rentabilidad acumulada de cada fecha.

    Args:
        df (pl.DataFrame): DataFrame con las rentabilidades acumuladas
        cla_dates (dict[int, date]): Diccionario con las fechas relevantes

    Returns:
        pl.DataFrame: DataFrame con una nueva columna 'RENTABILIDAD_PERIODO'
    """
    # Obtener la fecha más reciente (clave 0 en cla_dates)
    fecha_reciente = cla_dates[0]

    # Crear un DataFrame con las rentabilidades de la fecha más reciente
    df_reciente = (
        df.filter(pl.col("FECHA_INF") == fecha_reciente)
        .select(["RUN_FM", "SERIE", "RENTABILIDAD_ACUMULADA"])
        .rename({"RENTABILIDAD_ACUMULADA": "RENTABILIDAD_ACUMULADA_RECIENTE"})
    )

    # Hacer join con el DataFrame original y calcular la rentabilidad del período
    return (
        df.join(df_reciente, on=["RUN_FM", "SERIE"], how="left")
        .with_columns(
            [
                (
                    pl.col("RENTABILIDAD_ACUMULADA_RECIENTE")
                    / pl.col("RENTABILIDAD_ACUMULADA")
                ).alias("RENTABILIDAD_PERIODO")
            ]
        )
        .drop("RENTABILIDAD_ACUMULADA_RECIENTE")
    )


@timer
def add_category_statistics(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """
    Calcula estadísticas por categoría y fecha:
    1. Número de series con datos
    2. Posición de la rentabilidad del período de SoyFocus (1 es la mejor)
    3. Rentabilidad promedio de las series
    4. Rentabilidad del período de SoyFocus

    Args:
        df (pl.DataFrame): DataFrame con los datos de rentabilidad

    Returns:
        tuple[pl.DataFrame, pl.DataFrame]: Tupla con:
            - DataFrame original con las estadísticas agregadas
            - DataFrame con las estadísticas resumidas por categoría y fecha
    """
    # Calcular estadísticas por categoría y fecha
    stats = df.group_by(["CATEGORIA", "FECHA_INF"]).agg(
        [
            pl.count("SERIE").alias("NUM_SERIES"),  # Número de series por categoría
            pl.mean("RENTABILIDAD_PERIODO").alias("RENTABILIDAD_PROMEDIO"),  # Rentabilidad promedio
        ]
    )

    # Calcular la posición y rentabilidad de SoyFocus para cada categoría y fecha
    soyfocus_stats = df.group_by(["CATEGORIA", "FECHA_INF"]).agg(
        [
            pl.col("RENTABILIDAD_PERIODO_SOYFOCUS_REL")
            .rank(
                method="min", descending=False
            )  # Cambiado a False para que 1 sea la mejor posición
            .filter(pl.col("RUN_FM") == pl.col("RUN_SOYFOCUS"))
            .first()
            .alias("POSICION_SOYFOCUS"),
            pl.col("RENTABILIDAD_PERIODO_SOYFOCUS")
            .filter(pl.col("RUN_FM") == pl.col("RUN_SOYFOCUS"))
            .first()
            .alias("RENTABILIDAD_PERIODO_SOYFOCUS"),
        ]
    )

    # Unir las estadísticas con el DataFrame original
    df_with_stats = df.join(stats, on=["CATEGORIA", "FECHA_INF"], how="left").join(
        soyfocus_stats, on=["CATEGORIA", "FECHA_INF"], how="left"
    )

    # Crear DataFrame resumen con todas las estadísticas
    df_stats = stats.join(
        soyfocus_stats, on=["CATEGORIA", "FECHA_INF"], how="left"
    ).sort(["CATEGORIA", "FECHA_INF"])

    return df_with_stats, df_stats


@timer
def generate_cla_data(
    input_date: date = date.today(),
    categories: list[str] = CATEGORIAS_ELMER,
    relevant_columns: list[str] = RELEVANT_COLUMNS,
    save_xlsx: bool = False,
    xlsx_name: str = "cla_data.xlsx",
    excel_steps: EXCEL_STEPS = "minimal",
) -> pl.DataFrame:
    """
    Genera el DataFrame con los datos necesarios para el análisis CLA.

    Esta función realiza el proceso completo de generación de datos para el análisis CLA:
    1. Obtiene los datos base y agrega categorías
    2. Calcula rentabilidades acumuladas
    3. Filtra por categorías relevantes
    4. Selecciona columnas específicas
    5. Filtra por fechas relevantes
    6. Calcula rentabilidades del período
    7. Agrega rentabilidades de SoyFocus
    8. Calcula estadísticas por categoría y fecha
    9. Crea una tabla resumen tipo pivot con los principales indicadores por categoría y período

    Args:
        input_date (date): Fecha base para el análisis. Por defecto usa la fecha actual.
        categories (list[str]): Lista de categorías a incluir en el análisis.
            Por defecto usa CATEGORIAS_ELMER.
        relevant_columns (list[str]): Lista de columnas a mantener en el resultado.
            Por defecto usa RELEVANT_COLUMNS.
        save_xlsx (bool): Si es True, guarda los pasos intermedios en un archivo Excel.
            Por defecto es False.
        xlsx_name (str): Nombre del archivo Excel donde se guardarán los datos.
            Por defecto es "cla_data.xlsx".
        excel_steps (Literal["all", "minimal", "none"]): Controla qué pasos se guardan en Excel:
            - "all": guarda todos los pasos intermedios
            - "minimal": guarda solo los pasos más relevantes (categorías, fechas, período y final)
            - "none": no guarda ningún paso intermedio
            Por defecto es "minimal".

    Returns:
        pl.DataFrame: DataFrame procesado con todos los datos necesarios para el análisis CLA
    """
    # Obtener las fechas relevantes para el análisis
    cla_dates = generate_cla_dates(input_date)
    # Invertir el diccionario para mapear fecha a nombre de período
    fecha_a_periodo = {v: k for k, v in cla_dates.items()}
    # Etiquetas para los períodos en el reporte
    periodo_labels = {
        1: "1M",  # 1 mes
        3: "3M",  # 3 meses
        6: "6M",  # 6 meses
        12: "1Y",  # 1 año
        36: "3Y",  # 3 años
        60: "5Y",  # 5 años
        -1: "YTD",  # Año hasta la fecha
        0: "YTD",  # Año hasta la fecha
    }

    # Diccionario para almacenar los DataFrames intermedios
    dfs_intermedios = {}

    # Paso 1: Obtener datos base y agregar categorías
    df_base: pl.LazyFrame = merge_cartolas_with_categories()
    if save_xlsx and excel_steps == "all":
        dfs_intermedios[EXCEL_SHEETS["datos_base"]] = df_base.collect()

    # Paso 2: Calcular rentabilidades acumuladas
    df_rent: pl.LazyFrame = add_cumulative_returns(df_base)
    if save_xlsx and excel_steps == "all":
        dfs_intermedios[EXCEL_SHEETS["rentabilidades"]] = df_rent.collect()

    # Paso 3: Filtrar por categorías relevantes
    df_cat: pl.LazyFrame = df_rent.filter(pl.col("CATEGORIA").is_in(categories))
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["categorias"]] = df_cat.collect()

    # Paso 4: Seleccionar columnas relevantes y convertir a DataFrame
    df_cols: pl.DataFrame = df_cat.collect().select(relevant_columns)
    if save_xlsx and excel_steps == "all":
        dfs_intermedios[EXCEL_SHEETS["columnas"]] = df_cols

    # Paso 5: Filtrar por fechas relevantes
    df_fechas: pl.DataFrame = df_cols.filter(
        pl.col("FECHA_INF").is_in(list(cla_dates.values()))
    )
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["fechas"]] = df_fechas

    # Paso 6: Calcular rentabilidades del período
    df_periodo: pl.DataFrame = add_period_returns(df_fechas, cla_dates)
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["rentabilidad_periodo"]] = df_periodo

    # Paso 7: Agregar rentabilidad de SoyFocus
    df_final: pl.DataFrame = add_soyfocus_returns(df_periodo)
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["final"]] = df_final

    # Paso 8: Calcular estadísticas por categoría y fecha
    df_with_stats, df_stats = add_category_statistics(df_final)
    # Agregar columna PERIODO a df_stats
    df_stats = df_stats.with_columns(
        [
            pl.col("FECHA_INF")
            .map_elements(
                lambda x: periodo_labels.get(fecha_a_periodo.get(x, None), str(x)),
                return_dtype=pl.Utf8,
            )
            .alias("PERIODO")
        ]
    )
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["estadisticas"]] = df_stats

    # Paso 9: Crear tabla resumen y agregarla al Excel
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios["9 Resumen"] = df_stats.to_pandas()

    # Guardar todos los DataFrames en el Excel si se solicitó
    if save_xlsx and dfs_intermedios:
        dfs_pandas = {}
        for sheet_name, df in dfs_intermedios.items():
            if isinstance(df, pl.DataFrame):
                dfs_pandas[sheet_name] = df.to_pandas()
            else:
                dfs_pandas[sheet_name] = df
        with pd.ExcelWriter(xlsx_name, engine="xlsxwriter") as writer:
            for sheet_name, df in dfs_pandas.items():
                df.to_excel(writer, sheet_name=sheet_name, index=True)
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(), len(str(col))
                    )
                    worksheet.set_column(idx, idx, max_length * 1.2)
            # Crear hoja 10 Salida con formato visual
            write_hoja_10_salida(writer, df_stats)

    return df_with_stats


def write_hoja_10_salida(writer, df_stats, sheet_name="10 Salida"):
    """
    Escribe la hoja 10 Salida en el Excel, con formato visual tipo bloque por categoría.

    Esta función crea una hoja de Excel con formato visual que muestra:
    - Rentabilidades por período para cada fondo
    - Ranking vs comparables
    - Total de comparables
    - Rentabilidad promedio de comparables
    - Delta vs comparables

    Args:
        writer: ExcelWriter de pandas (engine xlsxwriter)
        df_stats: DataFrame de estadísticas (polars)
        sheet_name: nombre de la hoja
    """
    worksheet = writer.book.add_worksheet(sheet_name)
    writer.sheets[sheet_name] = worksheet

    # Definición de formatos para diferentes tipos de celdas
    azul = writer.book.add_format(
        {
            "bg_color": "#6161ff",
            "font_color": "white",
            "bold": True,
            "align": "left",
            "font_name": "Infra",
        }
    )
    negrita = writer.book.add_format(
        {"bold": True, "font_name": "Infra", "align": "right", "bg_color": "#FFFFFF"}
    )
    normal = writer.book.add_format(
        {"font_name": "Infra", "align": "right", "bg_color": "#FFFFFF"}
    )
    porcentaje = writer.book.add_format(
        {
            "num_format": "0.0%",
            "font_name": "Infra",
            "align": "right",
            "bg_color": "#FFFFFF",
        }
    )
    porcentaje_bold = writer.book.add_format(
        {
            "num_format": "0.0%",
            "bold": True,
            "font_name": "Infra",
            "align": "right",
            "bg_color": "#FFFFFF",
        }
    )
    porcentaje_verde = writer.book.add_format(
        {
            "num_format": "0.0%",
            "font_color": "#008000",
            "font_name": "Infra",
            "align": "right",
            "bg_color": "#FFFFFF",
        }
    )
    porcentaje_rojo = writer.book.add_format(
        {
            "num_format": "0.0%",
            "font_color": "#C00000",
            "font_name": "Infra",
            "align": "right",
            "bg_color": "#FFFFFF",
        }
    )
    vacio = writer.book.add_format({"bg_color": "#FFFFFF"})
    col_a = writer.book.add_format(
        {"font_name": "Infra", "align": "left", "bg_color": "#FFFFFF"}
    )
    col_a_bold = writer.book.add_format(
        {"font_name": "Infra", "align": "left", "bg_color": "#FFFFFF", "bold": True}
    )

    # Estructura de la hoja
    periodos = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"]  # Períodos a mostrar
    categorias = [
        ("BALANCEADO CONSERVADOR", "Fondo Conservador Focus"),
        ("BALANCEADO MODERADO", "Fondo Moderado Focus"),
        ("BALANCEADO AGRESIVO", "Fondo Arriesgado Focus"),
    ]
    filas = [
        "Fondo",
        "Ranking vs Comparables",
        "Total Comparables",
        "Rentabilidad Promedio Comparables",
        "Delta vs Comparables",
    ]

    # Convertir a pandas y preparar datos
    df_pd = df_stats.to_pandas()
    df_pd["PERIODO"] = df_pd["PERIODO"].astype(str)
    if "DELTA_VS_COMPARABLES" not in df_pd.columns:
        df_pd["DELTA_VS_COMPARABLES"] = (
            df_pd["RENTABILIDAD_PERIODO_SOYFOCUS"] - df_pd["RENTABILIDAD_PROMEDIO"]
        )

    # Escribir datos en la hoja
    row = 0
    for cat, fondo in categorias:
        df_cat = df_pd[df_pd["CATEGORIA"] == cat]
        # Encabezado azul con nombre de categoría
        worksheet.write(row, 0, cat.split()[-1].capitalize(), azul)
        for col in range(1, len(periodos) + 1):
            worksheet.write(row, col, "", azul)
        row += 1
        # Encabezado de períodos
        worksheet.write(row, 0, "", azul)
        for j, per in enumerate(periodos):
            worksheet.write(row, j + 1, per, azul)
        row += 1
        # Fondo Focus (negrita, porcentaje)
        worksheet.write(row, 0, fondo, col_a_bold)
        for j, per in enumerate(periodos):
            val = df_cat.loc[df_cat["PERIODO"] == per, "RENTABILIDAD_PERIODO_SOYFOCUS"]
            if not val.empty and pd.notnull(val.values[0]):
                worksheet.write(row, j + 1, float(val.values[0]) - 1, porcentaje_bold)
            else:
                worksheet.write(row, j + 1, "", vacio)
        row += 1
        # Ranking vs Comparables
        worksheet.write(row, 0, "Ranking vs Comparables", col_a)
        for j, per in enumerate(periodos):
            val = df_cat.loc[df_cat["PERIODO"] == per, "POSICION_SOYFOCUS"]
            worksheet.write(
                row,
                j + 1,
                int(val.values[0])
                if not val.empty and pd.notnull(val.values[0])
                else "",
                normal,
            )
        row += 1
        # Total Comparables
        worksheet.write(row, 0, "Total Comparables", col_a)
        for j, per in enumerate(periodos):
            val = df_cat.loc[df_cat["PERIODO"] == per, "NUM_SERIES"]
            worksheet.write(
                row,
                j + 1,
                int(val.values[0])
                if not val.empty and pd.notnull(val.values[0])
                else "",
                normal,
            )
        row += 1
        # Rentabilidad Promedio Comparables (porcentaje)
        worksheet.write(row, 0, "Rentabilidad Promedio Comparables", col_a)
        for j, per in enumerate(periodos):
            val = df_cat.loc[df_cat["PERIODO"] == per, "RENTABILIDAD_PROMEDIO"]
            if not val.empty and pd.notnull(val.values[0]):
                worksheet.write(row, j + 1, float(val.values[0]) - 1, porcentaje)
            else:
                worksheet.write(row, j + 1, "", vacio)
        row += 1
        # Delta vs Comparables (porcentaje, verde/rojo)
        worksheet.write(row, 0, "Delta vs Comparables", col_a)
        for j, per in enumerate(periodos):
            val = df_cat.loc[df_cat["PERIODO"] == per, "DELTA_VS_COMPARABLES"]
            if not val.empty and pd.notnull(val.values[0]):
                v = float(val.values[0])
                fmt = porcentaje_verde if v >= 0 else porcentaje_rojo
                worksheet.write(row, j + 1, v, fmt)
            else:
                worksheet.write(row, j + 1, "", vacio)
        row += 1
        # Fila vacía entre categorías
        row += 1

    # Ajustar anchos de columna
    worksheet.set_column(0, 0, 32)  # Primera columna más ancha
    worksheet.set_column(1, len(periodos), 12)  # Columnas de períodos más estrechas


if __name__ == "__main__":
    # Generar datos para el análisis CLA y guardar pasos intermedios en Excel
    df = generate_cla_data(
        save_xlsx=True,
        xlsx_name="cla_data.xlsx",
        excel_steps="minimal",  # Solo guardar los pasos más relevantes
    )
