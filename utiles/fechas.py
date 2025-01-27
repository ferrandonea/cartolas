"""Utilidades relacionadas con fechas"""

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


def date_range(start_date: date, end_date: date) -> list[date]:
    """
    Genera un rango de fechas entre dos fechas, esta es una función sencilla
    que toma todo como date, habría que camiarla para tomar datetime, es inclusivo
    de la fecha de inicio y la del final
    """

    if (end_date - start_date).days < 0:
        # TODO: Quizás sería mejor invertir las fechas en vez de lanzar un error
        raise ValueError("La fecha de inicio debe ser menor a la fecha de término")

    print()
    return [
        start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)
    ]


def consecutive_date_ranges(
    date_list: list[date], max_days: int = 29
) -> list[tuple[date, date]]:
    """Esta función identifica secuencias de fechas que están separadas por no más de un día,
    creando rangos. Un rango se cierra si la diferencia entre su primera y última fecha
    excede 'max_days' o si hay un salto de más de un día entre fechas consecutivas.
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
