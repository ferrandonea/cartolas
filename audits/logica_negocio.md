# Auditoría de Lógica de Negocio — Cartolas

**Fecha:** 2026-03-16
**Alcance:** Análisis de lógica de negocio, condiciones de carrera, manipulación de datos financieros, bypass de validaciones y vulnerabilidades de integridad de datos.
**Score de riesgo global: 5.5 / 10**

---

## Hallazgos

---

### 1. Defaults silenciosos en tipo de cambio enmascaran datos faltantes

| Campo | Valor |
|-------|-------|
| **Severidad** | Alta |
| **CWE** | CWE-754 (Improper Check for Unusual or Exceptional Conditions) |
| **Archivo** | `comparador/merge.py:77` |

**Evidencia:**

```python
# merge.py:74-78
merged_df = cartola_df.join(
    eco_df, on=["MONEDA", "FECHA_INF"], how="left"
).with_columns(
    pl.col("TIPO_CAMBIO").fill_null(1)  # <-- Asume 1:1 si falta el tipo de cambio
)
```

**Por qué importa:**
Cuando el BCCh no tiene datos para una fecha (feriados, fallas de API, datos atrasados), el tipo de cambio se asume como 1.0. Para fondos en USD o EUR, esto significa que el valor cuota en pesos se calcula como si 1 USD = 1 CLP, lo cual distorsiona todas las métricas derivadas: rentabilidad diaria, acumulada, rankings y comparaciones. Los fondos con moneda extranjera aparecerán con rentabilidades artificialmente bajas o altas según el día.

**Pasos de reproducción:**
1. Eliminar o vaciar el archivo `cartolas/data/bcch/bcch.parquet`
2. Ejecutar `cla_mensual2.py` sin conexión a internet (para que falle la actualización BCCh)
3. Observar que todos los fondos en USD/EUR tendrán tipo de cambio = 1

**Remediación:**

```python
# Opción 1: Filtrar registros sin tipo de cambio válido
merged_df = cartola_df.join(
    eco_df, on=["MONEDA", "FECHA_INF"], how="left"
).filter(
    pl.col("TIPO_CAMBIO").is_not_null() | (pl.col("MONEDA") == "PESOS")
)

# Opción 2: Marcar explícitamente y manejar downstream
.with_columns(
    pl.when(pl.col("MONEDA") == "PESOS")
    .then(pl.lit(1.0))
    .otherwise(pl.col("TIPO_CAMBIO"))  # Deja null si no hay dato
    .alias("TIPO_CAMBIO")
)
```

---

### 2. Rentabilidad diaria: división por cero y NaN enmascarados como "sin retorno"

| Campo | Valor |
|-------|-------|
| **Severidad** | Alta |
| **CWE** | CWE-682 (Incorrect Calculation) |
| **Archivo** | `comparador/merge.py:117-126` |

**Evidencia:**

```python
# merge.py:117-126
.with_columns(
    (
        (
            pl.col("VALOR_CUOTA_PESOS_AJUSTADO")
            / pl.col("VALOR_CUOTA_ANTERIOR_PESOS")
        )
        .fill_nan(1)   # NaN (0/0) se convierte en 1.0 = "sin retorno"
        .fill_null(1)   # null (primer día del fondo) también
    ).alias("RENTABILIDAD_DIARIA_PESOS")
)
```

**Por qué importa:**
- Si `VALOR_CUOTA_ANTERIOR_PESOS` es 0 (dato corrupto), la división produce `NaN` o `Inf`, que se convierte silenciosamente en 1.0 (rentabilidad neutral).
- No hay forma de distinguir "dato corrupto" de "primer día del fondo" de "rentabilidad genuina de 0%".
- Esto se propaga a `RENTABILIDAD_ACUMULADA` (`cla_monthly.py:132-141`) mediante `cum_prod()`, donde un solo valor incorrecto de 1.0 puede hacer que un fondo parezca no perder nunca.

**Remediación:**

