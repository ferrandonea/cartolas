# RESUMEN DE OBSERVACIONES — CARTOLAS

**Fecha:** 16 de marzo de 2026
**Contexto:** CLI/batch tool personal para análisis de fondos mutuos chilenos. No es app web pública.

---

## 1. Resumen General

Este proyecto tiene buen diseño de pipeline (Polars lazy, funciones puras, config centralizada), pero arrastra problemas concretos que afectan la **confiabilidad de los datos** y la **mantenibilidad del código**.

Los problemas se agrupan en 4 categorías, ordenadas por impacto real:

| Categoría | Calificación | Cantidad | Impacto real |
|-----------|-------------|----------|-------------|
| **Bugs activos** | **Crítico** | 2 | Datos incorrectos en producción ahora mismo |
| **Seguridad** | **Alto** | 5 | Credenciales expuestas, inyección posible |
| **Resiliencia** | **Medio** | 5 | El pipeline se cae o se cuelga ante fallos externos |
| **Calidad de código** | **Bajo** | 8 | Mantenibilidad, duplicación, naming |

---

## 2. CRÍTICO — Bugs Activos (afectan datos ahora)

### BUG-01: Fechas hardcodeadas congelan el análisis CLA

**Archivo:** `comparador/tablas.py:49-58`

Esto es lo más urgente. Las fechas de comparación 1M, 3M, 6M, etc. están congeladas en valores de 2024/2025. El análisis CLA mensual **produce datos incorrectos hoy**.

```python
# CÓDIGO ACTUAL (líneas 49-58) — INCORRECTO
selected_dates = {
    "OM": max_date,
    "1M": date(2025, 2, 28),   # ← congelado
    "3M": date(2024, 12, 31),  # ← congelado
    "6M": date(2024, 9, 30),   # ← congelado
    "1Y": date(2024, 3, 31),   # ← congelado
    "3Y": date(2022, 3, 31),   # ← congelado
    "5Y": date(2020, 3, 31),   # ← congelado
    "YTD": date(2024, 12, 31), # ← congelado
}
```

**Fix:** Descomentar el código dinámico que ya existe (líneas 60-68) y agregar YTD:

```python
# FIX — usar funciones dinámicas
from utiles.fechas import last_day_n_months_ago, last_day_n_months_ago_by_year

selected_dates = {
    "OM": max_date,
    "1M": last_day_n_months_ago(max_date, 1),
    "3M": last_day_n_months_ago(max_date, 3),
    "6M": last_day_n_months_ago(max_date, 6),
    "1Y": last_day_n_months_ago_by_year(max_date, 1),
    "3Y": last_day_n_months_ago_by_year(max_date, 3),
    "5Y": last_day_n_months_ago_by_year(max_date, 5),
    "YTD": date(max_date.year - 1, 12, 31),
}
```

---

### BUG-02: NameError en `update_bcch_parquet()` — crash si no existe el parquet

**Archivo:** `eco/bcentral.py:206-227`

Si `bcch.parquet` no existe, el `except FileNotFoundError` captura el error pero `df` queda sin definir. En la línea 220, `return df` lanza `UnboundLocalError`.

```python
# CÓDIGO ACTUAL (líneas 206-227)
def update_bcch_parquet(path: str = PARQUET_PATH) -> pl.LazyFrame:
    try:
        df = load_bcch_from_parquet()          # ← df se define aquí
        last_date = get_last_date_from_parquet(df)
    except FileNotFoundError:
        last_date = datetime(1970, 1, 1).date()
        print("BCCH: No se encontró el archivo de datos del BCCh")
        # ← df NO se define en este branch

    if last_date >= LAST_DATE.date():
        print("BCCH: No hay datos nuevos del BCCh")
        return df   # ← BOOM: UnboundLocalError si vino del except
    else:
        # ...
```

**Fix:**

```python
def update_bcch_parquet(path: str = PARQUET_PATH) -> pl.LazyFrame:
    df = None  # ← inicializar
    try:
        df = load_bcch_from_parquet()
        last_date = get_last_date_from_parquet(df)
    except FileNotFoundError:
        last_date = datetime(1970, 1, 1).date()
        print("BCCH: No se encontró el archivo de datos del BCCh")

    if df is not None and last_date >= LAST_DATE.date():
        print("BCCH: No hay datos nuevos del BCCh")
        return df
    else:
        print(f"BCCH: Última fecha en el archivo: {last_date}")
        print("BCCH: Actualizando datos del BCCh")
        df = baja_bcch_as_polars(as_lazy=True)
        df.collect().write_parquet(path)
    return df
```

---

## 3. ALTO — Seguridad

### SEG-01: Credenciales cargadas al importar módulo

**Archivo:** `eco/bcentral.py:18-32`

