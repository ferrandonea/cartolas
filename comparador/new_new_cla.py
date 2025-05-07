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
MESES_CLA = [1, 3, 6]  # Períodos mensuales a analizar
AÑOS_CLA = [1, 3, 5]  # Períodos anuales a analizar
CATEGORIAS_CLA = ["CONSERVADOR", "MODERADO", "AGRESIVO"]  # Categorías base de fondos
# Genera las categorías completas agregando el prefijo "BALANCEADO"
CATEGORIAS_ELMER = [f"BALANCEADO {categoria}" for categoria in CATEGORIAS_CLA]
RELEVANT_COLUMNS = [
    "RUN_FM",
    "SERIE",
    "FECHA_INF",
    "CATEGORIA",
    "RENTABILIDAD_ACUMULADA",
    "RUN_SOYFOCUS",
    "SERIE_SOYFOCUS",
]

# Nombres de las hojas para el archivo Excel
EXCEL_SHEETS = {
    "datos_base": "1 Base",
    "rentabilidades": "2 Acumuladas",
    "categorias": "3 Categoría",
    "columnas": "4 Seleccionadas",
    "fechas": "5 Fecha",
    "rentabilidad_periodo": "6 Rentabilidad Período",
    "final": "7 SoyFocus",
    "estadisticas": "8 Estadísticas"
}

# Pasos que se pueden guardar en Excel
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
        # Fechas para períodos mensuales
        **{mes: date_n_months_ago(mes, current_report_date) for mes in MESES_CLA},
        # Fechas para períodos anuales (convertidos a meses)
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
            .cum_prod()  # Producto acumulativo
            .over(["RUN_FM", "SERIE"])  # Agrupado por fondo y serie
            .fill_nan(1)  # Reemplazar NaN por 1
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
    df = df.with_columns([
        pl.col("RUN_SOYFOCUS").cast(pl.UInt16)
    ])

    # Hacemos el join para obtener la rentabilidad del fondo SoyFocus
    df_joined = df.join(
        df.select(["RUN_FM", "SERIE", "FECHA_INF", "RENTABILIDAD_ACUMULADA", "RENTABILIDAD_PERIODO"]),
        left_on=["RUN_SOYFOCUS", "SERIE_SOYFOCUS", "FECHA_INF"],
        right_on=["RUN_FM", "SERIE", "FECHA_INF"],
        how="left"
    ).rename({
        "RENTABILIDAD_ACUMULADA_right": "RENTABILIDAD_AC_SOYFOCUS",
        "RENTABILIDAD_PERIODO_right": "RENTABILIDAD_PERIODO_SOYFOCUS"
    })

    # Calcular la rentabilidad del período de SoyFocus
    return df_joined.with_columns([
        (pl.col("RENTABILIDAD_PERIODO_SOYFOCUS") / pl.col("RENTABILIDAD_PERIODO")).alias("RENTABILIDAD_PERIODO_SOYFOCUS_REL")
    ])

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
    df_reciente = df.filter(pl.col("FECHA_INF") == fecha_reciente).select([
        "RUN_FM",
        "SERIE",
        "RENTABILIDAD_ACUMULADA"
    ]).rename({"RENTABILIDAD_ACUMULADA": "RENTABILIDAD_ACUMULADA_RECIENTE"})
    
    # Hacer join con el DataFrame original y calcular la rentabilidad del período
    return df.join(
        df_reciente,
        on=["RUN_FM", "SERIE"],
        how="left"
    ).with_columns([
        (pl.col("RENTABILIDAD_ACUMULADA_RECIENTE") / pl.col("RENTABILIDAD_ACUMULADA")).alias("RENTABILIDAD_PERIODO")
    ]).drop("RENTABILIDAD_ACUMULADA_RECIENTE")

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
    stats = df.group_by(["CATEGORIA", "FECHA_INF"]).agg([
        pl.count("SERIE").alias("NUM_SERIES"),
        pl.mean("RENTABILIDAD_PERIODO").alias("RENTABILIDAD_PROMEDIO")
    ])

    # Calcular la posición y rentabilidad de SoyFocus para cada categoría y fecha
    soyfocus_stats = df.group_by(["CATEGORIA", "FECHA_INF"]).agg([
        pl.col("RENTABILIDAD_PERIODO_SOYFOCUS_REL")
        .rank(method="min", descending=False)  # Cambiado a False para que 1 sea la mejor posición
        .filter(pl.col("RUN_FM") == pl.col("RUN_SOYFOCUS"))
        .first()
        .alias("POSICION_SOYFOCUS"),
        pl.col("RENTABILIDAD_PERIODO_SOYFOCUS")
        .filter(pl.col("RUN_FM") == pl.col("RUN_SOYFOCUS"))
        .first()
        .alias("RENTABILIDAD_PERIODO_SOYFOCUS")
    ])

    # Unir las estadísticas con el DataFrame original
    df_with_stats = df.join(
        stats,
        on=["CATEGORIA", "FECHA_INF"],
        how="left"
    ).join(
        soyfocus_stats,
        on=["CATEGORIA", "FECHA_INF"],
        how="left"
    )

    # Crear DataFrame resumen con todas las estadísticas
    df_stats = stats.join(
        soyfocus_stats,
        on=["CATEGORIA", "FECHA_INF"],
        how="left"
    ).sort(["CATEGORIA", "FECHA_INF"])

    return df_with_stats, df_stats

