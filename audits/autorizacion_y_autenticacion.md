# Auditoría de Autorización y Autenticación

**Fecha:** 2026-03-16
**Alcance:** Todos los archivos Python del proyecto `cartolas`
**Auditor:** Claude Code

---

## Resumen Ejecutivo

Este proyecto es una **herramienta CLI de procesamiento batch** para análisis de fondos mutuos chilenos. **No es una aplicación web** — no expone endpoints HTTP, no tiene servidor, no tiene rutas, no tiene usuarios ni roles.

El proyecto actúa exclusivamente como **cliente HTTP** hacia APIs externas (CMF, Banco Central, El Mercurio Inversiones). Por esta razón, la mayoría de los controles de autorización solicitados (BOLA/IDOR, RBAC, JWT, CORS, CSRF, etc.) **no son aplicables**.

Sin embargo, existen hallazgos relevantes de seguridad relacionados con el manejo de credenciales y la comunicación con servicios externos.

**Score de riesgo global: 4/10** (riesgo moderado-bajo, concentrado en gestión de secretos)

---

## Hallazgos

### 1. Credenciales hardcodeadas en tiempo de importación

| Campo | Detalle |
|-------|---------|
| **Severidad** | Alta |
| **CWE** | CWE-798 (Use of Hard-coded Credentials), CWE-522 (Insufficiently Protected Credentials) |
| **Archivo** | `eco/bcentral.py:18-25,32` |
| **Evidencia** | Las credenciales BCCh se cargan y el login se ejecuta **a nivel de módulo**, no bajo demanda |

```python
# eco/bcentral.py:18-32
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)  # Login inmediato al importar
```

**Por qué importa:** Cualquier `import eco.bcentral` (incluso transitivo) ejecuta el login al BCCh. Si `.env` no existe, el módulo falla con `KeyError` sin mensaje útil. Las credenciales quedan como constantes globales accesibles desde cualquier parte del código.

**Remediación:**
```python
# eco/bcentral.py - Propuesta
import functools

@functools.cache
def _get_bcch_client():
    env_variables = dotenv_values(".env")
    try:
        return bcchapi.Siete(
            usr=env_variables["BCCH_USER"],
            pwd=env_variables["BCCH_PASS"],
        )
    except KeyError as e:
        raise RuntimeError(f"Falta variable de entorno: {e}. Verifica .env") from e
```

---

### 2. Archivo `.env` con credenciales sensibles sin protección adicional

| Campo | Detalle |
|-------|---------|
| **Severidad** | Media |
| **CWE** | CWE-256 (Plaintext Storage of a Password) |
| **Archivo** | `.env` (raíz del proyecto) |
| **Evidencia** | Contiene `BCCH_USER`, `BCCH_PASS`, `SENDGRID_API`, `CONNECTION_STRING` en texto plano |

**Por qué importa:** Aunque `.env` está en `.gitignore` (línea 143) y no se encontró en el historial de git, las credenciales incluyen una API key de SendGrid, credenciales del BCCh y una connection string de Azure Storage. Si el repositorio se clona o el archivo se comparte, quedan expuestas.

**Remediación:**
- Rotar las credenciales actuales (especialmente `SENDGRID_API` y `CONNECTION_STRING`)
- Considerar un gestor de secretos o variables de entorno del sistema en lugar de `.env`
- Agregar un `.env.example` con las claves sin valores como documentación

---

### 3. Inyección potencial vía JavaScript en Playwright

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-94 (Code Injection) |
| **Archivo** | `cartolas/download.py:81-82` |
| **Evidencia** | Interpolación directa de variables en `page.evaluate()` |

```python
# cartolas/download.py:81-82
page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
page.evaluate(f"document.querySelector('#txt_termino').value = '{end_date}';")
```

**Por qué importa:** Si `start_date` o `end_date` contuvieran caracteres especiales (comillas simples, etc.), podrían inyectar JavaScript en el contexto del navegador Playwright. En la práctica, las fechas provienen de `format_date_cmf()` que las formatea como strings seguros, pero el patrón es frágil.

**Remediación:**
```python
# Usar argumentos parametrizados de Playwright
page.evaluate("(date) => document.querySelector('#txt_inicio').value = date", start_date)
page.evaluate("(date) => document.querySelector('#txt_termino').value = date", end_date)
```