```python
.with_columns(
    pl.when(pl.col("VALOR_CUOTA_ANTERIOR_PESOS").is_null())
    .then(pl.lit(None))  # Primer día: null explícito
    .when(pl.col("VALOR_CUOTA_ANTERIOR_PESOS") == 0)
    .then(pl.lit(None))  # Dato corrupto: null explícito
    .otherwise(
        pl.col("VALOR_CUOTA_PESOS_AJUSTADO") / pl.col("VALOR_CUOTA_ANTERIOR_PESOS")
    )
    .alias("RENTABILIDAD_DIARIA_PESOS")
)
```

---

### 3. Inyección de fórmulas Excel en reportes CLA

| Campo | Valor |
|-------|-------|
| **Severidad** | Alta |
| **CWE** | CWE-1236 (Improper Neutralization of Formula Elements in a CSV File) |
| **Archivo** | `comparador/cla_monthly.py:451-453` |

**Evidencia:**

```python
# cla_monthly.py:451-453
with pd.ExcelWriter(xlsx_name, engine="xlsxwriter") as writer:
    for sheet_name, df in dfs_pandas.items():
        df.to_excel(writer, sheet_name=sheet_name, index=True)
```

**Por qué importa:**
Los datos provienen de fuentes externas (CMF y El Mercurio). Si un nombre de fondo contiene `=CMD|'/C calc'!A0` o `=HYPERLINK("http://evil.com","Click")`, este valor se escribe directamente en las celdas Excel. Cuando un usuario abre el archivo, Excel puede ejecutar la fórmula, resultando potencialmente en ejecución de código remoto.

**Vector de ataque:**
Un fondo registrado en El Mercurio con nombre malicioso se propagaría a través de `elmer.py` → `merge.py` → `cla_monthly.py` → archivo `.xlsx` → víctima.

**Remediación:**

```python
# Después de crear el ExcelWriter, desactivar fórmulas:
with pd.ExcelWriter(xlsx_name, engine="xlsxwriter") as writer:
    writer.book.strings_to_formulas = False
    writer.book.strings_to_urls = False
    # ... resto del código
```

---

### 4. Sin validación de respuestas HTTP de El Mercurio

| Campo | Valor |
|-------|-------|
| **Severidad** | Media |
| **CWE** | CWE-20 (Improper Input Validation) |
| **Archivo** | `comparador/elmer.py:75-103` |

**Evidencia:**

```python
# elmer.py:86-103
url = ELMER_URL_BASE + str(category_id)
response = requests.get(url)  # Sin timeout, sin validación de status
try:
    datos = response.json()
    datos["num_categoria"] = category_id
except JSONDecodeError:
    datos = None
return datos
```

Y en `filter_elmer_data` (líneas 118-138):
```python
categoria = datos["categoria"].upper()       # KeyError si falta
rows = datos["rows"]                         # KeyError si falta
new_dict["RUN_FM"] = int(new_dict.pop("RUN"))  # ValueError si no es numérico
new_dict["SERIE"] = new_dict["FONDOFULL"].split("-", 1)[1]  # IndexError si no tiene "-"
```

**Por qué importa:**
- Sin `timeout`: la petición puede bloquear indefinidamente el proceso
- Sin `raise_for_status()`: un 500 o 403 se procesa como datos válidos
- Sin validación de estructura: claves faltantes provocan crash no controlado
- `int()` sin try/except: un RUN no numérico detiene todo el pipeline

**Remediación:**

```python
def get_elmer_data(category_id: int, verbose: bool = False) -> dict | None:
    url = ELMER_URL_BASE + str(category_id)
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        datos = response.json()
        if "rows" not in datos or "categoria" not in datos:
            return None
        datos["num_categoria"] = category_id
        return datos
    except (requests.RequestException, JSONDecodeError, KeyError):
        if verbose:
            print(f"Error al obtener categoría {category_id}")
        return None
```

---

### 5. Condición de carrera en archivo temporal de CAPTCHA

| Campo | Valor |
|-------|-------|
| **Severidad** | Media |
| **CWE** | CWE-362 (Concurrent Execution using Shared Resource with Improper Synchronization) |
| **Archivo** | `cartolas/config.py:60-61`, `cartolas/download.py:69-72` |

**Evidencia:**

