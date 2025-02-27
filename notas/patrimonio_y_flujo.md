## Patrimonio

El patrimonio de un fondo es el valor de los activos del fondo menos los pasivos. Utilizando la información de la cartola diaria se puede calcular el patrimonio de un fondo a una fecha determinada de la siguiente manera:

$P_{t} = C_{t} \cdot VC_{t} $

Donde $C_{t}$ es el número de cuotas del fondo a la fecha $t$ y $VC_{t}$ es el valor cuota a la fecha $t$.

## Flujo

Corresponde al flujo de aportes y retiros de los inversionistas. Se calcula a partir de las cuotas aportadas y retiradas de un fondo.

$F_{t} = (CA_{t} - CR_{t}) \cdot VC_{t} $

Donde, $F_{t}$ es el flujo del fondo a la fecha $t$, $CA_{t}$ es el número de cuotas aportadas al fondo a la fecha $t$, $CR_{t}$ es el número de cuotas retiradas del fondo a la fecha $t$ y $VC_{t}$ es el valor cuota a la fecha $t$.

Alternativamente, se puede calcular con la variación del número de cuotas del fondo.

$F_{t} = (C_{t} - C_{t-1}) \cdot VC_{t} $

Donde, $F_{t}$ es el flujo del fondo a la fecha $t$, $C_{t}$ es el número de cuotas del fondo a la fecha $t$ y $VC_{t}$ es el valor cuota a la fecha $t$.

## Cambios en el patrimonio

Así existen tres fuentes de cambios en el patrimonio:

1. Flujos de aportes y retiros de los inversionistas.
2. Utilidad por las operaciones del fondo.
3. También existe la posibilidad de cambios producto de retiros o dividendos en efectivo.

Así

$P_{t} = P_{t-1} + F_{t} + U_{t} + R_{t} $

Donde, $P_{t}$ es el patrimonio del fondo a la fecha $t$, $F_{t}$ es el flujo del fondo a la fecha $t$, $U_{t}$ es la utilidad por las operaciones del fondo a la fecha $t$ y $R_{t}$ es el cambio en el patrimonio producto de retiros o dividendos en efectivo a la fecha $t$.

Podemos reordenar la ecuación para obtener el delta de patrimonio.

$\Delta P_{t} = F_{t} + U_{t} + R_{t} $

Donde, $\Delta P_{t}$ es el cambio en el patrimonio del fondo a la fecha $t$.

### Repartos de dividendos

La información de dividendos se puede obtener a partir del factor de reparto de la cartola diaria que tiene, de acuerdo a la circular 1.581-2002 de la cmf, la siguiente fórmula:

$FR_{t} = \frac{d_{t}}{VC_{t}} + 1 $

Donde $FR_{t}$ es el factor de reparto del fondo a la fecha $t$, $d_{t}$ es el dividendo del fondo por cuota a la fecha $t$ y $VC_{t}$ es el valor cuota a la fecha $t$.

Así, el dividendo por cuota es:

$d_{t} = (FR_{t} - 1) \cdot VC_{t} $

Donde, $d_{t}$ es el dividendo del fondo por cuota a la fecha $t$, $FR_{t}$ es el factor de reparto del fondo a la fecha $t$ y $VC_{t}$ es el valor cuota a la fecha $t$.

Por lo tanto el flujo de dividendos es:

$R_{t} = d_{t} \cdot C_{t} $

Donde, $R_{t}$ es el flujo de dividendos a la fecha $t$, $d_{t}$ es el dividendo del fondo por cuota a la fecha $t$ y $C_{t}$ es el número de cuotas del fondo a la fecha $t$.

## Cálculo de la utilidad por las operaciones del fondo

De acuerdo a lo anterior, el delta patrimonio se puede descomponer de la siguiente manera:

$\Delta P_{t} = F_{t} + U_{t} + R_{t} $

Usando las fórmulas anteriores, se puede obtener la utilidad por las operaciones del fondo de la siguiente manera:

$U_{t} = \Delta P_{t} - F_{t} - R_{t} $

Donde, $U_{t}$ es la utilidad por las operaciones del fondo a la fecha $t$, $\Delta P_{t}$ es el cambio en el patrimonio del fondo a la fecha $t$, $F_{t}$ es el flujo del fondo a la fecha $t$ y $R_{t}$ es el flujo de dividendos a la fecha $t$.















