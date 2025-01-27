""" Utilidades relacionadas con fechas """

from datetime import date, datetime, timedelta

def from_date_to_datetime(input_date: datetime | date) -> date:
    """Esto recibe una fecha, si es datetime da la fecha, si es date la deja igual"""
    if not isinstance(input_date, (datetime, date)):
        raise ValueError("El input debe ser de tipo datetime o date")
    return input_date.date() if isinstance(input_date, datetime) else input_date


def format_date_cmf(input_date: date | datetime) -> str:
    """Formatea una fecha a string para la CMF"""
    CMF_DATE_FORMAT = r"%d/%m/%Y"
    return from_date_to_datetime(input_date).strftime(CMF_DATE_FORMAT)

