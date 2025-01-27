""" Este módulo se encarga de actualizar las cartolas de la CMF. """

from datetime import date, datetime, timedelta

## FECHAS
FECHA_MINIMA = date(2007, 12, 31)
# Esto considera los días para atrás que es la última cartola
# Si es antes de las 11 es el de ante ayer, si es después de las 11 es el de ayer
DIAS_ATRAS = 1 if datetime.now().hour > 11 else 2
FECHA_MAXIMA = datetime.now().date() - timedelta(days=DIAS_ATRAS)
