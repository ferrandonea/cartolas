# Auditoría de Logging y Monitoreo

**Fecha**: 2026-03-16
**Alcance**: Revisión completa de logging, monitoreo, manejo de datos sensibles y prevención de inyección de logs.

---

## Puntuación de Riesgo Global: 6/10

El proyecto no utiliza ningún framework de logging (solo `print()`), no tiene monitoreo ni alertas, y expone credenciales en variables globales a nivel de módulo. No hay registro de eventos de seguridad ni políticas de retención de logs.

---

## Top 5 Correcciones Prioritarias

1. **Reemplazar `print()` por el módulo `logging`** — 142 ocurrencias en 22 archivos sin niveles, rotación ni formato estructurado.
2. **Eliminar credenciales de variables globales** en `eco/bcentral.py` — cargar credenciales solo cuando se necesitan, no al importar el módulo.
3. **Sanitizar excepciones antes de loguear** — `decorators.py` y `download.py` loguean `{e}` directamente.
4. **Implementar logging de eventos de seguridad** — no hay registro de fallos de autenticación ni errores de validación.
5. **Agregar monitoreo básico** — no existe detección de actividad inusual ni alertas de tasa de errores.

---

## Hallazgos Detallados

### 1. Ausencia total de framework de logging

| Campo | Detalle |
|-------|---------|
| **Severidad** | High |
| **CWE** | CWE-778 (Insufficient Logging) |
| **Evidencia** | 22 archivos Python, 142 llamadas a `print()`. 0 usos de `import logging`. |
| **Por qué importa** | Sin niveles de log (DEBUG/INFO/WARNING/ERROR), sin rotación, sin formato estructurado, sin posibilidad de enviar logs a un sistema centralizado. Los `print()` van a stdout y se pierden. |

**Archivos con más `print()`:**

| Archivo | Ocurrencias |
|---------|-------------|
| `utiles/fechas.py` | 36 |
| `utiles/file_tools.py` | 14 |
| `cartolas/fund_identifica.py` | 12 |
| `comparador/elmer.py` | 9 |
| `cla_mensual2.py` | 9 |
| `cartolas/download.py` | 8 |

**Remediación:**

```python
# Crear un módulo utiles/logging_config.py
import logging
import sys

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

```python
# Ejemplo de migración en decorators.py
from utiles.logging_config import get_logger
logger = get_logger(__name__)

# Antes:
print(f"Error en {func.__name__}: {e}")
# Después:
logger.warning("Reintento %d/%d en %s", attempts, max_attempts, func.__name__)
```

---

### 2. Credenciales cargadas a nivel de módulo

| Campo | Detalle |
|-------|---------|
| **Severidad** | Medium |
| **CWE** | CWE-798 (Use of Hard-coded Credentials), CWE-522 (Insufficiently Protected Credentials) |
| **Evidencia** | `eco/bcentral.py:18,24-25,32` — `BCCH_USER` y `BCCH_PASS` se cargan como variables globales al importar el módulo. `BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)` crea un objeto global con credenciales. |
| **Por qué importa** | Cualquier `import eco.bcentral` ejecuta el login y expone credenciales en el namespace global. Si una excepción contiene el traceback, las credenciales podrían filtrarse en logs. |

**Nota:** El archivo `.env` **NO** fue commiteado a git (verificado en historial). Está en `.gitignore` correctamente.

**Remediación:**

```python
# eco/bcentral.py — cargar credenciales bajo demanda
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_bcch_client() -> bcchapi.Siete:
    env_variables = dotenv_values(".env")
    return bcchapi.Siete(
        usr=env_variables["BCCH_USER"],
        pwd=env_variables["BCCH_PASS"],
    )

# Usar _get_bcch_client() en lugar de BCCh global
```

---

### 3. Excepciones logueadas sin sanitización

| Campo | Detalle |
|-------|---------|
| **Severidad** | Medium |
| **CWE** | CWE-209 (Generation of Error Message Containing Sensitive Information) |
| **Evidencia** | `utiles/decorators.py:37,72` — `print(f"Error en {func.__name__}: {e}")`. `cartolas/download.py:118` — `print(f"Detalles: {e}")`. `utiles/file_tools.py:133,161,197,200` — múltiples `print(f"Error...{e}")`. |
| **Por qué importa** | El objeto excepción `{e}` puede contener rutas del sistema, credenciales parciales, URLs con tokens, o información de la infraestructura interna. |

**Reproducción:**

```python
# Si bcchapi lanza un error de autenticación, el mensaje podría contener:
# "Authentication failed for user 77057272K with password Av4..."
# Esto se imprimiría directamente por el decorador retry_function
```

**Remediación:**

```python
# En decorators.py, loguear solo el tipo de excepción:
logger.warning(
    "Error en %s: %s (intento %d/%d)",
    func.__name__,
    type(e).__name__,  # Solo el tipo, no el mensaje completo
    attempts,
    max_attempts,
)
logger.debug("Detalle de excepción en %s", func.__name__, exc_info=True)
```

---

### 4. Riesgo de inyección de logs

| Campo | Detalle |
|-------|---------|
| **Severidad** | Low |
| **CWE** | CWE-117 (Improper Output Neutralization for Logs) |
| **Evidencia** | `cartolas/download.py:74` — `print(f"Predicción del captcha: {prediction}")`. La variable `prediction` viene de OCR externo (`captchapass.predict()`). `cartolas/download.py:114` — `print(f"Archivo descargado como: {download_path}")` incluye nombre de archivo del servidor remoto. |
| **Por qué importa** | Si `prediction` contiene caracteres de control (`\n`, `\r`, secuencias ANSI), podría inyectar líneas falsas en los logs. En este contexto el riesgo real es bajo porque el captcha es generado por la CMF, no por un atacante. |

**Remediación:**

```python
# Sanitizar antes de loguear:
import re
safe_prediction = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', prediction)
logger.info("Predicción del captcha: %s", safe_prediction)
```

---

### 5. Sin logging de eventos de seguridad

| Campo | Detalle |
|-------|---------|
| **Severidad** | Medium |
| **CWE** | CWE-778 (Insufficient Logging) |
| **Evidencia** | `eco/bcentral.py:32` — login a BCCh sin registrar éxito/fallo. `cartolas/download.py:56` — navegación a CMF sin registrar resultado. `comparador/elmer.py:89` — peticiones HTTP a El Mercurio sin registrar códigos de respuesta. |
| **Por qué importa** | Sin registro de eventos de seguridad es imposible detectar: intentos fallidos de autenticación con BCCh, scraping bloqueado por CMF, o cambios en la API de El Mercurio. |

**Remediación:**

```python
# eco/bcentral.py — registrar intentos de autenticación
@lru_cache(maxsize=1)
def _get_bcch_client() -> bcchapi.Siete:
    env_variables = dotenv_values(".env")
    try:
        client = bcchapi.Siete(
            usr=env_variables["BCCH_USER"],
            pwd=env_variables["BCCH_PASS"],
        )
        logger.info("BCCh: Autenticación exitosa")
        return client
    except Exception:
        logger.error("BCCh: Fallo de autenticación")
        raise
