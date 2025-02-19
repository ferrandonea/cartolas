"""Utilidades relacionadas con fechas"""

from datetime import date, datetime, timedelta
from typing import Union


def from_date_to_datetime(input_date: datetime | date) -> date:
    """
    Convierte un objeto datetime a date. Si el input ya es un date, lo retorna sin cambios.

    Args:
        input_date (datetime | date): La fecha a convertir.

    Returns:
        date: La fecha convertida.

    Raises:
        ValueError: Si el input no es de tipo datetime o date.
    """
    if not isinstance(input_date, (datetime, date)):
        raise ValueError("El input debe ser de tipo datetime o date")
    return input_date.date() if isinstance(input_date, datetime) else input_date


def format_date_cmf(input_date: date | datetime) -> str:
    """
    Formatea una fecha a string en el formato requerido por la CMF (dd/mm/yyyy).

    Args:
        input_date (date | datetime): La fecha a formatear.

    Returns:
        str: La fecha formateada como string.
    """
    CMF_DATE_FORMAT = r"%d/%m/%Y"
    return from_date_to_datetime(input_date).strftime(CMF_DATE_FORMAT)


def date_range(start_date: date, end_date: date) -> list[date]:
    """
    Genera una lista de fechas entre dos fechas dadas, inclusive.

    Args:
        start_date (date): La fecha de inicio del rango.
        end_date (date): La fecha de término del rango.

    Returns:
        list[date]: Lista de fechas entre start_date y end_date, inclusive.

    Raises:
        ValueError: Si la fecha de inicio es mayor que la fecha de término.
    """

    if (end_date - start_date).days < 0:
        # TODO: Quizás sería mejor invertir las fechas en vez de lanzar un error
        raise ValueError("La fecha de inicio debe ser menor a la fecha de término")

    return [
        start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)
    ]


def consecutive_date_ranges(
    date_list: list[date], max_days: int = 29
) -> list[tuple[date, date]]:
    """
    Identifica secuencias de fechas consecutivas en una lista de fechas, creando rangos.

    Args:
        date_list (list[date]): Lista de fechas a procesar.
        max_days (int, opcional): Número máximo de días permitidos en un rango. Por defecto es 29.

    Returns:
        list[tuple[date, date]]: Lista de tuplas con los rangos de fechas consecutivas.

    Note:
        - Un rango se cierra si la diferencia entre su primera y última fecha excede 'max_days'
          o si hay un salto de más de un día entre fechas consecutivas.
    """

    if not date_list:
        return []

    # Ordenar la lista de fechas
    sorted_dates = sorted(date_list)

    ranges = []
    range_start = sorted_dates[0]
    range_end = sorted_dates[0]

    for current_date in sorted_dates[1:]:
        # Verificar si la fecha actual continúa el rango o inicia uno nuevo
        if (current_date - range_end).days > 1 or (
            current_date - range_start
        ).days > max_days:
            # Cerrar el rango actual y empezar uno nuevo
            ranges.append((range_start, range_end))
            range_start = current_date

        # Actualizar el fin del rango actual
        range_end = current_date

    # Añadir el último rango
    ranges.append((range_start, range_end))

    return ranges


def es_mismo_mes(fecha: Union[datetime, str]) -> bool:
    """
    Verifica si una fecha dada está en el mismo mes que la fecha actual.

    Args:
        fecha (Union[datetime, str]): Fecha a comparar. Puede ser un objeto datetime
            o un string en formato 'YYYY-MM-DD' o 'YYYY-MM-DD HH:MM:SS'

    Returns:
        bool: True si la fecha está en el mismo mes que la fecha actual, False en caso contrario

    Examples:
        >>> es_mismo_mes('2024-03-15')  # Si hoy es marzo 2024
        True
        >>> es_mismo_mes('2024-02-15')  # Si hoy es marzo 2024
        False
        >>> es_mismo_mes(datetime.now())
        True
    """
    try:
        # Si la fecha es un string, convertirla a datetime
        if isinstance(fecha, str):
            try:
                fecha = datetime.strptime(fecha, "%Y-%m-%d")
            except ValueError:
                fecha = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")

        # Obtener fecha actual
        hoy = datetime.now()

        # Comparar año y mes
        return fecha.year == hoy.year and fecha.month == hoy.month

    except Exception as e:
        print(f"Error al comparar fechas: {e}")
        return False


if __name__ == "__main__":
    print("*" * 80)
    print(f"{date_range.__name__}")
    start_date = date(2010, 1, 1)
    end_date = date(2010, 1, 5)
    print(f"{start_date=}, {end_date=}")
    print(f"range: {date_range(start_date, end_date)}")

    try:
        start_date, end_date = end_date, start_date
        print(f"{start_date=}, {end_date=}")
        print(f"range: {date_range(start_date, end_date)}")
    except Exception as e:
        print(f"ERROR: {e}")

    try:
        start_date = end_date = start_date
        print(f"{start_date=}, {end_date=}")
        print(f"range: {date_range(start_date, end_date)}")
    except Exception as e:
        print(f"ERROR: {e}")

    print("*" * 80)
    print(f"{consecutive_date_ranges.__name__}")
    start_date = date(2010, 1, 1)
    end_date = date(2010, 1, 10)
    print(f"{start_date=}, {end_date=}")
    days = 3
    print(f"days: {days}")
    rangos = consecutive_date_ranges(date_range(start_date, end_date), days)
    for i, x in enumerate(rangos):
        print(i, x)

    print("*" * 80)
    print(f"{consecutive_date_ranges.__name__}")
    start_date = date(2010, 1, 1)
    end_date = date(2013, 1, 10)
    print(f"{start_date=}, {end_date=}")
    days = 30
    print(f"days: {days}")
    rangos = consecutive_date_ranges(date_range(start_date, end_date), days)
    for i, x in enumerate(rangos):
        print(i, x)
