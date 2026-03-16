# Auditoría de Estructura del Proyecto - Cartolas

**Fecha:** 2026-03-16
**Alcance:** Estructura completa del proyecto, puntos de entrada, integraciones, manejo de secretos, dependencias y superficie de ataque.
**Puntuación de riesgo global: 7/10**

---

## Hallazgos

### 1. Credenciales expuestas en `.env` versionado

| Campo | Valor |
|-------|-------|
| **Severidad** | CRITICAL |
| **CWE** | CWE-798 (Use of Hard-coded Credentials), CWE-540 (Inclusion of Sensitive Information in Source Code) |
| **Evidencia** | `.env` lineas 1-16 |
| **Archivos afectados** | `.env`, `eco/bcentral.py:18-32`, `cartolas/config.py:116-120` |

**Por que importa:** El archivo `.env` contiene en texto plano: clave API de SendGrid, credenciales BCCh (RUN + password), connection string de Azure Storage con account key completa, y correos. Aunque `.gitignore` lista `.env`, el archivo ya esta trackeado en el repositorio. Cualquier persona con acceso al repo tiene acceso completo a estos servicios.

**Explotabilidad:** Trivial. Clonar el repo y leer `.env`.

**Remediacion:**

```bash
# 1. Rotar TODAS las credenciales inmediatamente
# 2. Eliminar .env del historial de git
git filter-repo --path .env --invert-paths --force
# 3. Asegurar que .env esta en .gitignore (ya lo esta)
# 4. Nunca mas commitear .env
```

**Defensa en profundidad:** Migrar a un secrets manager (Azure KeyVault, AWS Secrets Manager) o al menos variables de entorno del sistema, no archivo `.env`.

---

### 2. Credenciales cargadas en tiempo de importacion del modulo

| Campo | Valor |
|-------|-------|
| **Severidad** | HIGH |
| **CWE** | CWE-522 (Insufficiently Protected Credentials) |
| **Evidencia** | `eco/bcentral.py:18-32` |

**Por que importa:** Las credenciales BCCh se cargan con `dotenv_values(".env")` al importar el modulo, no cuando se necesitan. Esto significa que cualquier `import eco.bcentral` expone las credenciales en memoria durante toda la vida del proceso.

**Remediacion:**

```python
# Antes (bcentral.py linea 18-32):
config = dotenv_values(".env")
BCCH_USER = config["BCCH_USER"]
BCCH_PASS = config["BCCH_PASS"]
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)

# Despues: lazy initialization
_bcch_client = None

def get_bcch_client():
    global _bcch_client
    if _bcch_client is None:
        config = dotenv_values(".env")
        _bcch_client = bcchapi.Siete(
            usr=config["BCCH_USER"], pwd=config["BCCH_PASS"]
        )
    return _bcch_client
```

---

### 3. Dependencia privada via SSH sin pinning de hash

| Campo | Valor |
|-------|-------|
| **Severidad** | MEDIUM |
| **CWE** | CWE-829 (Inclusion of Functionality from Untrusted Control Sphere) |
| **Evidencia** | `pyproject.toml:10` |

**Por que importa:** `captchapass` se instala desde `git+ssh://git@github.com/ferrandonea/captchapass.git` sin version ni hash. Si el repo se compromete, el codigo malicioso se instalaria automaticamente en la proxima `uv sync`.

**Remediacion:**

```toml
# Pinear a un commit especifico
"captchapass @ git+ssh://git@github.com/ferrandonea/captchapass.git@abc1234def5678"
```

---

### 4. Inyeccion JavaScript en Playwright `page.evaluate()`

| Campo | Valor |
|-------|-------|
| **Severidad** | LOW |
| **CWE** | CWE-94 (Improper Control of Generation of Code) |
| **Evidencia** | `cartolas/download.py:81-82` |

**Por que importa:** Se usa f-string para inyectar valores de fecha en `page.evaluate()`:

```python
page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
page.evaluate(f"document.querySelector('#txt_termino').value = '{end_date}';")
```

Si `start_date` o `end_date` contuvieran caracteres maliciosos, se ejecutaria JavaScript arbitrario en el contexto del navegador Playwright. El riesgo es bajo porque las fechas son parametros controlados internamente (formato YYYYMMDD), no input de usuario.