Cualquier `import eco.bcentral` (incluso indirecto) ejecuta inmediatamente:
1. Lee `.env`
2. Extrae usuario/contraseña
3. Hace login al BCCh

Si `.env` no existe → `KeyError` críptico. Si existe → credenciales en memoria global todo el tiempo.

```python
# CÓDIGO ACTUAL (líneas 18-32) — se ejecuta al importar
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)
```

**Fix:**

```python
# FIX — lazy initialization
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_bcch_client():
    """Crea cliente BCCh solo cuando se necesita."""
    env = dotenv_values(".env")
    user = env.get("BCCH_USER")
    pwd = env.get("BCCH_PASS")
    if not user or not pwd:
        raise EnvironmentError(
            "Variables BCCH_USER y BCCH_PASS requeridas en .env. "
            "Ver .env.example para referencia."
        )
    return bcchapi.Siete(usr=user, pwd=pwd)

# Luego reemplazar BCCh.cuadro(...) por _get_bcch_client().cuadro(...)
# en baja_datos_bcch() (líneas 78, 80)
```

---

### SEG-02: Inyección JavaScript en Playwright

**Archivo:** `cartolas/download.py:81-82`

Fechas interpoladas directamente en JavaScript. Aunque las fechas vienen de código interno, el patrón es peligroso.

```python
# CÓDIGO ACTUAL (líneas 81-82)
page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
page.evaluate(f"document.querySelector('#txt_termino').value = '{end_date}';")
```

**Fix — usar API nativa de Playwright (más simple además):**

```python
page.locator('#txt_inicio').fill(start_date)
page.locator('#txt_termino').fill(end_date)
```

---

### SEG-03: HTTP requests sin timeout

**Archivos:** `comparador/elmer.py:89`, `cartolas/fund_identifica.py:26`

Si el servidor no responde, el proceso se cuelga indefinidamente. Sin timeout = sin control.

```python
# CÓDIGO ACTUAL
# elmer.py:89
response = requests.get(url)

# fund_identifica.py:26
response = requests.get(url, headers=headers)
```

**Fix:**

```python
# elmer.py:89
response = requests.get(url, timeout=30)

# fund_identifica.py:26
response = requests.get(url, headers=headers, timeout=30)
```

---

### SEG-04: Path traversal en nombre de archivo descargado

**Archivo:** `cartolas/download.py:112`

`download.suggested_filename` viene del servidor CMF. Si el servidor fuera comprometido, podría sugerir nombres como `../../algo`.

```python
# CÓDIGO ACTUAL (línea 112)
download_path = cartolas_txt_folder / download.suggested_filename
```

**Fix:**

```python
from pathlib import PurePosixPath

safe_name = PurePosixPath(download.suggested_filename).name
download_path = cartolas_txt_folder / safe_name
```

---

### SEG-05: Email personal hardcodeado en código versionado

**Archivo:** `cartolas/config.py:116-120`

```python
# CÓDIGO ACTUAL
SENDER_MAIL, SENDER_NAME, TO_EMAILS = (
    "francisco@soyfocus.com",
    "Francisco",
    ["francisco@soyfocus.com"],
)
```

**Fix:** Mover a `.env`:

```python
env = dotenv_values(".env")
SENDER_MAIL = env.get("SENDER_MAIL", "")
SENDER_NAME = env.get("SENDER_NAME", "")
TO_EMAILS = [env.get("TO_EMAIL", "")]
```

---

## 4. MEDIO — Resiliencia

### RES-01: Doble decorador de retry = hasta 120 intentos

**Archivo:** `cartolas/download.py:29-30`

`@exp_retry_function` (12 intentos) envuelve `@retry_function` (10 intentos) = 120 reintentos posibles. Con backoff exponencial, puede esperar **más de 2 horas** antes de fallar.

```python
# CÓDIGO ACTUAL (líneas 29-30)
@exp_retry_function
@retry_function
def get_cartola_from_cmf(...):
```

**Fix — un solo decorador con tope razonable:**

```python
@exp_retry_function  # 12 intentos con backoff es suficiente
def get_cartola_from_cmf(...):
```

Y en `utiles/decorators.py`, reducir `max_attempts` default de 12 a 5 (máximo ~62 segundos de espera total).

---

### RES-02: `fill_null(1)` enmascara tipo de cambio faltante

**Archivo:** `comparador/merge.py:77`

Si no hay dato de tipo de cambio para una fecha, se asume 1.0 (es decir, 1 USD = 1 CLP). Esto produce rentabilidades totalmente incorrectas para fondos en USD/EUR.

```python
# CÓDIGO ACTUAL (línea 77)
pl.col("TIPO_CAMBIO").fill_null(1)
```

**Fix — propagar el null para que se note:**

