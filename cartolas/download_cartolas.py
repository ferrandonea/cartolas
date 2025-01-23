from datetime import date, datetime
from captchapass import predict

DEFAULT_HEADLESS = True
URL_CARTOLAS = ""
VERBOSE = True

def from_date_to_datetime(input_date: datetime | date) -> date:
    """ Esto recibe una fecha, si es datetime da la fecha, si es date la deja igual"""
    if not isinstance(input_date, (datetime, date)):
        raise ValueError("El input debe ser de tipo datetime o date")
    return input_date.date() if isinstance(input_date, datetime) else input_date

def format_date_cmf(input_date: date | datetime) -> str:
    """ Formatea una fecha a string para la CMF"""
    CMF_DATE_FORMAT = r"%d/%m/%Y"
    return from_date_to_datetime(input_date).strftime(CMF_DATE_FORMAT)

def download_cartolas(
    start_date: date | datetime,
    end_date: date | datetime,
    headless: bool = DEFAULT_HEADLESS,
    url: str = URL_CARTOLAS,
    verbose:  bool = VERBOSE
):
    """ Descarga cartolas desde la CMF en unas fechas determinadas"""
    
     # Define una función lambda para formatear las fechas según el formato CMF
    format_date = lambda d: format_date_cmf(d)
    # Aplica la función de formato a las fechas de inicio y fin
    start_date, end_date = map(format_date, [start_date, end_date])
    
    if verbose:
        print ("*" * 80)
        print (f"Descargando cartolas desde {start_date} hasta {end_date}")
        
    
if __name__ == "__main__":
    start_date = date(2021, 1, 1)
    end_date = date(2021, 12, 31)
    download_cartolas(start_date, end_date)