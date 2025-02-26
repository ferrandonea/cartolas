from comparador.merge import merge_cartolas_with_categories
import polars as pl
from datetime import datetime

def calcular_rentabilidad_periodos(df: pl.LazyFrame, fecha_consulta: datetime) -> pl.LazyFrame:
    # FECHA_INF asumo es de tipo pl.Date
    df_hasta_fecha = df.filter(pl.col("FECHA_INF") <= fecha_consulta)
    
    return df_hasta_fecha

if __name__ == "__main__":
    df = merge_cartolas_with_categories()  
    changed_df = calcular_rentabilidad_periodos(df, datetime(2024, 1, 1))
    print (changed_df.collect())
    