@timer
def create_summary_table(df_stats: pl.DataFrame) -> pd.DataFrame:
    """
    Genera una tabla resumen tipo bloque por categoría, con los principales indicadores como filas y los períodos como columnas,
    siguiendo el formato visual de la imagen de ejemplo del usuario.

    Args:
        df_stats (pl.DataFrame): DataFrame de estadísticas por categoría y fecha (paso 8), con columna PERIODO

    Returns:
        pd.DataFrame: Tabla resumen lista para exportar a Excel
    """
    # Orden y nombres de los indicadores
    indicadores = [
        ("RENTABILIDAD_PERIODO_SOYFOCUS", "Fondo {cat} Focus", True),
        ("POSICION_SOYFOCUS", "Ranking vs Comparables", False),
        ("NUM_SERIES", "Total Comparables", False),
        ("RENTABILIDAD_PROMEDIO", "Rentabilidad Promedio Comparables", True),
        ("DELTA_VS_COMPARABLES", "Delta vs comparables", True)
    ]
    # Orden de los períodos
    periodos_orden = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"]
    # Calcular Delta vs comparables si no existe
    if "DELTA_VS_COMPARABLES" not in df_stats.columns:
        df_stats = df_stats.with_columns([
            (pl.col("RENTABILIDAD_PERIODO_SOYFOCUS") - pl.col("RENTABILIDAD_PROMEDIO")).alias("DELTA_VS_COMPARABLES")
        ])
    df_pd = df_stats.to_pandas()
    # Asegurar que los períodos estén como string
    df_pd["PERIODO"] = df_pd["PERIODO"].astype(str)
    # Lista para bloques
    bloques = []
    categorias = df_pd["CATEGORIA"].unique()
    for cat in categorias:
        bloque = []
        df_cat = df_pd[df_pd["CATEGORIA"] == cat]
        # Diccionario temporal para guardar las rentabilidades transformadas por período
        rent_soyfocus = {}
        rent_promedio = {}
        for col, nombre, es_rentabilidad in indicadores:
            # Ajuste especial para la categoría agresivo
            if col == "RENTABILIDAD_PERIODO_SOYFOCUS" and cat.upper() == "BALANCEADO AGRESIVO":
                nombre_fila = "Fondo Focus Arriesgado"
            else:
                nombre_fila = nombre.replace("{cat}", cat.split()[-1].capitalize())
            fila = [nombre_fila]
            for per in periodos_orden:
                val = df_cat.loc[df_cat["PERIODO"] == per, col]
                if not val.empty:
                    v = val.values[0]
                    if es_rentabilidad and pd.notnull(v):
                        try:
                            v = float(v) - 1
                        except Exception:
                            v = np.nan
                        # Guardar para delta si corresponde
                        if col == "RENTABILIDAD_PERIODO_SOYFOCUS":
                            rent_soyfocus[per] = v
                        if col == "RENTABILIDAD_PROMEDIO":
                            rent_promedio[per] = v
                    fila.append(v)
                else:
                    fila.append(np.nan)
            bloque.append(fila)
        # Corregir la fila de delta: recalcular como diferencia de las filas ya transformadas
        idx_delta = 4  # Es la quinta fila
        for i, per in enumerate(periodos_orden):
            v_soy = rent_soyfocus.get(per, np.nan)
            v_prom = rent_promedio.get(per, np.nan)
            bloque[idx_delta][i+1] = v_soy - v_prom if pd.notnull(v_soy) and pd.notnull(v_prom) else np.nan
        # Crear DataFrame del bloque
        df_bloque = pd.DataFrame(
            bloque,
            columns=["", *periodos_orden]
        )
        # Insertar título de categoría como fila superior
        titulo = pd.DataFrame([[cat.upper()] + ["" for _ in periodos_orden]], columns=df_bloque.columns)
        # Concatenar título, bloque y fila vacía
        bloques.append(titulo)
        bloques.append(df_bloque)
        bloques.append(pd.DataFrame([["" for _ in df_bloque.columns]], columns=df_bloque.columns))
    # Concatenar todos los bloques
    tabla_final = pd.concat(bloques, ignore_index=True)
    return tabla_final