```

---

### 6. Sin monitoreo ni alertas

| Campo | Detalle |
|-------|---------|
| **Severidad** | Medium |
| **CWE** | CWE-223 (Omission of Security-relevant Information) |
| **Evidencia** | No existe configuración de monitoreo en ningún archivo del proyecto. No hay health checks, métricas, ni integración con servicios de alertas. |
| **Por qué importa** | Si la descarga de CMF falla silenciosamente, si BCCh cambia su API, o si El Mercurio deja de responder, nadie se entera hasta que los datos estén desactualizados. |

**Remediación (mínima):**

```python
# Agregar al final de actualiza_parquet.py:
import smtplib
# O usar el módulo correo/ existente para notificar errores críticos

# Alternativa: usar logging con un handler SMTP
from logging.handlers import SMTPHandler
mail_handler = SMTPHandler(
    mailhost="smtp.sendgrid.net",
    fromaddr="alerts@soyfocus.com",
    toaddrs=["francisco@soyfocus.com"],
    subject="Error en pipeline cartolas",
)
mail_handler.setLevel(logging.ERROR)
logger.addHandler(mail_handler)
```

---

### 7. Sin política de retención ni rotación de logs

| Campo | Detalle |
|-------|---------|
| **Severidad** | Low |
| **CWE** | N/A |
| **Evidencia** | Todo va a stdout vía `print()`. No hay archivos de log, no hay rotación, no hay backup. |
| **Por qué importa** | Los logs se pierden al cerrar la terminal. No hay trazabilidad histórica de ejecuciones. |

**Remediación:**

```python
from logging.handlers import RotatingFileHandler

file_handler = RotatingFileHandler(
    "cartolas.log",
    maxBytes=5_000_000,  # 5 MB
    backupCount=3,
)
```

---

## Checklist de Cumplimiento

| Control | Estado | Notas |
|---------|--------|-------|
| **Datos sensibles no logueados** | | |
| Contraseñas/tokens no en logs | PASS | No se imprimen directamente, pero podrían filtrarse via excepciones |
| Números de tarjeta no en logs | N/A | No se manejan datos de tarjetas |
| API keys no en logs | PASS | No se loguean API keys |
| PII no en logs | PASS | No se maneja PII de usuarios |
| **Logging de eventos de seguridad** | | |
| Intentos fallidos de login | FAIL | BCCh login no registra fallos |
| Fallos de autorización | FAIL | No hay control de autorización |
| Fallos de validación de input | FAIL | Solo `_validate_custom_mapping()` en merge.py, sin logging |
| Errores del sistema | PARTIAL | Excepciones se imprimen pero sin niveles ni persistencia |
| **Prevención de inyección de logs** | | |
| Sanitización de input en logs | FAIL | `prediction` del captcha y nombres de archivo se loguean sin sanitizar |
| Logging estructurado | FAIL | Solo f-strings con `print()` |
| **Almacenamiento y retención** | | |
| Almacenamiento seguro | FAIL | Solo stdout, se pierde |
| Política de rotación | FAIL | No existe |
| Estrategia de backup | FAIL | No existe |
| **Monitoreo y alertas** | | |
| Detección de actividad inusual | FAIL | No implementado |
| Monitoreo de tasa de errores | FAIL | No implementado |
| Anomalías de rendimiento | PARTIAL | `@timer` mide tiempos pero solo imprime a stdout |

---

## Resumen

| Severidad | Cantidad |
|-----------|----------|
| Critical | 0 |
| High | 1 |
| Medium | 4 |
| Low | 2 |

El proyecto tiene un riesgo moderado. No hay vulnerabilidades críticas de exposición directa de secretos en logs, pero la ausencia completa de un framework de logging profesional, combinada con excepciones sin sanitizar y cero monitoreo, deja al proyecto ciego ante fallos operacionales y potenciales incidentes de seguridad.