```python
# config.py:60-61
TEMP_FILE_NAME = generate_hash_image_name()  # Se genera UNA vez al importar el módulo
TEMP_FILE_PWD = TEMP_FOLDER / TEMP_FILE_NAME

# download.py:69-72
with open(temp_file_path, "wb") as temp_file:
    temp_file.write(bytearray(image_data))
prediction = predict(temp_file_path)  # Lee el mismo archivo global
```

**Por qué importa:**
`TEMP_FILE_PWD` se genera una sola vez cuando se importa `config.py`. Si dos procesos importan el mismo módulo (e.g., dos instancias de `actualiza_parquet.py`), comparten la misma ruta de archivo temporal. El proceso A escribe su CAPTCHA, el proceso B lo sobreescribe antes de que A lo lea, y A resuelve el CAPTCHA equivocado.

**Nota:** En la práctica actual esto es poco probable porque el script se ejecuta secuencialmente, pero el diseño es frágil.

**Remediación:**

```python
# En download.py, usar tempfile en lugar de archivo global
import tempfile

def get_cartola_from_cmf(...):
    # ...
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(bytearray(image_data))
        temp_path = Path(tmp.name)
    try:
        prediction = predict(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)
```

---

### 6. Apilamiento de decoradores de retry con tiempo de espera excesivo

| Campo | Valor |
|-------|-------|
| **Severidad** | Media |
| **CWE** | CWE-400 (Uncontrolled Resource Consumption) |
| **Archivo** | `cartolas/download.py:29-30` |

**Evidencia:**

```python
# download.py:29-30
@exp_retry_function   # 12 intentos, backoff exponencial: 2^1 + 2^2 + ... + 2^12 = 8190 seg
@retry_function       # 10 intentos, delay fijo de 10 seg = 100 seg por ciclo
def get_cartola_from_cmf(...):
```

**Por qué importa:**
Los decoradores están anidados: `exp_retry_function` envuelve `retry_function` que envuelve la función real. Cada intento del decorador externo ejecuta **todos** los 10 intentos del decorador interno. En el peor caso: 12 x (10 x 10s) + (2 + 4 + ... + 4096)s = **~12,000 + 8,190 = ~20,190 segundos (~5.6 horas)** de espera antes de fallar definitivamente.

Si la CMF está caída, el proceso queda colgado horas sin producir ningún resultado útil.

**Remediación:**

```python
# Usar un solo decorador con backoff exponencial y tope
@exp_retry_function  # Solo este, con max_attempts=5
def get_cartola_from_cmf(...):
```

O bien, reducir `max_attempts` en ambos decoradores para que el tiempo total sea razonable.

---

### 7. Overflow potencial de UInt16 en RUN_FM

| Campo | Valor |
|-------|-------|
| **Severidad** | Media |
| **CWE** | CWE-190 (Integer Overflow or Wraparound) |
| **Archivo** | `cartolas/config.py:80` |

**Evidencia:**

```python
# config.py:80
"RUN_FM": pl.UInt16,  # OJO QUE ES HASTA 65.535
```

**Por qué importa:**
El propio código incluye un comentario de advertencia ("OJO"). Si la CMF asigna un RUN_FM > 65,535, Polars lanzará un error de overflow durante la carga del CSV. Actualmente los RUN van hasta ~10,000, pero el campo fue diseñado para crecer. Un overflow silencioso (en versiones anteriores de Polars) podría mapear un fondo a otro RUN_FM diferente, corrompiendo todos los joins y rankings.

**Remediación:**

```python
"RUN_FM": pl.UInt32,  # Soporta hasta 4,294,967,295
```

---

### 8. Inyección JavaScript en formulario CMF

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-79 (Cross-site Scripting) |
| **Archivo** | `cartolas/download.py:81-82` |

**Evidencia:**

```python
# download.py:81-82
page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
page.evaluate(f"document.querySelector('#txt_termino').value = '{end_date}';")
```

**Por qué importa:**
Las fechas se interpolan directamente en una cadena JavaScript sin escapar. Aunque en la práctica `start_date` y `end_date` provienen de `format_date_cmf()` que las convierte a strings de fecha, el patrón es peligroso. Si alguien extendiera la función para aceptar input de usuario, sería vulnerable a inyección JS.

**Remediación:**

```python
# Usar Playwright locators en lugar de evaluate
page.locator('#txt_inicio').fill(str(start_date))
page.locator('#txt_termino').fill(str(end_date))
```

