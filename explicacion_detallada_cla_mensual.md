# EXPLICACIÓN ULTRA DETALLADA DE `cla_mensual.py`
## Para alguien que no escribió el código

---

## 📋 ÍNDICE DE CONTENIDO

1. [Introducción: ¿Qué hace este programa?](#introduccion)
2. [¿Qué es un archivo `.py`?](#que-es-py)
3. [Repaso del código completo](#codigo-completo)
4. [Explicación línea por línea](#linea-por-linea)
   - [Parte 1: El Docstring del Módulo](#parte-1-docstring)
   - [Parte 2: Los Imports](#parte-2-imports)
   - [Parte 3: Cálculo de REPORT_DATE](#parte-3-report-date)
   - [Parte 4: Configuración de Rutas](#parte-4-rutas)
   - [Parte 5: La Función main()](#parte-5-funcion-main)
   - [Parte 6: El Punto de Entrada](#parte-6-punto-entrada)
5. [Flujo completo de ejecución](#flujo-ejecucion)
6. [Resumen visual completo](#resumen-visual)

---

<a name="introduccion"></a>
## 🎯 ¿QUÉ HACE ESTE PROGRAMA?

Imagina que tienes una empresa de inversiones llamada **SoyFocus** que administra fondos mutuos. Cada mes necesitas saber:
- ¿Cómo les fue a tus fondos?
- ¿Ganaron o perdieron dinero?
- ¿Cómo se comparan con otros fondos similares en el mercado?

**Este programa hace exactamente eso**: genera automáticamente un reporte mensual en Excel que compara el desempeño de los fondos SoyFocus contra todos los demás fondos mutuos de Chile.

---

<a name="que-es-py"></a>
## 📂 ¿QUÉ ES UN ARCHIVO `.py`?

Antes de comenzar, aclaremos: un archivo `.py` es un **programa escrito en Python**. Python es un lenguaje de programación (como si fueran instrucciones en español que la computadora entiende).

`cla_mensual.py` es el nombre del archivo. Significa:
- `cla` = "Comparación de Liquidez y Activos" o simplemente el nombre del reporte
- `mensual` = se ejecuta una vez al mes
- `.py` = es un programa en Python

---

<a name="codigo-completo"></a>
## 📖 REPASEMOS EL CÓDIGO COMPLETO PRIMERO

```python
"""
Script para generar el reporte mensual de análisis CLA (Comparación de Rentabilidades).

Este script automatiza el proceso de generación del reporte mensual de análisis CLA, que incluye:
1. Actualización de datos históricos de fondos mutuos
2. Actualización de datos del Banco Central
3. Generación del reporte CLA con comparativas de rentabilidad

El reporte se guarda en un archivo Excel con la fecha del último día del mes anterior.
"""

from comparador.cla_monthly import generate_cla_data
from cartolas.update_by_year import update_parquet_by_year
from eco.bcentral import update_bcch_parquet
from datetime import date
from utiles.fechas import ultimo_dia_mes_anterior
from pathlib import Path

# Fecha del reporte: último día del mes anterior
REPORT_DATE = ultimo_dia_mes_anterior(date.today())

# Configuración de rutas y nombres de archivos
CLA_FOLDER = "cla_mensual"  # Carpeta donde se guardarán los reportes
CLA_EXCEL = Path(CLA_FOLDER) / f"cla_{REPORT_DATE.strftime('%Y%m%d')}.xlsx"  # Nombre del archivo Excel


def main():
    """
    Función principal que ejecuta el proceso completo de generación del reporte CLA.

    El proceso incluye:
    1. Actualización de datos históricos de fondos mutuos
    2. Actualización de datos del Banco Central
    3. Generación del reporte CLA con comparativas de rentabilidad

    El reporte se guarda en un archivo Excel con la fecha del último día del mes anterior.
    """
    print(CLA_EXCEL)

    # Paso 1: Actualizar datos históricos de fondos mutuos
    print("Actualizando parquet por año")
    update_parquet_by_year()

    # Paso 2: Actualizar datos del Banco Central
    print("Actualizando bcch parquet")
    update_bcch_parquet()

    # Paso 3: Generar reporte CLA mensual
    print("Generando cla mensual")
    generate_cla_data(
        save_xlsx=True,  # Guardar resultados en Excel
        xlsx_name=CLA_EXCEL,  # Nombre del archivo Excel
        excel_steps="all"  # Guardar todos los pasos intermedios
    )


if __name__ == "__main__":
    main()
```

---

<a name="linea-por-linea"></a>
## 🔍 EXPLICACIÓN LÍNEA POR LÍNEA

<a name="parte-1-docstring"></a>
### **PARTE 1: El "comentario de ayuda" (líneas 1-9)**

```python
"""
Script para generar el reporte mensual de análisis CLA (Comparación de Rentabilidades).
...
"""
```

#### **¿Qué es esto?**

Todo lo que está entre `"""` y `"""` es un **comentario largo** llamado **docstring** (documentation string).

Los comentarios NO se ejecutan, son solo para que los humanos entiendan el código. Es como poner un Post-it en tu código diciendo "esto hace X cosa".

#### **¿Para qué sirve?**

- Explica rápidamente qué hace el programa completo
- Cualquier persona que abra este archivo sabrá inmediatamente su propósito
- Las herramientas de documentación automática pueden leerlo

#### **Diferencia entre comentarios:**

```python
# Esto es un comentario de UNA línea
# Si quiero escribir más, necesito otra línea con #
# Y otra más...

"""
Esto es un docstring de MÚLTIPLES líneas.
Puedo escribir todo lo que quiera aquí.
No necesito poner # en cada línea.
"""
```

#### **Análisis del contenido:**

```
Script para generar el reporte mensual de análisis CLA (Comparación de Rentabilidades).
```
- **"Script"**: Programa que se ejecuta de principio a fin (no es una biblioteca)
- **"mensual"**: Se ejecuta una vez al mes
- **"CLA"**: Nombre del reporte

```
Este script automatiza el proceso de generación del reporte mensual de análisis CLA, que incluye:
```
- **"automatiza"**: Lo hace sin intervención humana
- **"proceso"**: Conjunto de pasos ordenados

```
1. Actualización de datos históricos de fondos mutuos
2. Actualización de datos del Banco Central
3. Generación del reporte CLA con comparativas de rentabilidad
```
- Lista numerada de los 3 pasos principales
- Da una vista rápida de lo que hace el script

---

<a name="parte-2-imports"></a>
### **PARTE 2: Los "imports" - Traer herramientas (líneas 12-17)**

```python
from comparador.cla_monthly import generate_cla_data
from cartolas.update_by_year import update_parquet_by_year
from eco.bcentral import update_bcch_parquet
from datetime import date
from utiles.fechas import ultimo_dia_mes_anterior
from pathlib import Path
```

#### **¿Qué significa esto?**

Imagina que estás cocinando. Antes de empezar, necesitas sacar los ingredientes del refrigerador y los utensilios del cajón. Los `import` hacen exactamente eso: traen herramientas que ya fueron programadas antes.

#### **Anatomía de un import:**

```
from CARPETA.ARCHIVO import FUNCIÓN
```

#### **Estructura de carpetas del proyecto:**

```
📁 cartolas/                    ← Carpeta raíz del proyecto
  📄 cla_mensual.py             ← Estamos aquí
  📁 comparador/                ← Carpeta con funciones de comparación
    📄 cla_monthly.py           ← Contiene generate_cla_data
  📁 cartolas/                  ← Carpeta con funciones de datos
    📄 update_by_year.py        ← Contiene update_parquet_by_year
  📁 eco/                       ← Carpeta con funciones económicas
    📄 bcentral.py              ← Contiene update_bcch_parquet
  📁 utiles/                    ← Carpeta con utilidades
    📄 fechas.py                ← Contiene ultimo_dia_mes_anterior
```

---

#### **IMPORT 1: `generate_cla_data` (Línea 12)**

```python
from comparador.cla_monthly import generate_cla_data
```

**Desglose:**

1. **`from`**: Palabra clave de Python que significa "desde"
2. **`comparador`**: Nombre de una **carpeta** (también llamada "paquete")
3. **`.`**: Separador que significa "dentro de"
4. **`cla_monthly`**: Nombre de un **archivo Python** (sin el `.py`)
5. **`import`**: Palabra clave que significa "tráeme"
6. **`generate_cla_data`**: Nombre de una **función** dentro de ese archivo

**¿Qué hace esta función?**

Es la función más importante del script. Ejecuta un pipeline (cadena de procesos) de 9 pasos:

1. Genera fechas relevantes para análisis (1M, 3M, 6M, 1Y, 3Y, 5Y)
2. Lee datos de fondos mutuos
3. Calcula rentabilidades acumuladas
4. Filtra por categorías (Conservador, Moderado, Agresivo)
5. Filtra por fechas relevantes
6. Calcula rentabilidades por período
7. Agrega datos de fondos SoyFocus
8. Calcula estadísticas (rankings, promedios)
9. Genera archivo Excel con 10 hojas

**Parámetros que acepta:**

```python
def generate_cla_data(
    input_date: date = date.today(),           # Fecha base para el análisis
    categories: list[str] = CATEGORIAS_ELMER,  # Categorías a incluir
    relevant_columns: list[str] = RELEVANT_COLUMNS,  # Columnas a mantener
    save_xlsx: bool = False,                   # Si guardar en Excel
    xlsx_name: str = "cla_data.xlsx",         # Nombre del archivo
    excel_steps: str = "minimal",              # Nivel de detalle
) -> pl.DataFrame:
```

**Retorna:**
- Un DataFrame de Polars con los datos procesados

---

#### **IMPORT 2: `update_parquet_by_year` (Línea 13)**

```python
from cartolas.update_by_year import update_parquet_by_year
```

**¿Qué hace esta función?**

Actualiza archivos Parquet con datos de fondos mutuos, organizados por año.

**Proceso interno detallado:**

**Paso 1: Verifica archivos existentes**
```
Para cada año desde 2007 hasta 2025:
  ¿Existe el archivo cartolas_YYYY.parquet?
  Si existe → leer las fechas que contiene
  Si no existe → marcar todas las fechas del año como faltantes
```

**Paso 2: Identifica fechas faltantes**
```
Fechas que deberían estar: [1-ene, 2-ene, 3-ene, ..., 31-dic]
Fechas que ya tengo:       [1-ene, 2-ene, 5-ene, ..., 30-sep]
Fechas faltantes:          [3-ene, 4-ene, ..., 1-oct, 2-oct, ...]
```

**Paso 3: Agrupa fechas en rangos consecutivos**
```
Ejemplo de salida:
0 : 01/10/2025 -> 05/10/2025
1 : 10/10/2025 -> 12/10/2025
```

**Paso 4: Descarga datos de la CMF**
- Se conecta a: `https://www.cmfchile.cl/institucional/estadisticas/fondos_cartola_diaria.php`
- Usa web scraping para descargar archivos TXT
- Espera 1 segundo entre cada descarga (para no sobrecargar el servidor)

**Paso 5: Transforma datos TXT a Parquet**

Los archivos TXT descargados tienen un formato como:
```
RUN_ADM|NOM_ADM|RUN_FM|FECHA_INF|...
12345678|BANCO ESTADO|1234|01/10/2025|...
```

Esta función:
- Lee todos los archivos TXT
- Los convierte a formato tabular (filas y columnas)
- Limpia los datos
- Convierte tipos de datos (texto → números, fechas)

**Paso 6: Filtra por año**

Si descargaste datos de 2025, solo guarda los registros donde el año es 2025.

**Paso 7: Concatena datos nuevos con existentes**

```
Datos existentes:  [enero] [febrero] [marzo] ... [septiembre]
Datos nuevos:                                    [octubre 1-11]
Resultado:         [enero] [febrero] [marzo] ... [septiembre] [octubre 1-11]
```

**Paso 8: Guarda archivo Parquet**

Sobrescribe `cartolas_2025.parquet` con la versión actualizada.

**Paso 9: Limpia archivos temporales**

Elimina todos los archivos TXT descargados (ya no los necesitas).

**Parámetros:**

```python
def update_parquet_by_year(
    base_dir: Path = PARQUET_FOLDER_YEAR,  # cartolas/data/yearly/
    min_date: date = FECHA_MINIMA,         # 2007-12-31
    max_date: date = FECHA_MAXIMA,         # ayer o anteayer
    sleep_time: int = 1,                   # segundos entre descargas
) -> None:
```

**¿Qué es "parquet"?**

Parquet es un formato de archivo para guardar datos (como Excel pero más eficiente):
- Comprimido (ocupa menos espacio)
- Rápido de leer
- Mejor que CSV para grandes volúmenes
- Usado en ciencia de datos

**Duración estimada:**
- Si está actualizado: < 1 segundo
- Si faltan 10 días: ~2-3 minutos
- Si es la primera vez: 30-60 minutos

---

#### **IMPORT 3: `update_bcch_parquet` (Línea 14)**

```python
from eco.bcentral import update_bcch_parquet
```

**¿Qué hace esta función?**

Descarga series temporales económicas del Banco Central de Chile usando su API oficial.

**Proceso interno detallado:**

**Paso 1: Intenta cargar archivo existente**
```python
try:
    df = load_bcch_from_parquet()
    last_date = get_last_date_from_parquet(df)
except FileNotFoundError:
    last_date = datetime(1970, 1, 1).date()  # Fecha muy antigua
```

**¿Por qué 1970?**

Es una fecha "época" en informática (Unix epoch). Al usar una fecha tan antigua, garantiza que descargue TODO el historial.

**Paso 2: Compara con fecha objetivo**

Si ya tienes datos hasta ayer o más reciente, no hace nada y retorna.

**Paso 3: Descarga datos del BCCh**

**3a. Inicializa conexión con API**
```python
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)
```

- `bcchapi` es una biblioteca Python para la API del Banco Central
- Necesita usuario y contraseña (guardados en archivo `.env`)

**3b. Lee configuración de series**

Lee el archivo `bcentral_tickers.json`:

```json
{
  "DOLAR": {
    "TICKER": "F073.TCO.PRE.Z.D",
    "NOMBRE": "Dólar Observado"
  },
  "EURO": {
    "TICKER": "F072.CLP.EUR.N.O.D",
    "NOMBRE": "Euro"
  },
  "UF": {
    "TICKER": "F073.UF.Z.Z.Z.D",
    "NOMBRE": "Unidad de Fomento"
  }
}
```

**3c. Descarga todas las series**

```python
return BCCh.cuadro(series=tickers, nombres=nombres, hasta=last_date).ffill()
```

- `cuadro()`: Descarga múltiples series en un solo DataFrame
- `.ffill()`: Rellena valores faltantes con el último valor conocido

**Ejemplo de datos descargados:**

| FECHA_INF | DOLAR | EURO | UF |
|-----------|-------|------|-----|
| 2025-10-01| 920.5 | 1005.2| 37542.12|
| 2025-10-02| 922.3 | 1008.7| 37543.89|
| 2025-10-03| 918.7 | 1002.1| 37545.67|

**¿Por qué necesitas estos datos?**

Porque algunos fondos invierten en dólares o euros. Para compararlos, necesitas convertir todo a pesos chilenos.

**Ejemplo:**
```
Fondo A tiene $1,000 USD
Si el dólar está a $900 pesos → Fondo vale $900,000 pesos
Si el dólar sube a $950 pesos → Fondo vale $950,000 pesos
¡Ganó $50,000 pesos solo por el tipo de cambio!
```

**Paso 4: Guarda archivo Parquet**

Sobrescribe `cartolas/data/bcch/bcch.parquet` con los datos actualizados.

**Duración estimada:**
- Si está actualizado: < 0.1 segundos
- Si necesita actualizar: 5-30 segundos

---

#### **IMPORT 4: `date` (Línea 15)**

```python
from datetime import date
```

**¿Qué es `datetime`?**

Es un **módulo de la biblioteca estándar de Python**. No necesitas instalarlo, viene con Python.

Contiene clases para trabajar con fechas y horas:
- `date`: Solo fecha (año, mes, día)
- `datetime`: Fecha + hora
- `time`: Solo hora
- `timedelta`: Diferencia entre fechas

**¿Cómo se usa?**

```python
# Crear fecha de hoy
hoy = date.today()
print(hoy)  # 2025-10-14

# Crear fecha específica
navidad = date(2025, 12, 25)
print(navidad)  # 2025-12-25

# Componentes de una fecha
print(hoy.year)   # 2025
print(hoy.month)  # 10
print(hoy.day)    # 14

# Formatear fecha
print(hoy.strftime('%d/%m/%Y'))  # 14/10/2025
```

**En este script se usa:**

```python
REPORT_DATE = ultimo_dia_mes_anterior(date.today())
```

`date.today()` obtiene la fecha actual del sistema operativo.

---

#### **IMPORT 5: `ultimo_dia_mes_anterior` (Línea 16)**

```python
from utiles.fechas import ultimo_dia_mes_anterior
```

**¿Qué hace esta función?**

Calcula el último día del mes anterior a partir de una fecha base.

**Implementación:**

```python
def ultimo_dia_mes_anterior(base_date: date = None) -> date:
    if base_date is None:
        base_date = date.today()

    # Ir al primer día del mes actual y restar un día
    return base_date.replace(day=1) - timedelta(days=1)
```

**¿Cómo funciona?**

Usa un truco inteligente:

1. Va al primer día del mes actual: `base_date.replace(day=1)`
2. Resta un día: `... - timedelta(days=1)`

**Ejemplo:**

Si hoy es `14-oct-2025`:
1. Primer día del mes: `01-oct-2025`
2. Restar 1 día: `30-sep-2025`

**¿Por qué funciona?**

Al ir al primer día del mes y restar 1 día, automáticamente caes en el último día del mes anterior, sin importar cuántos días tenga ese mes (28, 29, 30 o 31).

**Más ejemplos:**

```python
# Si hoy es 14 de octubre de 2025
ultimo_dia_mes_anterior(date(2025, 10, 14))
# Resultado: 2025-09-30

# Si hoy es 5 de marzo de 2024 (año bisiesto)
ultimo_dia_mes_anterior(date(2024, 3, 5))
# Resultado: 2024-02-29  (febrero tiene 29 días en año bisiesto)

# Si hoy es 1 de enero de 2025
ultimo_dia_mes_anterior(date(2025, 1, 1))
# Resultado: 2024-12-31  (cruza al año anterior)
```

---

#### **IMPORT 6: `Path` (Línea 17)**

```python
from pathlib import Path
```

**¿Qué es `pathlib`?**

Es un **módulo de la biblioteca estándar de Python** para trabajar con rutas de archivos y carpetas de manera moderna.

**¿Por qué usar `Path` en lugar de strings?**

**Forma antigua (strings):**
```python
# Tienes que concatenar manualmente
carpeta = "cla_mensual"
archivo = "cla_20250930.xlsx"
ruta = carpeta + "/" + archivo  # Problema: solo funciona en Linux/Mac
ruta = carpeta + "\\" + archivo  # Problema: solo funciona en Windows
```

**Forma moderna (Path):**
```python
from pathlib import Path

carpeta = Path("cla_mensual")
archivo = "cla_20250930.xlsx"
ruta = carpeta / archivo  # Funciona en todos los sistemas operativos
```

**Ventajas de Path:**

1. **Operador `/` para concatenar:**
   ```python
   ruta = Path("carpeta") / "subcarpeta" / "archivo.txt"
   ```

2. **Multiplataforma automático:**
   ```python
   # En Windows: carpeta\subcarpeta\archivo.txt
   # En Linux/Mac: carpeta/subcarpeta/archivo.txt
   ```

3. **Métodos útiles:**
   ```python
   ruta = Path("archivo.txt")

   ruta.exists()         # ¿Existe el archivo?
   ruta.is_file()        # ¿Es un archivo?
   ruta.is_dir()         # ¿Es una carpeta?
   ruta.mkdir()          # Crear carpeta
   ruta.read_text()      # Leer contenido
   ruta.write_text("..") # Escribir contenido
   ```

4. **Componentes de la ruta:**
   ```python
   ruta = Path("/home/user/proyecto/datos.csv")

   ruta.name         # "datos.csv"
   ruta.stem         # "datos" (sin extensión)
   ruta.suffix       # ".csv"
   ruta.parent       # Path("/home/user/proyecto")
   ```

---

<a name="parte-3-report-date"></a>
### **PARTE 3: CÁLCULO DE REPORT_DATE (Línea 20)**

```python
REPORT_DATE = ultimo_dia_mes_anterior(date.today())
```

#### **¿Qué sucede cuando Python lee esta línea?**

Python ejecuta el código **de derecha a izquierda**:

**Paso 1: `date.today()`**

Pregunta al sistema operativo: "¿Qué día es hoy?"

Resultado:
```python
datetime.date(2025, 10, 14)
```

Es un **objeto** de tipo `date` que representa el 14 de octubre de 2025.

**Paso 2: `ultimo_dia_mes_anterior(...)`**

Llama a la función pasándole la fecha de hoy.

Proceso interno:
1. Recibe: `date(2025, 10, 14)`
2. Hace: `date(2025, 10, 14).replace(day=1)` → `date(2025, 10, 1)`
3. Hace: `date(2025, 10, 1) - timedelta(days=1)` → `date(2025, 9, 30)`
4. Retorna: `date(2025, 9, 30)`

**Paso 3: Asignación a `REPORT_DATE`**

```python
REPORT_DATE = date(2025, 9, 30)
```

Guarda el resultado en una **variable** llamada `REPORT_DATE`.

#### **¿Por qué está en MAYÚSCULAS?**

Es una **convención de estilo** en Python:
- `minusculas` → variables normales
- `MAYUSCULAS` → constantes (valores que no deberían cambiar)

#### **¿Es realmente constante?**

**No técnicamente**. Python no tiene constantes "reales". Podrías cambiarla:

```python
REPORT_DATE = date(2025, 9, 30)
REPORT_DATE = date(2024, 1, 1)  # Funciona, pero NO deberías hacerlo
```

Pero las MAYÚSCULAS son una **señal** para otros programadores: "No cambies esto".

#### **¿Por qué el último día del mes anterior?**

Los reportes financieros siempre se hacen "cerrados" al final del mes. Por ejemplo:
- Hoy es 14 de octubre
- Pero el reporte que vas a generar es del mes de **septiembre completo**
- Por eso necesitas la fecha 30-sep-2025

#### **¿Cuándo se ejecuta esta línea?**

**Importante:** Esta línea se ejecuta **cuando Python carga el archivo**, NO cuando ejecutas `main()`.

**Ejemplo:**

```python
# Archivo: cla_mensual.py
print("Cargando módulo...")
REPORT_DATE = ultimo_dia_mes_anterior(date.today())
print(f"REPORT_DATE = {REPORT_DATE}")

def main():
    print("Ejecutando main()...")
    print(f"Usando fecha: {REPORT_DATE}")

if __name__ == "__main__":
    main()
```

**Salida:**
```
Cargando módulo...
REPORT_DATE = 2025-09-30
Ejecutando main()...
Usando fecha: 2025-09-30
```

Nota cómo "Cargando módulo..." aparece ANTES de ejecutar `main()`.

#### **Implicación práctica:**

Si importas el módulo a las 10 AM y ejecutas `main()` a las 11 PM, `REPORT_DATE` sigue siendo el valor calculado a las 10 AM.

---

<a name="parte-4-rutas"></a>
### **PARTE 4: CONFIGURACIÓN DE RUTAS (Líneas 23-24)**

#### **Línea 23: `CLA_FOLDER`**

```python
CLA_FOLDER = "cla_mensual"
```

**¿Qué es esto?**

Una **constante de configuración** que define el nombre de la carpeta donde se guardarán los reportes.

**Tipo de dato:**

```python
type(CLA_FOLDER)  # <class 'str'>
```

Es un **string** (cadena de texto), NO un objeto `Path`.

**Interpretación:**

Es una **ruta relativa**:
- No empieza con `/` (Linux/Mac) o `C:\` (Windows)
- Es relativa al **directorio de trabajo actual**

**¿Cuál es el directorio de trabajo actual?**

El directorio desde donde ejecutas el script:

```bash
cd /Users/franciscoerrandonea/code/cartolas/
python cla_mensual.py
```

Directorio de trabajo: `/Users/franciscoerrandonea/code/cartolas/`

Por lo tanto, `"cla_mensual"` se interpreta como:
```
/Users/franciscoerrandonea/code/cartolas/cla_mensual/
```

---

#### **Línea 24: `CLA_EXCEL`**

```python
CLA_EXCEL = Path(CLA_FOLDER) / f"cla_{REPORT_DATE.strftime('%Y%m%d')}.xlsx"
```

Esta línea es **compleja**. Vamos a descomponerla en partes.

**Parte 1: `Path(CLA_FOLDER)`**

Convierte el string `"cla_mensual"` en un objeto `Path`.

**Antes:**
```python
CLA_FOLDER = "cla_mensual"  # tipo: str
```

**Después:**
```python
Path(CLA_FOLDER)  # tipo: pathlib.Path
```

**Parte 2: `/` (operador de concatenación)**

El operador `/` está **sobrecargado** en la clase `Path`.

**¿Qué significa "sobrecargado"?**

Normalmente `/` es división:
```python
10 / 2  # 5.0
```

Pero la clase `Path` le da un significado diferente: "unir rutas".

**Ejemplos:**
```python
Path("carpeta") / "archivo.txt"
# Resultado: Path("carpeta/archivo.txt")

Path("a") / "b" / "c" / "d.txt"
# Resultado: Path("a/b/c/d.txt")
```

**Parte 3: `f"cla_{REPORT_DATE.strftime('%Y%m%d')}.xlsx"`**

Este es un **f-string** (formatted string literal).

**¿Qué es un f-string?**

Una forma de insertar variables dentro de strings usando `{}`.

**La `f` antes de las comillas es crucial:**

```python
# Sin f (string normal)
"cla_{REPORT_DATE}.xlsx"
# Resultado: "cla_{REPORT_DATE}.xlsx"  (literal, no reemplaza)

# Con f (f-string)
f"cla_{REPORT_DATE}.xlsx"
# Resultado: "cla_2025-09-30.xlsx"  (sí reemplaza)
```

**Parte 3a: `"cla_"`**

Texto literal. Se mantiene como está.

**Parte 3b: `{REPORT_DATE.strftime('%Y%m%d')}`**

Todo lo que está entre `{}` se **ejecuta como código Python**.

**¿Qué es `strftime`?**

Significa "string format time". Es un método de objetos `date` y `datetime` que convierte fechas a strings con un formato específico.

**Códigos de formato:**

| Código | Significado | Ejemplo |
|--------|-------------|---------|
| `%Y` | Año con 4 dígitos | 2025 |
| `%y` | Año con 2 dígitos | 25 |
| `%m` | Mes con 2 dígitos (01-12) | 09 |
| `%d` | Día con 2 dígitos (01-31) | 30 |
| `%B` | Nombre del mes completo | September |
| `%b` | Nombre del mes abreviado | Sep |

**En nuestro caso:**
```python
REPORT_DATE.strftime('%Y%m%d')
```

- `REPORT_DATE` = `date(2025, 9, 30)`
- `'%Y%m%d'` = formato "AñoMesDía" sin separadores

**Proceso:**
1. `%Y` → `2025`
2. `%m` → `09` (con cero a la izquierda)
3. `%d` → `30`
4. Concatena: `20250930`

**Parte 3c: `".xlsx"`**

Texto literal. La extensión del archivo Excel.

**Resultado completo:**

```python
f"cla_{REPORT_DATE.strftime('%Y%m%d')}.xlsx"
# Se convierte en:
"cla_20250930.xlsx"
```

#### **Juntando todo:**

**Paso a paso:**

1. `CLA_FOLDER` = `"cla_mensual"`
2. `Path(CLA_FOLDER)` = `Path("cla_mensual")`
3. `REPORT_DATE.strftime('%Y%m%d')` = `"20250930"`
4. `f"cla_{...}.xlsx"` = `"cla_20250930.xlsx"`
5. `Path("cla_mensual") / "cla_20250930.xlsx"` = `Path("cla_mensual/cla_20250930.xlsx")`
6. `CLA_EXCEL` = `Path("cla_mensual/cla_20250930.xlsx")`

**Visualización:**
```
📁 cla_mensual/
  📄 cla_20250930.xlsx  ← Este archivo
```

**¿Por qué este formato de nombre?**

- Incluye la fecha en el nombre para saber qué mes es cada reporte
- El formato AAAAMMDD ordena cronológicamente:
  ```
  cla_20250830.xlsx  ← Agosto
  cla_20250930.xlsx  ← Septiembre
  cla_20251031.xlsx  ← Octubre
  ```

---

<a name="parte-5-funcion-main"></a>
### **PARTE 5: LA FUNCIÓN `main()` (Líneas 27-54)**

#### **Línea 27: Definición de la función**

```python
def main():
```

**Anatomía de una definición de función:**

```
def NOMBRE(PARAMETROS):
    CUERPO
```

**Componentes:**

1. **`def`**: Palabra clave de Python que significa "define una función"
2. **`main`**: Nombre de la función (podría ser cualquier nombre válido)
3. **`()`**: Paréntesis vacíos = no acepta parámetros
4. **`:`**: Dos puntos que indican el inicio del cuerpo de la función
5. **Indentación**: Todo el código con sangría pertenece a la función

**¿Qué hace `def`?**

**Crea** la función pero **no la ejecuta**.

**Analogía:**

Es como escribir una receta en un libro de cocina. La receta existe, pero no estás cocinando todavía. Para cocinar, tienes que "llamar" a la función:

```python
def hacer_cafe():
    print("Moliendo café...")
    print("Calentando agua...")
    print("☕ ¡Café listo!")

# La función existe, pero no se ha ejecutado
hacer_cafe()  # Ahora SÍ se ejecuta
```

**¿Por qué se llama `main`?**

Es una **convención** de muchos lenguajes de programación. Significa "función principal" o "punto de entrada principal".

---

#### **Líneas 28-37: Docstring de la función**

```python
    """
    Función principal que ejecuta el proceso completo de generación del reporte CLA.

    El proceso incluye:
    1. Actualización de datos históricos de fondos mutuos
    2. Actualización de datos del Banco Central
    3. Generación del reporte CLA con comparativas de rentabilidad

    El reporte se guarda en un archivo Excel con la fecha del último día del mes anterior.
    """
```

Un **docstring** específico de la función que documenta:
- **Qué hace** la función
- **Qué parámetros** acepta (en este caso, ninguno)
- **Qué retorna** (en este caso, nada)
- **Efectos secundarios** (crea archivos, imprime en pantalla)

---

#### **Línea 38: Primer print**

```python
    print(CLA_EXCEL)
```

**¿Qué hace `print`?**

Muestra texto en la **salida estándar** (stdout), que normalmente es la terminal/consola.

**¿Qué valor tiene `CLA_EXCEL`?**

```python
Path("cla_mensual/cla_20250930.xlsx")
```

**Salida en pantalla:**

```
cla_mensual/cla_20250930.xlsx
```

**¿Para qué sirve?**

- Informa al usuario dónde se va a guardar el archivo
- Permite verificar que la ruta es correcta
- Útil para debugging

---

#### **Líneas 41-42: Paso 1 - Actualizar fondos mutuos**

```python
    # Paso 1: Actualizar datos históricos de fondos mutuos
    print("Actualizando parquet por año")
    update_parquet_by_year()
```

**Línea 41: Comentario**

```python
    # Paso 1: Actualizar datos históricos de fondos mutuos
```

Es un **comentario** que explica QUÉ hace el código siguiente.

**Línea 42: Print informativo**

```python
    print("Actualizando parquet por año")
```

Muestra: `Actualizando parquet por año`

**Línea 43: Llamada a función**

```python
    update_parquet_by_year()
```

**¿Qué es esto?**

Una **llamada a función** (function call).

**¿Qué significa "llamar" a una función?**

**Ejecutarla**. Python:
1. Pausa la ejecución de `main()`
2. Salta a la función `update_parquet_by_year()`
3. Ejecuta todo el código dentro de esa función
4. Cuando termina, regresa a `main()` y continúa

**Visualización del flujo:**

```
main() línea 43:  update_parquet_by_year()
                           ↓
                  [salta a update_parquet_by_year()]
                           ↓
                  [ejecuta todo su código]
                           ↓
                  [descarga datos, guarda archivos]
                           ↓
                  [termina y retorna None]
                           ↓
main() línea 45:  print("Actualizando bcch parquet")
```

**¿Qué pasa si no usaras paréntesis?**

```python
update_parquet_by_year  # Sin ()
```

Esto **no llama** a la función. Solo hace referencia a ella.

**¿La función acepta parámetros?**

Sí, pero todos tienen valores por defecto:

```python
def update_parquet_by_year(
    base_dir: Path = PARQUET_FOLDER_YEAR,
    min_date: date = FECHA_MINIMA,
    max_date: date = FECHA_MAXIMA,
    sleep_time: int = 1,
) -> None:
```

Cuando llamas sin argumentos, usa los valores por defecto.

**¿Cuánto tarda?**

- Si está actualizado: < 1 segundo
- Si faltan 10 días: ~2-3 minutos
- Si es la primera vez: 30-60 minutos

---

#### **Líneas 45-46: Paso 2 - Actualizar Banco Central**

```python
    # Paso 2: Actualizar datos del Banco Central
    print("Actualizando bcch parquet")
    update_bcch_parquet()
```

Mismo patrón que el Paso 1:
1. Comentario explicativo
2. Print informativo
3. Llamada a función

**Llamada a `update_bcch_parquet()`:**

**¿Retorna algo?**

Sí, un `pl.LazyFrame`, pero **no usamos el valor retornado** en este script.

**¿Cuánto tarda?**

- Si está actualizado: < 0.1 segundos
- Si necesita actualizar: 5-30 segundos

---

#### **Líneas 49-54: Paso 3 - Generar reporte**

```python
    # Paso 3: Generar reporte CLA mensual
    print("Generando cla mensual")
    generate_cla_data(
        save_xlsx=True,  # Guardar resultados en Excel
        xlsx_name=CLA_EXCEL,  # Nombre del archivo Excel
        excel_steps="all"  # Guardar todos los pasos intermedios
    )
```

**¿Por qué está en múltiples líneas?**

Es una convención de estilo de Python (PEP 8):
- Cuando una función tiene muchos argumentos
- Es mejor ponerlos en líneas separadas para legibilidad

#### **Argumentos explicados:**

**Argumento 1: `save_xlsx=True`**

- **Tipo:** `bool` (booleano: `True` o `False`)
- **Significado:** "Sí, quiero que guardes el resultado en un archivo Excel"

**¿Qué pasa si fuera `False`?**

La función solo retornaría el DataFrame sin guardar archivo.

**Argumento 2: `xlsx_name=CLA_EXCEL`**

- **Tipo:** `Path` o `str`
- **Valor:** `Path("cla_mensual/cla_20250930.xlsx")`
- **Significado:** "Guarda el archivo con este nombre y en esta ubicación"

**Argumento 3: `excel_steps="all"`**

- **Tipo:** `str`
- **Valores posibles:** `"all"`, `"minimal"`, `"none"`
- **Significado:** Controla cuántas hojas se incluyen en el Excel

**Valores:**

1. **`"all"`**: Todas las hojas (10 hojas total) - útil para análisis profundo
2. **`"minimal"`**: Solo hojas clave (5-6 hojas) - suficiente para reporte
3. **`"none"`**: Sin hojas intermedias - solo lo esencial

**Nota:** El comentario en el código dice "Guardar solo los pasos más relevantes" pero debería decir "Guardar **todos** los pasos" porque usa `"all"`.

---

#### **¿Qué hace `generate_cla_data` internamente?**

Es una función MUY compleja. Resumen del pipeline de 9 pasos:

**Paso 1: Generar fechas CLA**

Crea diccionario con fechas relevantes:

```python
{
    1: date(2025, 8, 30),    # 1 mes atrás
    3: date(2025, 6, 30),    # 3 meses atrás
    6: date(2025, 3, 31),    # 6 meses atrás
    12: date(2024, 9, 30),   # 1 año atrás
    36: date(2022, 9, 30),   # 3 años atrás
    60: date(2020, 9, 30),   # 5 años atrás
    -1: date(2024, 12, 31),  # Último día del año anterior
    0: date(2025, 9, 30)     # Fecha actual del reporte
}
```

**Paso 2: Merge de cartolas con categorías**

Lee y combina:
- Datos de fondos mutuos (Parquet)
- Datos del Banco Central (Parquet)
- Categorías de Elmer (JSON)

**Paso 3: Calcular rentabilidades acumuladas**

Para cada fondo y cada día, calcula rentabilidad acumulada desde el inicio.

**Ejemplo:**

| Fecha | Valor Cuota | Rent. Diaria | Rent. Acumulada |
|-------|-------------|--------------|-----------------|
| 01-ene| $1,000      | 1.0000       | 1.0000          |
| 02-ene| $1,010      | 1.0100       | 1.0100          |
| 03-ene| $1,020      | 1.0099       | 1.0200          |
| 04-ene| $1,015      | 0.9951       | 1.0150          |

**Paso 4: Filtrar por categorías**

Solo mantiene fondos de categorías relevantes:
- BALANCEADO CONSERVADOR
- BALANCEADO MODERADO
- BALANCEADO AGRESIVO

**Paso 5: Seleccionar columnas relevantes**

Reduce el DataFrame a columnas necesarias:
- RUN_FM, SERIE, FECHA_INF
- CATEGORIA
- RENTABILIDAD_ACUMULADA
- RUN_SOYFOCUS, SERIE_SOYFOCUS

**Paso 6: Filtrar por fechas relevantes**

Solo mantiene registros de las 8 fechas calculadas en Paso 1.

**Antes:** Millones de filas
**Después:** ~10,000 filas

**Paso 7: Calcular rentabilidades del período**

Calcula rentabilidad ENTRE dos fechas.

**Fórmula:**
```
RENTABILIDAD_PERIODO = RENT_ACUM_FINAL / RENT_ACUM_INICIAL
```

**Ejemplo:**
```
Rent. acum. 30-ago: 1.0500
Rent. acum. 30-sep: 1.0725

Rentabilidad 1 mes: 1.0725 / 1.0500 = 1.0214 = +2.14%
```

**Paso 8: Agregar datos de SoyFocus**

Hace un **self-join** para obtener la rentabilidad del fondo SoyFocus correspondiente.

**Paso 9: Calcular estadísticas**

Para cada categoría y período, calcula:
- Número de series con datos
- Posición de SoyFocus (ranking)
- Rentabilidad promedio
- Delta vs promedio

**Paso 10: Crear archivo Excel**

Usa `xlsxwriter` para:
- Crear archivo Excel
- Escribir 10 hojas de cálculo
- Aplicar formato (colores, fuentes, anchos)
- Crear hoja final "10 Salida" con formato visual

**Hojas generadas:**

1. 1 Base - Datos crudos
2. 2 Acumuladas - Rentabilidades acumuladas
3. 3 Categoría - Solo categorías relevantes
4. 4 Seleccionadas - Columnas importantes
5. 5 Fecha - Fechas de análisis
6. 6 Rentabilidad Período - Rentabilidades por período
7. 7 SoyFocus - Comparación con SoyFocus
8. 8 Estadísticas - Resumen estadístico
9. 9 Resumen - Tabla resumen
10. **10 Salida** - Reporte visual formateado ⭐

**La hoja 10 Salida se ve así:**

```
┌─────────────────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ Conservador     │ 1M  │ 3M  │ 6M  │ YTD │ 1Y  │ 3Y  │ 5Y  │
├─────────────────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│ Fondo Focus     │ 2.1%│ 5.3%│ 8.2%│ 9.1%│10.5%│25.3%│45.2%│
│ Ranking         │ 3   │ 5   │ 2   │ 3   │ 4   │ 1   │ 2   │
│ Total Fondos    │ 47  │ 47  │ 47  │ 47  │ 46  │ 42  │ 35  │
│ Promedio        │ 1.8%│ 4.9%│ 7.8%│ 8.5%│ 9.8%│23.1%│41.3%│
│ Delta           │+0.3%│+0.4%│+0.4%│+0.6%│+0.7%│+2.2%│+3.9%│
└─────────────────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

---

<a name="parte-6-punto-entrada"></a>
### **PARTE 6: EL PUNTO DE ENTRADA (Líneas 57-58)**

```python
if __name__ == "__main__":
    main()
```

#### **¿Qué es esto?**

Es un **idiom** (expresión idiomática) de Python. Una frase especial con significado específico.

#### **¿Qué es `__name__`?**

Es una **variable especial** que Python crea automáticamente en cada módulo.

**Dunder:** Double underscore (doble guion bajo): `__algo__`

#### **¿Qué valor tiene `__name__`?**

Depende de **cómo se usa el archivo**:

**Caso 1: Ejecutar el archivo directamente**

```bash
python cla_mensual.py
```

Python establece: `__name__ = "__main__"`

**Caso 2: Importar el archivo**

```python
import cla_mensual
```

Python establece: `__name__ = "cla_mensual"`

#### **¿Por qué es útil?**

Permite que un archivo funcione de **dos formas**:

1. **Como script ejecutable** - ejecuta código al correrlo
2. **Como biblioteca importable** - solo define funciones

#### **Ejemplo:**

```python
# archivo: saludos.py

def saludar(nombre):
    print(f"¡Hola, {nombre}!")

if __name__ == "__main__":
    saludar("Francisco")
```

**Ejecutar directamente:**
```bash
python saludos.py
# Salida: ¡Hola, Francisco!
```

**Importar:**
```python
import saludos
saludos.saludar("María")
# Salida: ¡Hola, María!
# Nota: NO imprime "¡Hola, Francisco!"
```

#### **En `cla_mensual.py`:**

```python
if __name__ == "__main__":
    main()
```

**Significado:**

"Si estás ejecutando este archivo directamente (no importándolo), entonces ejecuta la función `main()`."

#### **Línea 58: `main()`**

Llamada a la función `main()` que definimos antes.

Esto **inicia todo el proceso**:
1. Imprime ruta del Excel
2. Actualiza datos de fondos
3. Actualiza datos del BCCh
4. Genera reporte CLA

---

<a name="flujo-ejecucion"></a>
## 🔄 FLUJO COMPLETO DE EJECUCIÓN

Cuando ejecutas `python cla_mensual.py`, esto sucede **en orden**:

### **Fase 1: Carga del módulo**

```
1. Python lee el archivo de arriba hacia abajo
2. Ejecuta los imports (trae funciones de otros archivos)
3. Ejecuta cálculos de nivel módulo:
   - REPORT_DATE = ultimo_dia_mes_anterior(date.today())
   - CLA_EXCEL = Path(...) / f"cla_{...}.xlsx"
4. Define la función main() (pero NO la ejecuta)
5. Llega a: if __name__ == "__main__":
6. Comprueba: __name__ == "__main__"  → True
7. Ejecuta: main()
```

### **Fase 2: Ejecución de `main()`**

```
8. Entra en main()
9. print(CLA_EXCEL)
   → Muestra: cla_mensual/cla_20250930.xlsx

10. print("Actualizando parquet por año")
    → Muestra: Actualizando parquet por año

11. update_parquet_by_year()
    → Pausa main()
    → Ejecuta descarga de datos
    → Retorna a main()

12. print("Actualizando bcch parquet")
    → Muestra: Actualizando bcch parquet

13. update_bcch_parquet()
    → Pausa main()
    → Descarga datos del BCCh
    → Retorna a main()

14. print("Generando cla mensual")
    → Muestra: Generando cla mensual

15. generate_cla_data(...)
    → Pausa main()
    → Ejecuta pipeline de 9 pasos
    → Crea archivo Excel
    → Retorna a main()

16. Fin de main()
17. Fin del programa
```

### **Salida en pantalla:**

```
cla_mensual/cla_20250930.xlsx
Actualizando parquet por año
Fechas faltantes para 2025:
0 : 01/10/2025 -> 11/10/2025
Descargando datos de CMF...
Grabando parquet para el año 2025
Actualizando bcch parquet
BCCH: Última fecha en el archivo: 2025-10-10
BCCH: Actualizando datos del BCCh
Generando cla mensual
current_report_date = datetime.date(2025, 9, 30)
⏱️ generate_cla_dates ejecutada en 0.001s
⏱️ add_cumulative_returns ejecutada en 2.543s
⏱️ add_period_returns ejecutada en 1.234s
⏱️ add_soyfocus_returns ejecutada en 0.876s
⏱️ add_category_statistics ejecutada en 0.543s
⏱️ generate_cla_data ejecutada en 8.432s
```

---

<a name="resumen-visual"></a>
## 📊 RESUMEN VISUAL COMPLETO

```
┌─────────────────────────────────────────────────┐
│  ARCHIVO: cla_mensual.py                        │
└─────────────────────────────────────────────────┘

📝 DOCSTRING DEL MÓDULO (líneas 1-9)
   "Explicación de qué hace el script"

📦 IMPORTS (líneas 12-17)
   ├─ generate_cla_data     ← Genera el reporte
   ├─ update_parquet_by_year ← Actualiza fondos
   ├─ update_bcch_parquet   ← Actualiza BCCh
   ├─ date                  ← Clase para fechas
   ├─ ultimo_dia_mes_anterior ← Calcula fecha
   └─ Path                  ← Trabaja con rutas

📅 CONSTANTES (líneas 20, 23-24)
   ├─ REPORT_DATE = 30-sep-2025
   ├─ CLA_FOLDER = "cla_mensual"
   └─ CLA_EXCEL = Path("cla_mensual/cla_20250930.xlsx")

⚙️ FUNCIÓN main() (líneas 27-54)
   │
   ├─ [Imprime ruta del Excel]
   │
   ├─ PASO 1: update_parquet_by_year()
   │   ├─ Verifica archivos existentes
   │   ├─ Identifica fechas faltantes
   │   ├─ Descarga datos de CMF
   │   ├─ Transforma TXT → Parquet
   │   └─ Guarda archivos actualizados
   │
   ├─ PASO 2: update_bcch_parquet()
   │   ├─ Carga archivo existente
   │   ├─ Verifica última fecha
   │   ├─ Descarga de API del BCCh
   │   └─ Guarda archivo Parquet
   │
   └─ PASO 3: generate_cla_data(...)
       ├─ Genera fechas relevantes
       ├─ Lee datos de fondos + BCCh
       ├─ Calcula rentabilidades acumuladas
       ├─ Filtra por categorías y fechas
       ├─ Calcula rentabilidades del período
       ├─ Agrega datos de SoyFocus
       ├─ Calcula estadísticas
       ├─ Crea archivo Excel con 10 hojas
       └─ Aplica formato visual

🚪 PUNTO DE ENTRADA (líneas 57-58)
   if __name__ == "__main__":
       main()  ← Ejecuta todo el proceso
```

---

## 🔑 CONCEPTOS CLAVE PARA RECORDAR

### **1. Variables**
```python
REPORT_DATE = ultimo_dia_mes_anterior(date.today())
```
Una variable es como una caja con etiqueta donde guardas un valor.

### **2. Funciones**
```python
def main():
    # código aquí
```
Una función es una receta: tiene nombre y pasos a seguir.

### **3. Llamar a una función**
```python
update_parquet_by_year()
```
"Llamar" es ejecutar la función (como si presionaras un botón).

### **4. Parámetros**
```python
generate_cla_data(save_xlsx=True, xlsx_name=CLA_EXCEL)
```
Parámetros son opciones que le pasas a una función.

### **5. Imports**
```python
from cartolas.update_by_year import update_parquet_by_year
```
Importar es traer código de otros archivos para usarlo aquí.

### **6. Comentarios**
```python
# Esto es un comentario de una línea
"""Esto es un comentario
   de varias líneas"""
```
Los comentarios son notas para humanos, no se ejecutan.

### **7. Strings (cadenas de texto)**
```python
"cla_mensual"
f"cla_{REPORT_DATE}.xlsx"
```
Texto entre comillas. La `f` permite meter variables.

---

## 💡 PREGUNTAS FRECUENTES

### **P: ¿Cuánto tarda en ejecutarse todo el programa?**
**R:** Depende:
- Primera vez (sin datos): 30-60 minutos
- Ejecuciones normales: 3-8 minutos
- Si ya está actualizado: 1-2 minutos

### **P: ¿Qué pasa si hay un error?**
**R:** El programa se detiene y muestra un mensaje de error. No hay manejo de errores actualmente (es una mejora pendiente).

### **P: ¿Dónde se guardan los datos descargados?**
**R:**
```
📁 cartolas/data/
  📁 yearly/          ← Datos de fondos mutuos
    📄 cartolas_2024.parquet
    📄 cartolas_2025.parquet
  📁 bcch/            ← Datos del Banco Central
    📄 bcch.parquet
  📁 elmer/           ← Clasificación de fondos
    📄 *.json
```

### **P: ¿Necesito internet para ejecutar esto?**
**R:** Sí, para:
- Descargar datos de la CMF (si hay fechas faltantes)
- Descargar datos del Banco Central (si hay actualizaciones)
- Si los datos ya están actualizados, NO necesitas internet

### **P: ¿Qué pasa si lo ejecuto dos veces el mismo día?**
**R:** La segunda vez será más rápida porque:
- Los datos ya están descargados
- Solo regenera el Excel
- Tarda menos de 1 minuto

### **P: ¿Qué es "Parquet"?**
**R:** Es un formato de archivo para guardar tablas de datos. Ventajas:
- Comprimido (ocupa menos espacio)
- Rápido de leer
- Mejor que CSV para grandes volúmenes
- Usado en ciencia de datos

---

## 🎓 RESUMEN FINAL EN UNA ORACIÓN

> **`cla_mensual.py` es un programa que descarga datos de fondos mutuos y del Banco Central, calcula rentabilidades de múltiples períodos, compara fondos SoyFocus con la competencia, y genera un reporte Excel profesional.**

---

## 🎯 LOS 3 PASOS CLAVE

1. 📥 **Descargar datos de fondos** (CMF)
2. 📥 **Descargar datos económicos** (BCCh)
3. 📊 **Generar reporte Excel** con comparativas

---

## 📄 ARCHIVO RESULTANTE

- **Ubicación:** `cla_mensual/cla_20250930.xlsx`
- **Hojas:** 10 hojas de cálculo
- **Hoja principal:** "10 Salida" con reporte visual
- **Frecuencia:** Una vez al mes
- **Fecha del reporte:** Último día del mes anterior

---

**¡Fin de la explicación detallada!**
