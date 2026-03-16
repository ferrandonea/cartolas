# Auditoría de Secretos Expuestos

**Fecha**: 2026-03-16
**Alcance**: Codebase completo de `cartolas/`
**Puntuación de riesgo global**: **6/10** (mitigado por `.gitignore`, pero con prácticas riesgosas activas)

---

## Hallazgos

### 1. Credenciales en archivo `.env` — CRÍTICO

| Campo | Severidad | CWE |
|-------|-----------|-----|
| `SENDGRID_API` | **CRÍTICO** | CWE-798 (Hardcoded Credentials) |
| `CONNECTION_STRING` (Azure Storage) | **CRÍTICO** | CWE-798 |
| `BCCH_USER` / `BCCH_PASS` | **ALTO** | CWE-798 |
| `TO_EMAILS` (emails personales) | **BAJO** | CWE-200 (Information Exposure) |

**Evidencia**: `.env` (líneas 2, 9-10, 13, 15)

El archivo contiene:
- API key de SendGrid (permite enviar correos suplantando la aplicación)
- Credenciales del Banco Central (acceso a API oficial BCCh)
- Connection string de Azure Storage con AccountKey (acceso completo a blob storage)
- Direcciones de correo personales

**Por qué importa**: Si la máquina es comprometida o el archivo se filtra accidentalmente, un atacante obtiene acceso a envío de correos, APIs bancarias y almacenamiento cloud.

**Estado de mitigación**: `.gitignore` línea 143 incluye `.env` — el archivo NO está en el repositorio git. No se encontró evidencia de que haya sido commiteado previamente.

**Remediación**:
1. **Rotar todas las credenciales inmediatamente** (SendGrid key, BCCh password, Azure key)
2. Considerar un gestor de secretos (Azure Key Vault, dado que ya usan Azure)
3. Permisos restrictivos en `.env`: `chmod 600 .env`

---

### 2. Carga de credenciales a nivel de módulo — ALTO

**Severidad**: ALTO
**CWE**: CWE-522 (Insufficiently Protected Credentials)

**Evidencia**:

**`eco/bcentral.py`** (líneas 10, 18, 24-25, 32):
```python
from dotenv import dotenv_values
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]
BCCh = bcchapi.Siete(usr=BCCH_USER, pwd=BCCH_PASS)
```

**`cartolas/economy.py`** (líneas 1-6):
```python
from dotenv import dotenv_values
config = dotenv_values(".env")
BCCH_USER = config["BCCH_USER"]
BCCH_PASS = config["BCCH_PASS"]
```

**Por qué importa**: Las credenciales quedan expuestas como variables globales del módulo. Pueden filtrarse en stack traces, logs, o por introspección (`dir(module)`). Además, la carga ocurre al importar — incluso si no se usan las credenciales.

**Remediación** — carga lazy con cache:
```python
import os
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_bcch_credentials() -> tuple[str, str]:
    """Carga credenciales BCCh solo cuando se necesitan."""
    user = os.environ["BCCH_USER"]
    passwd = os.environ["BCCH_PASS"]
    return user, passwd
```

Ventajas: no expone variables globales, falla rápido si faltan credenciales, y `os.environ` es el patrón estándar (compatible con Docker, CI, etc.).

---

### 3. Código comentado con patrón de secretos — MEDIO

**Severidad**: MEDIO
**CWE**: CWE-615 (Inclusion of Sensitive Information in Source Code Comments)

**Evidencia**: `correo/correo.py` (líneas 1-20)
```python
# from dotenv import dotenv_values
# config = dotenv_values(".env")
# SENDGRID_API = config["SENDGRID_API"]
# import sendgrid
```

**Por qué importa**: Código comentado que documenta cómo cargar la API key de SendGrid. Riesgo bajo pero puede reactivarse accidentalmente.

**Remediación**: Eliminar el código comentado. Si se necesita documentar el patrón, hacerlo en `CLAUDE.md` o en documentación separada sin referencia directa a variables de secretos.

---

### 4. Duplicación de carga de credenciales — MEDIO

**Severidad**: MEDIO
**CWE**: CWE-1041 (Use of Redundant Code)

**Evidencia**: Las credenciales BCCh se cargan en dos archivos independientes:
- `eco/bcentral.py` (líneas 24-25)
- `cartolas/economy.py` (líneas 5-6)

**Por qué importa**: Duplicar la carga de secretos aumenta la superficie de ataque y dificulta la rotación de credenciales (hay que verificar más puntos).

**Remediación**: Centralizar en un solo módulo (e.g., `cartolas/config.py` o un nuevo `cartolas/secrets.py`).

---

## Checklist de verificación

| Control | Estado | Notas |
|---------|--------|-------|
| Secretos hardcodeados en código fuente | ✅ Pass | No se encontraron secretos directamente en `.py` |
| API keys en `.env` (no en git) | ✅ Pass | `.gitignore` protege `.env` |
| `.env` nunca commiteado en historial | ✅ Pass | Sin evidencia en `git log` |
| Contraseñas de BD | ⬜ N/A | No hay base de datos en el proyecto |
| JWT secrets | ⬜ N/A | No hay autenticación JWT |
| Claves de encriptación | ⬜ N/A | No hay encriptación propia |
| Variables de entorno (no hardcoded) | ✅ Pass | Todos los secretos vienen de `.env` |
| Configuración prod vs dev separada | ❌ Fail | Un solo `.env` para todos los ambientes |
| Capacidad de rotación de secretos | ❌ Fail | Requiere cambio manual del `.env` |
| Carga lazy de credenciales | ❌ Fail | Se cargan al importar módulos |
| Salt/KDF para contraseñas | ⬜ N/A | No hay hashing de contraseñas |

---

## Top 5 acciones prioritarias

| # | Acción | Impacto | Esfuerzo |
|---|--------|---------|----------|
| 1 | **Rotar credenciales** (SendGrid, BCCh, Azure) | Elimina riesgo de credenciales potencialmente expuestas | Bajo |
| 2 | **Refactorizar carga de secretos** a función lazy centralizada | Reduce superficie de ataque, mejora mantenibilidad | Bajo |
| 3 | **Eliminar código comentado** en `correo/correo.py` | Reduce información expuesta | Trivial |
| 4 | **Restringir permisos** del `.env` (`chmod 600`) | Protección a nivel de filesystem | Trivial |
| 5 | **Agregar pre-commit hook** para detectar secretos (e.g., `detect-secrets`) | Previene commits accidentales de secretos | Medio |

### Snippet para pre-commit hook:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

---

## Notas de explotabilidad

- **SendGrid**: Un atacante con la API key puede enviar correos desde `sarah.connor.bot@soyfocus.com`, útil para phishing dirigido.
- **Azure Storage**: El connection string da acceso completo (read/write/delete) al account `marketpricesdata`.
- **BCCh**: Acceso a datos económicos oficiales. El RUN expuesto (`BCCH_USER`) es información personal identificable.
- **Vector de ataque principal**: Acceso al filesystem local (malware, acceso físico, backup no cifrado).

---

*Auditoría generada el 2026-03-16. Próxima revisión recomendada: después de implementar las remediaciones.*