---

### 9. Credenciales BCCh cargadas al momento de importar el módulo

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-798 (Use of Hard-coded Credentials) |
| **Archivo** | `eco/bcentral.py:18-32` |

**Evidencia:**

```python
# bcentral.py:18-32
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)  # Login al importar
```

**Por qué importa:**
- El login a la API del BCCh se ejecuta como efecto secundario del `import`. Cualquier módulo que importe `bcentral.py` (directa o transitivamente) gatilla una conexión de red y autenticación, incluso si no la necesita.
- Si `.env` no existe o le faltan las claves, el `import` falla con `KeyError`, no con un mensaje descriptivo.
- Las credenciales quedan como variables globales de módulo, accesibles desde cualquier parte del código.

**Nota:** El archivo `.env` está correctamente en `.gitignore` y nunca fue committed al repositorio. Las credenciales NO están expuestas en el historial de git.

**Remediación:**

```python
# Lazy initialization
_bcch_client = None

def get_bcch_client():
    global _bcch_client
    if _bcch_client is None:
        env = dotenv_values(".env")
        _bcch_client = bcchapi.Siete(
            usr=env.get("BCCH_USER", ""),
            pwd=env.get("BCCH_PASS", "")
        )
    return _bcch_client
```

---

## Score de riesgo: 5.5 / 10

**Justificación:**
- No hay endpoints web expuestos ni autenticación de usuarios, lo cual reduce mucho la superficie de ataque.
- Las fuentes de datos externas (CMF, El Mercurio) son semi-confiables pero sin validación.
- El impacto principal es **integridad de datos financieros**: cálculos incorrectos que afectan reportes y comparaciones de fondos.
- El riesgo de inyección Excel es real pero requiere compromiso de una fuente upstream.

---

## Top 5 remediaciones prioritarias

| # | Hallazgo | Esfuerzo | Impacto |
|---|----------|----------|---------|
| 1 | Dejar de enmascarar tipo de cambio faltante con `fill_null(1)` | Bajo | Alto — elimina cálculos financieros incorrectos |
| 2 | Desactivar fórmulas en escritura Excel (`strings_to_formulas = False`) | Bajo | Alto — cierra vector de RCE via fórmulas |
| 3 | Validar respuestas de El Mercurio (timeout, status, estructura) | Bajo | Medio — previene crashes silenciosos |
| 4 | Cambiar `RUN_FM` de `UInt16` a `UInt32` | Trivial | Medio — previene overflow futuro |
| 5 | Usar un solo decorador de retry con tope razonable | Bajo | Medio — evita bloqueos de horas |

---

## Checklist

| Verificación | Estado | Notas |
|---|---|---|
| **Condiciones de carrera** | FAIL | Archivo temporal CAPTCHA compartido (#5) |
| **Manejo de solicitudes concurrentes** | N/A | No hay servidor web ni endpoints |
| **Prevención de doble gasto** | N/A | No hay transacciones monetarias |
| **Gestión de inventario** | N/A | No aplica |
| **Validación de precios solo en cliente** | N/A | No hay interfaz cliente/servidor |
| **Abuso de descuentos/cupones** | N/A | No aplica |
| **Manipulación de moneda** | FAIL | Tipo de cambio silenciosamente defaulteado a 1 (#1) |
| **Salto de pasos de validación** | FAIL | Sin validación de datos El Mercurio (#4) |
| **Manipulación de estado** | PASS | Los LazyFrames son inmutables por diseño |
| **Bypass de proceso de aprobación** | N/A | No hay flujo de aprobación |
| **TOCTOU** | FAIL | Archivo temporal (#5), aunque riesgo práctico bajo |
| **Bypass de expiración** | N/A | No hay tokens ni sesiones |
| **Manipulación de timezone** | PASS | Usa `date` nativo de Python, sin TZ |
| **Overflow de enteros** | FAIL | `RUN_FM` como UInt16 (#7) |
| **Errores de cálculo** | FAIL | División por cero enmascarada (#2), defaults silenciosos (#1) |
| **Manejo de valores negativos** | PASS | Los valores financieros pueden ser negativos legítimamente |
