# Auditoría de Seguridad de Autenticación

**Fecha**: 2026-03-16
**Alcance**: Revisión completa del repositorio `cartolas`
**Puntuación de riesgo global**: **4/10** (riesgo moderado — no hay sistema de auth, pero hay credenciales expuestas)

---

## Contexto Importante

Este proyecto es una **aplicación CLI/batch de procesamiento de datos** (fondos mutuos chilenos). **No es una aplicación web** y **no tiene sistema de autenticación de usuarios**. No existe:

- Login / registro de usuarios
- JWT, sesiones, cookies
- Middleware HTTP, framework web (Flask, FastAPI, Django)
- Base de datos de usuarios
- Endpoints HTTP propios

Por lo tanto, la mayoría de los ítems del checklist de autenticación estándar **no aplican**. Sin embargo, el proyecto sí maneja **credenciales de APIs externas** y hace **peticiones HTTP**, lo cual genera hallazgos de seguridad reales.

---

## Hallazgos de Seguridad

### 1. Credenciales en texto plano en `.env`

| Campo | Detalle |
|-------|---------|
| **Severidad** | CRITICAL |
| **CWE** | CWE-798 (Use of Hard-coded Credentials), CWE-256 (Plaintext Storage of Password) |
| **Evidencia** | `.env` líneas 2, 9-10, 13, 15 |
| **Credenciales expuestas** | SendGrid API key, BCCh user/pass, Azure connection string, emails personales |

**Por qué importa**: Si el archivo `.env` se filtra (commit accidental, backup, acceso al disco), un atacante obtiene acceso a SendGrid (envío de correos), BCCh API, y Azure Storage.

**Explotabilidad**: Directa. Cualquier persona con acceso al archivo puede usar las credenciales inmediatamente.

**Estado actual**: `.gitignore` incluye `.env` (línea 131), lo que mitiga la filtración vía git. Sin embargo, el archivo existe en disco sin cifrado.

**Remediación**:
1. **Rotar inmediatamente** todas las credenciales expuestas (SendGrid, BCCh, Azure)
2. Verificar que `.env` nunca fue commiteado: `git log --all --diff-filter=A -- .env`
3. Considerar un gestor de secretos para producción (1Password CLI, `age` encryption, o variables de entorno del sistema)

---

### 2. Credenciales cargadas a nivel de módulo sin validación

| Campo | Detalle |
|-------|---------|
| **Severidad** | HIGH |
| **CWE** | CWE-522 (Insufficiently Protected Credentials) |
| **Evidencia** | `eco/bcentral.py:18-25`, `cartolas/economy.py:1-6` |

**Código problemático** (`eco/bcentral.py`):
```python
config = dotenv_values(".env")
BCCH_USER = config["BCCH_USER"]
BCCH_PASS = config["BCCH_PASS"]
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)
```

**Por qué importa**: Las credenciales se cargan al importar el módulo, incluso si no se van a usar. Si falta `.env`, el error es un `KeyError` genérico sin contexto.

**Remediación**:
```python
def get_bcch_client() -> bcchapi.Siete:
    """Crea cliente BCCh bajo demanda."""
    config = dotenv_values(".env")
    user = config.get("BCCH_USER")
    pwd = config.get("BCCH_PASS")
    if not user or not pwd:
        raise EnvironmentError("Faltan BCCH_USER o BCCH_PASS en .env")
    return bcchapi.Siete(usr=user, pwd=pwd)
```

---

### 3. Peticiones HTTP sin timeout

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIUM |
| **CWE** | CWE-400 (Uncontrolled Resource Consumption) |
| **Evidencia** | `comparador/elmer.py:89`, `cartolas/fund_identifica.py:26` |

**Código problemático**:
```python
# elmer.py
response = requests.get(url)  # Sin timeout

# fund_identifica.py
response = requests.get(url, headers=headers)  # Sin timeout
```

**Por qué importa**: Sin timeout, una petición puede colgar indefinidamente si el servidor no responde, bloqueando el proceso completo.

**Remediación**:
```python
response = requests.get(url, timeout=30)
```

---

### 4. Sin validación de código de estado HTTP

| Campo | Detalle |
|-------|---------|
| **Severidad** | MEDIUM |
| **CWE** | CWE-252 (Unchecked Return Value) |
| **Evidencia** | `comparador/elmer.py:89-93`, `cartolas/fund_identifica.py:26` |

**Por qué importa**: Se parsea la respuesta JSON sin verificar que el servidor respondió 200. Respuestas 4xx/5xx pueden contener HTML de error que rompe el parsing silenciosamente.

**Remediación**:
```python
response = requests.get(url, timeout=30)
response.raise_for_status()
```

---

### 5. Inyección JavaScript en Playwright (mitigada)

| Campo | Detalle |
|-------|---------|
| **Severidad** | LOW |
| **CWE** | CWE-94 (Improper Control of Generation of Code) |
| **Evidencia** | `cartolas/download.py:81-82` |

**Código problemático**:
```python
page.evaluate(f"document.querySelector('#txt_inicio').value = '{start_date}';")
page.evaluate(f"document.querySelector('#txt_termino').value = '{end_date}';")
```