```python
# Opción A: forward fill (usar último tipo de cambio conocido)
pl.col("TIPO_CAMBIO").forward_fill()

# Opción B: dejar null y filtrar después
# (no usar fill_null(1) porque 1 USD ≠ 1 CLP)
```

---

### RES-03: `fill_nan(1)` oculta divisiones por cero en rentabilidad

**Archivo:** `comparador/merge.py:117-126`

El primer día de un fondo no tiene `VALOR_CUOTA_ANTERIOR_PESOS`, produciendo `null/0 → NaN → 1.0`. Esto es correcto para el primer día, pero también oculta datos corruptos reales.

```python
# CÓDIGO ACTUAL (líneas 117-126)
(
    pl.col("VALOR_CUOTA_PESOS_AJUSTADO")
    / pl.col("VALOR_CUOTA_ANTERIOR_PESOS")
).fill_nan(1).fill_null(1)
```

**Fix — ser explícito sobre cuándo es 1.0:**

```python
pl.when(pl.col("VALOR_CUOTA_ANTERIOR_PESOS").is_null() | (pl.col("VALOR_CUOTA_ANTERIOR_PESOS") == 0))
  .then(1.0)  # Primer día del fondo: rentabilidad neutra
  .otherwise(
      pl.col("VALOR_CUOTA_PESOS_AJUSTADO") / pl.col("VALOR_CUOTA_ANTERIOR_PESOS")
  )
  .alias("RENTABILIDAD_DIARIA_PESOS")
```

---

### RES-04: Excepciones genéricas pierden el tipo original

**Archivo:** `utiles/decorators.py:35-42, 70-79`

Los decoradores de retry capturan `Exception` (todo) y al agotar reintentos lanzan una `Exception` genérica nueva, perdiendo el tipo y traceback original.

```python
# CÓDIGO ACTUAL (líneas 40-42)
raise Exception(
    f"No se pudo ejecutar {func.__name__} después de {max_attempts} intentos"
)
```

**Fix:**

```python
# Guardar última excepción y re-lanzarla
def wrapper(*args, **kwargs) -> T:
    attempts = 0
    last_exception = None
    while attempts < max_attempts:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            attempts += 1
            print(f"Error en {func.__name__}: {e}")
            print(f"Intento {attempts}/{max_attempts}. Esperando {delay} segundos")
            time.sleep(delay)
    raise last_exception  # Mantiene tipo y traceback original
```

Mismo cambio para `exp_retry_function` (líneas 70-79).

---

### RES-05: Sin validación de respuesta HTTP de El Mercurio

**Archivo:** `comparador/elmer.py:89-101`

No se verifica status code. Un 500 o 403 se procesa como si fuera respuesta válida.

```python
# CÓDIGO ACTUAL (líneas 89-101)
response = requests.get(url)
try:
    datos = response.json()
```

**Fix:**

```python
response = requests.get(url, timeout=30)
if response.status_code != 200:
    print(f"HTTP {response.status_code} para categoría {category_id}") if verbose else None
    return None
try:
    datos = response.json()
```

---

## 5. BAJO — Calidad de Código

Estos no son urgentes, pero mejorarlos hará el código más fácil de mantener y extender.

### CAL-01: Importación circular `config.py` ↔ `file_tools.py`

**Archivos:** `cartolas/config.py:55`, `utiles/file_tools.py:53`

Ambos archivos tienen imports a mitad del archivo con `# noqa: E402` para silenciar el linter. Esto indica un problema de diseño.

**Fix:** Mover `generate_hash_image_name` a un módulo que no dependa de `config.py`, o simplemente generar el nombre en `download.py` cuando se necesita (no en config al importar).

---

### CAL-02: Función muerta `cmf_to_pl()`

**Archivo:** `cartolas/fund_identifica.py:31-63`

`cmf_to_pl()` hace lo mismo que `cmf_text_to_df()` pero no retorna nada (solo imprime schema). Es dead code.

**Fix:** Eliminar `cmf_to_pl()` completa. También eliminar el dict `columnas` sin usar en `download_fund_identification()` (líneas 127-139).

---

### CAL-03: Constantes SoyFocus en 4 lugares distintos

**Archivos:**
- `cartolas/config.py:105` → `{9809: "MODERADO", 9810: "CONSERVADOR", 9811: "ARRIESGADO"}`
- `comparador/merge.py:257-262` → `{"BALANCEADO CONSERVADOR": 9810, ...}`
- `comparador/cla_monthly.py` → mapeo de nombres para Excel
- `resumen_apv.py` → lista de RUNs

**Fix:** Centralizar en `config.py` con una sola fuente de verdad:

```python
# config.py
SOYFOCUS_FUNDS = {
    9809: {"nombre": "MODERADO", "categoria": "BALANCEADO MODERADO"},
    9810: {"nombre": "CONSERVADOR", "categoria": "BALANCEADO CONSERVADOR"},
    9811: {"nombre": "ARRIESGADO", "categoria": "BALANCEADO AGRESIVO"},
}

# Derivar vistas
SOYFOCUS_CATEGORY_MAPPING = {v["categoria"]: k for k, v in SOYFOCUS_FUNDS.items()}
SOYFOCUS_RUNS = list(SOYFOCUS_FUNDS.keys())
```

---

### CAL-04: Duplicación `update.py` vs `update_by_year.py`

~80% del código es idéntico. Diferencia: uno procesa todo junto, otro por año.

**Fix:** Extraer pipeline común a función reutilizable con parámetro de granularidad.

---

### CAL-05: `FECHA_MAXIMA` y `DIAS_ATRAS` evaluados al importar

**Archivo:** `cartolas/config.py:67-68`

```python
DIAS_ATRAS = 1 if datetime.now().hour > 10 else 2
FECHA_MAXIMA = datetime.now().date() - timedelta(days=DIAS_ATRAS)
```

Si el módulo se importa a las 9am pero se usa a las 3pm, la fecha es incorrecta.

**Fix:** Convertir a función:

```python
def get_fecha_maxima() -> date:
    dias_atras = 1 if datetime.now().hour > 10 else 2
    return datetime.now().date() - timedelta(days=dias_atras)
```

---

### CAL-06: `random` en vez de `secrets` para hash de archivos temporales

**Archivo:** `utiles/file_tools.py:29-30`

```python
random_string = "".join(random.choices(string.ascii_letters + string.digits, k=length))
```

**Fix:** `secrets.token_hex(length)` — más simple y criptográficamente seguro.

---

### CAL-07: Falta `@wraps` en decoradores de retry

**Archivo:** `utiles/decorators.py:30, 65`

Los wrappers de `retry_function` y `exp_retry_function` no usan `@wraps(func)`, lo que hace que `func.__name__` reporte "wrapper" en vez del nombre real. Nota: `timer` sí lo tiene (línea 108).

**Fix:** Agregar `@wraps(func)` antes de `def wrapper(...)` en ambos decoradores.

---

### CAL-08: Parámetro `sorted` sombrea built-in de Python

**Archivos:** `cartolas/read.py:8`, `cartolas/soyfocus.py:28`

**Fix:** Renombrar a `pre_sorted` o `is_sorted`.

---

## 6. IRRELEVANTE para este proyecto

Las auditorías anteriores mencionan estos puntos que **no aplican o no valen la pena** dado que es un CLI personal:

| Observación | Por qué no aplica |
|-------------|-------------------|
| Cifrado de datos en reposo | Es un CLI local; depende de FileVault del OS |
| Rate limiting en El Mercurio | 30 requests con 1s de sleep es razonable |
| Checksums de integridad en Parquet | Parquet ya tiene checksums internos |
| Formula injection en Excel | Requiere que El Mercurio sea comprometido Y macros habilitados |
| Política formal de backup | Es un proyecto personal, no enterprise |
| GDPR/PCI DSS/SOC 2 | No maneja datos personales ni pagos |

---

## 7. Plan de Acción Sugerido

### Sesión 1 (~30 min): Bugs críticos
- [ ] Descomentar fechas dinámicas en `tablas.py` (BUG-01)
- [ ] Inicializar `df = None` en `bcentral.py` (BUG-02)
- [ ] Cambiar `page.evaluate(f"...")` por `page.locator().fill()` en `download.py` (SEG-02)

### Sesión 2 (~1 hora): Seguridad y resiliencia
- [ ] Lazy init de BCCh client (SEG-01)
- [ ] Agregar `timeout=30` a requests (SEG-03)
- [ ] Sanitizar `download.suggested_filename` (SEG-04)
- [ ] Mover email a `.env` (SEG-05)
- [ ] Quitar un decorador de retry en `download.py` (RES-01)

### Sesión 3 (~1 hora): Integridad de datos
- [ ] Cambiar `fill_null(1)` en tipo de cambio (RES-02)
- [ ] Cambiar `fill_nan(1)` en rentabilidad (RES-03)
- [ ] Re-lanzar excepción original en decoradores (RES-04)
- [ ] Validar status code HTTP (RES-05)

### Sesión 4 (cuando haya tiempo): Limpieza
- [ ] Resolver import circular (CAL-01)
- [ ] Eliminar `cmf_to_pl()` (CAL-02)
- [ ] Centralizar constantes SoyFocus (CAL-03)
- [ ] Convertir `FECHA_MAXIMA` a función (CAL-05)

---

*Generado por Claude Code (Opus 4.6) — 16 de marzo de 2026*
*Basado en 21 auditorías previas + análisis directo del código fuente*