**Remediacion:**

```python
# Usar locator.fill() en vez de evaluate con f-string
page.locator("#txt_inicio").fill(start_date)
page.locator("#txt_termino").fill(end_date)
```

---

### 5. Sin validacion explicita de formato de fechas

| Campo | Valor |
|-------|-------|
| **Severidad** | LOW |
| **CWE** | CWE-20 (Improper Input Validation) |
| **Evidencia** | `utiles/fechas.py`, `cartolas/download.py:124-138` |

**Por que importa:** Las funciones de descarga aceptan fechas como strings sin validar formato. Si se pasa un string malformado, el error se propagaria sin mensaje claro, o peor, podria afectar la inyeccion JavaScript del hallazgo #4.

**Remediacion:**

```python
from datetime import datetime

def validate_date(date_str: str) -> str:
    """Valida formato YYYYMMDD."""
    try:
        datetime.strptime(date_str, "%Y%m%d")
        return date_str
    except ValueError:
        raise ValueError(f"Formato de fecha invalido: {date_str}. Use YYYYMMDD.")
```

---

### 6. User-Agent spoofing en requests a El Mercurio

| Campo | Valor |
|-------|-------|
| **Severidad** | LOW |
| **CWE** | N/A |
| **Evidencia** | `comparador/elmer.py:75-103` |

**Por que importa:** Se usa un User-Agent de navegador para simular trafico humano a la API de El Mercurio Inversiones. No es una vulnerabilidad de seguridad del proyecto, pero podria violar TOS del servicio y resultar en bloqueo de IP.

**Remediacion:** Evaluar si El Mercurio ofrece una API oficial o si el scraping es aceptable bajo sus terminos de uso.

---

### 7. Sin rate limiting en API de El Mercurio

| Campo | Valor |
|-------|-------|
| **Severidad** | LOW |
| **CWE** | CWE-770 (Allocation of Resources Without Limits) |
| **Evidencia** | `comparador/elmer.py:75-103` |

**Por que importa:** Las peticiones a El Mercurio se hacen en un loop secuencial sin delay. Aunque es solo 30 categorias, podria provocar rate limiting o bloqueo del lado del servidor.

**Remediacion:**

```python
import time
# Agregar delay entre requests
time.sleep(0.5)  # 500ms entre peticiones
```

---

### 8. Manejo generico de excepciones en descarga CMF

| Campo | Valor |
|-------|-------|
| **Severidad** | MEDIUM |
| **CWE** | CWE-755 (Improper Handling of Exceptional Conditions) |
| **Evidencia** | `cartolas/download.py:106-120` |

**Por que importa:** Se captura `Exception` generica en el flujo de descarga. Esto puede ocultar errores criticos (como credenciales invalidas o cambios en la estructura del sitio CMF) bajo reintentos silenciosos, desperdiciando hasta 10 intentos x 10 segundos cada uno.

**Remediacion:** Capturar excepciones especificas (`TimeoutError`, `PlaywrightError`) y fallar rapido en errores irrecuperables.

---

### 9. Sin lock file para dependencias

| Campo | Valor |
|-------|-------|
| **Severidad** | MEDIUM |
| **CWE** | CWE-1104 (Use of Unmaintained Third Party Components) |
| **Evidencia** | `.gitignore:113` (uv.lock comentado), ausencia de `uv.lock` en repo |

**Por que importa:** Sin lock file, cada `uv sync` puede instalar versiones diferentes de dependencias, incluyendo versiones con vulnerabilidades conocidas. Las versiones minimas en `pyproject.toml` (ej: `polars>=1.16.0`) permiten cualquier version superior.

**Nota:** No se pudo verificar si `uv.lock` existe localmente pero no esta commiteado. Verificar con `ls -la uv.lock`.

**Remediacion:**

```bash
# Generar y commitear el lock file
uv lock
git add uv.lock
```

---

## Puntos de entrada del proyecto