def get_summary_dict(df_stats: pl.DataFrame) -> dict:
    """
    Genera un diccionario limpio por categoría, período e indicador a partir del DataFrame de estadísticas.
    """
    periodos_orden = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"]
    categorias_orden = [
        ("BALANCEADO CONSERVADOR", "Fondo Conservador Focus"),
        ("BALANCEADO MODERADO", "Fondo Moderado Focus"),
        ("BALANCEADO AGRESIVO", "Fondo Focus Arriesgado")
    ]
    indicadores = [
        ("Fondo", "RENTABILIDAD_PERIODO_SOYFOCUS"),
        ("Ranking vs Comparables", "POSICION_SOYFOCUS"),
        ("Total Comparables", "NUM_SERIES"),
        ("Rentabilidad Promedio Comparables", "RENTABILIDAD_PROMEDIO"),
        ("Delta vs comparables", "DELTA_VS_COMPARABLES")
    ]
    df_pd = df_stats.to_pandas()
    summary = {}
    for cat, fondo in categorias_orden:
        summary[cat] = {ind[0]: [] for ind in indicadores}
        for per in periodos_orden:
            row = df_pd[(df_pd["CATEGORIA"] == cat) & (df_pd["PERIODO"] == per)]
            for label, col in indicadores:
                if label == "Fondo":
                    val = row["RENTABILIDAD_PERIODO_SOYFOCUS"].values[0] if not row.empty else None
                else:
                    val = row[col].values[0] if not row.empty else None
                summary[cat][label].append(val)
    return summary

