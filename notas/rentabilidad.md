# Rentabilidad

Para calcular la rentabilidad, se utiliza la siguiente fórmula:

$$
RT_{(0,T)} = \frac{VC_T\prod_{t=1}^{T}F_{t}}{VC_0} - 1
$$

Donde:

- $RT_{(0,T)}$ es la rentabilidad total del fondo desde el día 0 al día T.
- $VC_T$ es el valor cuota del fondo al cierre del día T.
- $F_t$ es el producto entre el factor de ajuste y el factor de reparto del día t.

## Rentabilidad en pesos de fondos en moneda extranjera

Para calcular la rentabilidad en moneda extranjera de fondos en moneda extranjera, se utiliza la siguiente fórmula:

$$
RTE_{(0,T)} = \frac{VCE_T\prod_{t=1}^{T}F_{t}}{VCE_0} - 1
$$

Donde:

- $RTE_{(0,T)}$ es la rentabilidad total del fondo desde el día 0 al día T en moneda extranjera.
- $VCE_T$ es el valor cuota del fondo en moneda extranjera al cierre del día T.
- $VCE_0$ es el valor cuota del fondo en moneda extranjera al cierre del día 0.
- $F_t$ es el producto entre el factor de ajuste y el factor de reparto del día t.

Ahora, sabemos que $$VCE_{T} = \frac{{VC_{T}}}{TC_{T}}$$

Donde:

- $VCE_T$ es el valor cuota del fondo en moneda extranjera al cierre del día T.
- $VC_T$ es el valor cuota del fondo al cierre en pesos del día T.
- $TC_T$ es el tipo de cambio al cierre del día T en pesos por unidad de moneda extranjera.

Entonces, podemos reescribir la fórmula de la rentabilidad en moneda extranjera como:

$$
RTE_{(0,T)} = \frac{\frac{{VC_{T}}}{TC_{T}}\prod_{t=1}^{T}F_{t}}{\frac{{VC_{0}}}{TC_{0}}} - 1
$$

Agrupando los factores de ajuste y de reparto, tenemos:

$$
RTE_{(0,T)} = \frac{VC_{T}\cdot \prod_{t=1}^{T}F_{t} }{VC_{0}} \cdot \frac{TC_{0}}{TC_{T}} - 1
$$

Que es lo mismo que:

$$
RTE_{(0,T)} = (RT_{(0,T)} +1 )\cdot \frac{TC_{0}}{TC_{T}}-1
$$

Si llamamos $RFX_{(0,T)}$ a la rentabilidad del tipo de cambio, definida como:

$$
RFX_{(0,T)} = \frac{TC_{0}}{TC_{T}}-1
$$

Entonces, la rentabilidad en moneda extranjera es:

$$
RTE_{(0,T)} = (RT_{(0,T)} +1 )\cdot (RFX_{(0,T)}+1)-1
$$

Que es el resultado esperado. Por lo que los factores de ajuste y de reparto son los mismos para calcular la rentabilidad en moneda extranjera y en pesos.