| Script | Proposito | Servicios externos |
|--------|-----------|-------------------|
| `actualiza_parquet.py` | Actualizacion diaria CMF + BCCh | CMF (scraping), BCCh (API) |
| `actualiza_parquet_year.py` | Datos historicos por anio | CMF (scraping), BCCh (API) |
| `cla_mensual.py` | Reporte CLA mensual (Excel) | El Mercurio (API) |
| `cla_mensual2.py` | Variante CLA con categorias custom | El Mercurio (API) |
| `soyfocus.py` | Analisis fondos SoyFocus | Ninguno (datos locales) |
| `resumen_apv.py` | Resumen APV | Ninguno (datos locales) |

## Integraciones externas

| Servicio | Modulo | Metodo | Autenticacion |
|----------|--------|--------|---------------|
| CMF | `cartolas/download.py` | Playwright + captchapass | CAPTCHA |
| El Mercurio | `comparador/elmer.py` | HTTP GET (requests) | Ninguna (User-Agent spoofing) |
| BCCh | `eco/bcentral.py` | bcchapi (API oficial) | Usuario/Password (.env) |
| SendGrid | `correo/correo.py` | API REST | API Key (.env) - **INACTIVO** |
| Azure Storage | N/A (config solamente) | Connection string | Account Key (.env) - **INACTIVO** |

## Cadena de middleware / retry

```
Descarga CMF:
  @exp_retry_function(max=12, backoff=2^n seg)
    └── @retry_function(max=10, delay=10s)
          └── download_cartola() → Playwright → CMF
                └── sleep(1s) entre rangos de fecha

Actualizacion BCCh:
  Sin retry (llamada directa a bcchapi)

El Mercurio:
  Sin retry, sin delay entre requests
```

---

## Checklist de verificacion

| Item | Estado | Notas |
|------|--------|-------|
| Credenciales fuera de version control | **FAIL** | `.env` trackeado en git |
| Dependencias con versiones fijas | **FAIL** | Sin lock file, sin hash pinning |
| Validacion de input | **FAIL** | Fechas sin validar formato |
| Manejo especifico de errores | **FAIL** | `except Exception` generico |
| Rate limiting en APIs externas | **FAIL** | El Mercurio sin delay |
| Rotacion de credenciales | **FAIL** | Sin mecanismo |
| Web server / endpoints expuestos | **N/A** | Proyecto CLI/batch |
| SQL injection | **N/A** | No usa SQL |
| File upload handling | **N/A** | No acepta uploads de usuario |
| Autenticacion/autorizacion de usuarios | **N/A** | No tiene usuarios |
| CORS / headers de seguridad | **N/A** | No es web server |
| XSS en respuestas | **N/A** | No genera HTML para usuarios |
| Uso de pathlib para rutas | **PASS** | Consistente en todo el proyecto |
| Deduplicacion de datos | **PASS** | Parquet con unique constraint |
| Separacion de configuracion | **PASS** | `config.py` centralizado |
| Retry con backoff exponencial | **PASS** | Decoradores bien implementados |

---

## Top 5 fixes prioritarios

1. **Rotar todas las credenciales** y eliminar `.env` del historial de git (`git filter-repo`). Impacto: elimina el riesgo critico inmediato.
2. **Commitear `uv.lock`** para fijar versiones de dependencias. Impacto: reproducibilidad y proteccion contra supply chain.
3. **Pinear `captchapass` a un commit especifico** en `pyproject.toml`. Impacto: elimina riesgo de supply chain en dependencia privada.
4. **Lazy initialization de credenciales BCCh** en `eco/bcentral.py`. Impacto: reduce exposicion de secretos en memoria.
5. **Reemplazar `page.evaluate()` con `locator.fill()`** y agregar validacion de fechas. Impacto: elimina vector de inyeccion JavaScript.

---

## Resumen

El proyecto tiene una superficie de ataque reducida al ser CLI/batch sin endpoints web. Los riesgos principales estan concentrados en la **gestion de secretos**: credenciales expuestas en `.env` versionado es el hallazgo mas critico. La arquitectura de datos (Polars + Parquet + pathlib) es solida desde el punto de vista de seguridad. Las integraciones externas (CMF, BCCh, El Mercurio) funcionan correctamente pero carecen de rate limiting uniforme y manejo granular de errores.
