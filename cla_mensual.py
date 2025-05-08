from comparador.new_new_cla import generate_cla_data
from cartolas.update_by_year import update_parquet_by_year
from eco.bcentral import update_bcch_parquet
from datetime import date
from utiles.fechas import ultimo_dia_mes_anterior
from pathlib import Path

REPORT_DATE = ultimo_dia_mes_anterior(date.today())
CLA_FOLDER = "cla_mensual"
CLA_EXCEL = Path(CLA_FOLDER) / f"cla_{REPORT_DATE.strftime('%Y%m%d')}.xlsx"


def main():
    print(CLA_EXCEL)
    print("Actualizando parquet por año")
    update_parquet_by_year()
    print("Actualizando bcch parquet")
    update_bcch_parquet()
    print("Generando cla mensual")
    generate_cla_data(save_xlsx=True, xlsx_name=CLA_EXCEL, excel_steps="minimal")


if __name__ == "__main__":
    main()