---

### 4. Respuestas HTTP externas sin validación

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-20 (Improper Input Validation) |
| **Archivos** | `comparador/elmer.py:86-103`, `cartolas/fund_identifica.py` |
| **Evidencia** | No se valida status code HTTP ni estructura de respuesta |

```python
# comparador/elmer.py:89-93
response = requests.get(url)
try:
    datos = response.json()  # No verifica response.status_code
```

**Por qué importa:** Si la API externa retorna un error HTTP (500, 403) o una respuesta con estructura inesperada, el código puede fallar de formas impredecibles o procesar datos corruptos silenciosamente.

**Remediación:**
```python
response = requests.get(url)
response.raise_for_status()  # Lanza HTTPError para 4xx/5xx
datos = response.json()
```

---

### 5. Nombre de archivo descargado controlado por servidor externo

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-22 (Path Traversal) |
| **Archivo** | `cartolas/download.py:112` |
| **Evidencia** | `download.suggested_filename` se usa directamente en la ruta de guardado |

```python
download_path = cartolas_txt_folder / download.suggested_filename
download.save_as(download_path)
```

**Por qué importa:** Si el servidor CMF retornara un nombre de archivo con `../` (path traversal), el archivo podría guardarse fuera de la carpeta esperada. El riesgo es bajo porque proviene de la CMF (fuente confiable) y `pathlib` mitiga parcialmente esto.

**Remediación:**
```python
safe_name = Path(download.suggested_filename).name  # Solo el nombre, sin directorios
download_path = cartolas_txt_folder / safe_name
```

---

## Checklist de Controles

| Control | Estado | Notas |
|---------|--------|-------|
| Broken Object Level Authorization (BOLA/IDOR) | N/A | No hay endpoints ni objetos con dueño |
| Broken Function Level Authorization | N/A | No hay rutas ni roles |
| Missing authorization on sensitive endpoints | N/A | No hay endpoints |
| RBAC implementation | N/A | No hay usuarios ni roles |
| Privilege escalation | N/A | No hay sistema de privilegios |
| JWT token validation | N/A | No se usa JWT |
| API token scope checking | N/A | No hay tokens propios |
| Multi-tenant isolation | N/A | No es multi-tenant |
| Bulk endpoint protections | N/A | No hay endpoints bulk |
| Field-level authorization | N/A | No hay API propia |
| Error handling & resource enumeration | N/A | No hay API propia |
| Middleware ordering | N/A | No hay middleware |
| CORS & CSRF | N/A | No hay servidor web |
| Open redirect protections | N/A | No hay redirecciones web |
| Fallback/debug routes | N/A | No hay rutas |
| Credenciales en código fuente | **FAIL** | Ver hallazgo #1 y #2 |
| Validación de inputs externos | **FAIL** | Ver hallazgos #3, #4, #5 |
| `.env` excluido de git | **PASS** | `.gitignore` línea 143 |
| Credenciales en historial git | **PASS** | No encontradas |

---

## Top 5 Acciones Prioritarias

1. **Refactorizar `eco/bcentral.py`** — Diferir la carga de credenciales y login al momento de uso (lazy init). Manejar `KeyError` con mensaje claro. (Hallazgo #1)

2. **Rotar credenciales** — Regenerar `SENDGRID_API`, `BCCH_PASS` y `CONNECTION_STRING`. Aunque no están en git, es buena práctica rotarlas periódicamente. (Hallazgo #2)

3. **Parametrizar `page.evaluate()`** — Usar argumentos de Playwright en lugar de interpolación f-string. (Hallazgo #3)

4. **Validar respuestas HTTP** — Agregar `response.raise_for_status()` en `elmer.py` y `fund_identifica.py`. (Hallazgo #4)

5. **Sanitizar nombres de archivo descargados** — Usar `Path.name` para extraer solo el nombre sin componentes de directorio. (Hallazgo #5)

---

## Nota Final

La gran mayoría de los controles de la checklist original (BOLA, RBAC, JWT, CORS, middleware, etc.) **no son aplicables** a este proyecto porque no es una aplicación web ni expone APIs. Si en el futuro se agregara un servidor web (ej: FastAPI para servir reportes), sería necesario realizar una auditoría completa de estos controles.