def format_summary_sheet(writer, df_stats, sheet_name="10 Formateado"):
    """
    Escribe la hoja 10 usando solo el resumen estructurado, bloque por bloque, perfectamente alineada y formateada.
    """
    worksheet = writer.sheets[sheet_name]
    workbook = writer.book
    # Formatos base
    base_fmt = workbook.add_format({'font_name': 'Infra', 'bg_color': '#FFFFFF', 'align': 'right'})
    left_fmt = workbook.add_format({'font_name': 'Infra', 'bg_color': '#FFFFFF', 'align': 'left'})
    blue = workbook.add_format({'bg_color': '#6161ff', 'font_color': 'white', 'bold': True, 'font_name': 'Infra'})
    percent = workbook.add_format({'num_format': '0.0%', 'align': 'right', 'font_name': 'Infra', 'bg_color': '#FFFFFF'})
    normal = workbook.add_format({'align': 'right', 'font_name': 'Infra', 'bg_color': '#FFFFFF'})
    percent_bold_underline = workbook.add_format({'num_format': '0.0%', 'bold': True, 'bottom': 2, 'font_name': 'Infra', 'bg_color': '#FFFFFF'})
    percent_green = workbook.add_format({'num_format': '0.0%', 'font_color': '#008000', 'font_name': 'Infra', 'bg_color': '#FFFFFF'})
    percent_red = workbook.add_format({'num_format': '0.0%', 'font_color': '#C00000', 'font_name': 'Infra', 'bg_color': '#FFFFFF'})
    # Orden de bloques y nombres de fondo
    orden_bloques = [
        ("BALANCEADO CONSERVADOR", "Fondo Conservador Focus"),
        ("BALANCEADO MODERADO", "Fondo Moderado Focus"),
        ("BALANCEADO AGRESIVO", "Fondo Focus Arriesgado")
    ]
    periodos_orden = ["1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"]
    filas_bloque = [
        "Fondo", "Ranking vs Comparables", "Total Comparables",
        "Rentabilidad Promedio Comparables", "Delta vs comparables"
    ]
    # Ajustar ancho de columnas solo hasta la I
    worksheet.set_column(0, 0, 32, base_fmt)
    worksheet.set_column(1, 1, 34, left_fmt)
    worksheet.set_column(2, 8, 12, base_fmt)
    # Obtener el resumen limpio
    summary = get_summary_dict(df_stats)
    row = 0
    for cat, fondo in orden_bloques:
        # Título de bloque
        worksheet.write(row, 1, cat, blue)
        # Encabezado de períodos
        worksheet.write_row(row+1, 2, periodos_orden, left_fmt)
        # Fila: Fondo Focus
        worksheet.write(row+2, 1, fondo, left_fmt)
        for j, val in enumerate(summary[cat]["Fondo"]):
            col = 2 + j
            worksheet.write(row+2, col, val, percent_bold_underline)
        # Fila: Ranking vs Comparables
        worksheet.write(row+3, 1, "Ranking vs Comparables", left_fmt)
        for j, val in enumerate(summary[cat]["Ranking vs Comparables"]):
            col = 2 + j
            worksheet.write(row+3, col, val, normal)
        # Fila: Total Comparables
        worksheet.write(row+4, 1, "Total Comparables", left_fmt)
        for j, val in enumerate(summary[cat]["Total Comparables"]):
            col = 2 + j
            worksheet.write(row+4, col, val, normal)
        # Fila: Rentabilidad Promedio Comparables
        worksheet.write(row+5, 1, "Rentabilidad Promedio Comparables", left_fmt)
        for j, val in enumerate(summary[cat]["Rentabilidad Promedio Comparables"]):
            col = 2 + j
            worksheet.write(row+5, col, val, percent)
        # Fila: Delta vs comparables
        worksheet.write(row+6, 1, "Delta vs comparables", left_fmt)
        for j, val in enumerate(summary[cat]["Delta vs comparables"]):
            col = 2 + j
            if pd.notnull(val):
                fmt = percent_green if val >= 0 else percent_red
                worksheet.write(row+6, col, val, fmt)
            else:
                worksheet.write(row+6, col, val, percent)
        # Fila vacía
        row += 8

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
    # Obtener las fechas relevantes
    cla_dates = generate_cla_dates(input_date)
    # Invertir el diccionario para mapear fecha a nombre de período
    fecha_a_periodo = {v: k for k, v in cla_dates.items()}
    periodo_labels = {1: "1M", 3: "3M", 6: "6M", 12: "1Y", 36: "3Y", 60: "5Y", -1: "YTD", 0: "YTD"}
    
    # Diccionario para almacenar los DataFrames intermedios
    dfs_intermedios = {}
    
    # Obtener datos base y agregar categorías
    df_base: pl.LazyFrame = merge_cartolas_with_categories()
    if save_xlsx and excel_steps == "all":
        dfs_intermedios[EXCEL_SHEETS["datos_base"]] = df_base.collect()
    
    # Calcular rentabilidades acumuladas
    df_rent: pl.LazyFrame = add_cumulative_returns(df_base)
    if save_xlsx and excel_steps == "all":
        dfs_intermedios[EXCEL_SHEETS["rentabilidades"]] = df_rent.collect()
    
    # Filtrar por categorías relevantes
    df_cat: pl.LazyFrame = df_rent.filter(pl.col("CATEGORIA").is_in(categories))
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["categorias"]] = df_cat.collect()
    
    # Seleccionar columnas relevantes y convertir a DataFrame
    df_cols: pl.DataFrame = df_cat.collect().select(relevant_columns)
    if save_xlsx and excel_steps == "all":
        dfs_intermedios[EXCEL_SHEETS["columnas"]] = df_cols
    
    # Filtrar por fechas relevantes
    df_fechas: pl.DataFrame = df_cols.filter(
        pl.col("FECHA_INF").is_in(list(cla_dates.values()))
    )
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["fechas"]] = df_fechas
    
    # Calcular rentabilidades del período
    df_periodo: pl.DataFrame = add_period_returns(df_fechas, cla_dates)
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["rentabilidad_periodo"]] = df_periodo
    
    # Agregar rentabilidad de SoyFocus
    df_final: pl.DataFrame = add_soyfocus_returns(df_periodo)
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["final"]] = df_final
    
    # Calcular estadísticas por categoría y fecha
    df_with_stats, df_stats = add_category_statistics(df_final)
    # Agregar columna PERIODO a df_stats
    df_stats = df_stats.with_columns([
        pl.col("FECHA_INF").map_elements(
            lambda x: periodo_labels.get(fecha_a_periodo.get(x, None), str(x)),
            return_dtype=pl.Utf8
        ).alias("PERIODO")
    ])
    if save_xlsx and excel_steps in ["all", "minimal"]:
        dfs_intermedios[EXCEL_SHEETS["estadisticas"]] = df_stats

    # Paso 9: Crear tabla resumen y agregarla al Excel
    if save_xlsx and excel_steps in ["all", "minimal"]:
        tabla_resumen = create_summary_table(df_stats)
        dfs_intermedios["9 Resumen"] = tabla_resumen
        # Paso 10: Copiar y formatear
        dfs_intermedios["10 Formateado"] = tabla_resumen.copy()

    
    # Guardar todos los DataFrames en el Excel si se solicitó
    if save_xlsx and dfs_intermedios:
        dfs_pandas = {}
        for sheet_name, df in dfs_intermedios.items():
            if isinstance(df, pl.DataFrame):
                dfs_pandas[sheet_name] = df.to_pandas()
            else:
                dfs_pandas[sheet_name] = df
        with pd.ExcelWriter(xlsx_name, engine='xlsxwriter') as writer:
            for sheet_name, df in dfs_pandas.items():
                if sheet_name == "10 Formateado":
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                else:
                    df.to_excel(writer, sheet_name=sheet_name, index=True)
                worksheet = writer.sheets[sheet_name]
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    worksheet.set_column(idx, idx, max_length * 1.2)
            # Formatear la hoja 10 si existe
            if "10 Formateado" in dfs_pandas:
                if "DELTA_VS_COMPARABLES" not in df_stats.columns:
                    df_stats = df_stats.with_columns([
                        (pl.col("RENTABILIDAD_PERIODO_SOYFOCUS") - pl.col("RENTABILIDAD_PROMEDIO")).alias("DELTA_VS_COMPARABLES")
                    ])
                format_summary_sheet(writer, df_stats, sheet_name="10 Formateado")
    
    return df_with_stats


if __name__ == "__main__":
    # Generar fechas para el análisis CLA
    cla_dates = generate_cla_dates()
    print(f"{cla_dates = }")
    
    # Generar datos para el análisis CLA y guardar pasos intermedios en Excel
    df = generate_cla_data(
        save_xlsx=True,
        xlsx_name="cla_data.xlsx",
        excel_steps="minimal"  # Solo guardar los pasos más relevantes
    )