**Mitigación actual**: `start_date` y `end_date` provienen de `format_date_cmf()` que fuerza formato `dd/mm/yyyy`.

**Remediación** (defensa en profundidad):
```python
page.evaluate("(date) => document.querySelector('#txt_inicio').value = date", start_date)
page.evaluate("(date) => document.querySelector('#txt_termino').value = date", end_date)
```

---

### 6. Uso de `random` en lugar de `secrets` para nombres de archivo

| Campo | Detalle |
|-------|---------|
| **Severidad** | LOW |
| **CWE** | CWE-330 (Use of Insufficiently Random Values) |
| **Evidencia** | `utiles/file_tools.py:29-30` |

**Código actual**:
```python
random_string = "".join(random.choices(string.ascii_letters + string.digits, k=16))
```

**Remediación**:
```python
import secrets
random_string = secrets.token_hex(16)
```

---

### 7. Captura genérica de excepciones en decoradores

| Campo | Detalle |
|-------|---------|
| **Severidad** | LOW |
| **CWE** | CWE-754 (Improper Check for Unusual Conditions) |
| **Evidencia** | `utiles/decorators.py:35,70` |

**Por qué importa**: Capturar `Exception` genérica puede ocultar errores graves (MemoryError, KeyboardInterrupt) y reintentar operaciones que no deberían reintentarse.

**Remediación**: Capturar excepciones específicas (ej: `requests.RequestException`, `TimeoutError`).

---

### 8. Sin limpieza explícita de recursos Playwright

| Campo | Detalle |
|-------|---------|
| **Severidad** | LOW |
| **CWE** | CWE-404 (Improper Resource Shutdown or Release) |
| **Evidencia** | `cartolas/download.py:51-53` |

**Por qué importa**: Si ocurre una excepción, el browser de Playwright puede quedar abierto consumiendo recursos.

**Remediación**: Usar context manager o try-finally para asegurar `browser.close()`.

---

## Checklist de Autenticación: Pass / Fail / N/A

| Item | Estado | Nota |
|------|--------|------|
| Password hashing (bcrypt) | N/A | No hay sistema de usuarios/passwords |
| JWT secret/key strength | N/A | No se usa JWT |
| Token settings (TTL) | N/A | No hay tokens de sesión |
| Refresh token implementation | N/A | No hay refresh tokens |
| Session invalidation | N/A | No hay sesiones |
| Brute force protection | N/A | No hay endpoints de login |
| Account enumeration defenses | N/A | No hay cuentas de usuario |
| Password reset flow | N/A | No hay reset de passwords |
| Email verification | N/A | No hay verificación de email |
| SQL/NoSQL injection | N/A | No hay base de datos SQL/NoSQL (usa Parquet) |
| AuthZ integrity (roles) | N/A | No hay sistema de roles |
| Cookie & CSRF configuration | N/A | No hay cookies ni web framework |
| Input validation & normalization | **PASS** | Fechas validadas por `format_date_cmf()`, tipos tipados |
| Mass assignment risks | N/A | No hay modelos de usuario |
| JWT misuse (decode vs verify) | N/A | No se usa JWT |
| Logging & telemetry | **FAIL** | Excepciones genéricas con `print()`, sin redacción de datos sensibles |
| Dependency & crypto hygiene | **PASS** | No usa crypto custom; hashlib solo para nombres de archivo |
| Transport & CORS | **PASS** | Conexiones externas vía HTTPS; no hay servidor propio |
| Open redirect / next param | N/A | No hay redirecciones |
| Operational controls | **FAIL** | Sin rotación de secretos, sin monitoreo de patrones sospechosos |
| Credential storage | **FAIL** | Credenciales en `.env` sin cifrado; carga a nivel de módulo |
| HTTP request safety | **FAIL** | Sin timeouts ni validación de status codes |

---

## Top 5 Acciones Prioritarias

| # | Acción | Impacto | Esfuerzo |
|---|--------|---------|----------|
| 1 | **Rotar todas las credenciales** (SendGrid, BCCh, Azure) y verificar que `.env` nunca fue commiteado | Elimina riesgo de credenciales comprometidas | Bajo |
| 2 | **Agregar timeouts a todas las peticiones HTTP** (`requests.get(..., timeout=30)`) | Previene bloqueos indefinidos | Bajo |
| 3 | **Lazy-loading de credenciales** con validación (no cargar al importar módulo) | Mejor manejo de errores, menor exposición | Bajo |
| 4 | **Validar status codes HTTP** con `response.raise_for_status()` | Detecta errores de API tempranamente | Bajo |
| 5 | **Parametrizar `page.evaluate()`** en Playwright en vez de f-strings | Defensa en profundidad contra inyección JS | Bajo |

---

## Resumen

Este proyecto **no tiene sistema de autenticación** — es una herramienta CLI de procesamiento de datos financieros. La superficie de ataque principal son las **credenciales de APIs externas** almacenadas en `.env` y las **peticiones HTTP** a servicios externos.

Los riesgos más críticos son la exposición potencial de credenciales y la falta de prácticas defensivas en peticiones HTTP. Todas las remediaciones son de bajo esfuerzo y alto impacto.
