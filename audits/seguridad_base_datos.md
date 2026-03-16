# Auditoría de Seguridad - Interacciones con Base de Datos

**Fecha:** 2026-03-16
**Alcance:** Repositorio `cartolas/` completo
**Score de riesgo global:** 4/10

---

## Resumen ejecutivo

Este proyecto **no utiliza bases de datos tradicionales** (SQL, NoSQL). El almacenamiento se basa enteramente en **archivos Parquet** gestionados con Polars LazyFrames, complementado con JSON y CSV. Las APIs externas (BCCh, El Mercurio) son las únicas conexiones a sistemas remotos.

El riesgo principal es la **gestión de credenciales**: el archivo `.env` contiene secretos en texto plano (SendGrid API key, credenciales BCCh, Azure connection string). Aunque `.env` está en `.gitignore` y nunca fue commiteado, las credenciales no están cifradas ni gestionadas por un secrets manager.

---

## Hallazgos

### 1. Credenciales en texto plano en `.env`

| Campo | Valor |
|-------|-------|
| **Severidad** | Alta |
| **CWE** | CWE-256 (Plaintext Storage of a Password) |
| **Evidencia** | `.env` líneas 2, 9-10, 13 |
| **Por qué importa** | Cualquier persona con acceso al filesystem puede leer SendGrid API key, BCCh user/pass, y Azure Storage connection string. Un acceso no autorizado al equipo compromete todos los servicios externos. |

**Credenciales expuestas:**
- SendGrid API key (línea 2)
- BCCh usuario RUT + contraseña (líneas 9-10)
- Azure Storage connection string con AccountKey completa (línea 13)
- Emails del equipo (línea 15)

**Remediación:**
- Usar un secrets manager (1Password CLI, macOS Keychain, o `aws secretsmanager`/`az keyvault`).
- Como mínimo, restringir permisos del archivo: `chmod 600 .env`.
- Rotar las credenciales periódicamente.
- La Azure connection string no se usa activamente en el código — eliminarla del `.env` si no es necesaria.

---

### 2. Credenciales cargadas como constantes de módulo

| Campo | Valor |
|-------|-------|
| **Severidad** | Media |
| **CWE** | CWE-798 (Use of Hard-coded Credentials) |
| **Evidencia** | `eco/bcentral.py:18-25`, `cartolas/economy.py:1-6` |
| **Por qué importa** | Las credenciales se cargan al importar el módulo y permanecen en memoria durante toda la ejecución. Además están duplicadas en dos archivos. |

```python
# eco/bcentral.py:18-25
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]
```

**Remediación:**
Cargar credenciales de forma lazy, solo cuando se necesitan:

```python
def _get_bcch_client():
    env = dotenv_values(".env")
    return bcchapi.Sievi(usr=env["BCCH_USER"], pwd=env["BCCH_PASS"])
```

Eliminar la duplicación en `cartolas/economy.py`.

---

### 3. Emails hardcodeados en config.py

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-798 |
| **Evidencia** | `cartolas/config.py:116-120` |
| **Por qué importa** | Emails como valores por defecto en código fuente. Riesgo menor, pero expone información personal si el repo es público. |

```python
SENDER_MAIL, SENDER_NAME, TO_EMAILS = (
    "francisco@soyfocus.com",
    "Francisco",
    ["francisco@soyfocus.com"],
)
```

**Remediación:** Mover a `.env` o cargar desde variables de entorno.

---

### 4. Archivos Parquet sin protección de integridad

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-354 (Improper Validation of Integrity Check Value) |
| **Evidencia** | `cartolas/save.py:6-22`, `cartolas/read.py:7-31` |
| **Por qué importa** | Los archivos Parquet (~750MB) se leen y escriben sin checksums ni validación de integridad. Un archivo corrupto o manipulado se procesaría sin alerta. |

**Remediación:**
- Parquet ya incluye checksums internos por página. Considerar habilitar validación explícita si Polars lo soporta.
- Para datos críticos, mantener backups versionados o usar hashes SHA-256 como sidecar files.

---

### 5. Sin cifrado de datos en reposo

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-311 (Missing Encryption of Sensitive Data) |
| **Evidencia** | `cartolas/data/parquet/`, `cartolas/data/bcch/`, `cartolas/data/elmer/` |
| **Por qué importa** | Los datos financieros (cartolas, indicadores económicos) se almacenan sin cifrado. Si bien no contienen PII directamente, incluyen datos de fondos mutuos que podrían ser sensibles comercialmente. |

**Remediación:**
- Habilitar FileVault (macOS) para cifrado de disco completo.
- Para datos especialmente sensibles, considerar cifrado a nivel de archivo antes de escribir.

---

### 6. API El Mercurio sin validación TLS explícita

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-295 (Improper Certificate Validation) |
| **Evidencia** | `comparador/elmer.py:75-103` |
| **Por qué importa** | Las llamadas HTTP a El Mercurio usan `requests.get()` con configuración por defecto. Si bien `requests` valida TLS por defecto, no hay verificación explícita ni certificate pinning. |

```python
response = requests.get(url)
```

**Remediación:** El comportamiento por defecto de `requests` es seguro (verifica TLS). No se requiere acción inmediata. Para defensa en profundidad, considerar `verify=True` explícito y timeouts:

```python
response = requests.get(url, timeout=30, verify=True)
```

---

## Top 5 acciones prioritarias

| # | Acción | Impacto |
|---|--------|---------|
| 1 | Restringir permisos de `.env` (`chmod 600`) | Reduce exposición inmediata de credenciales |
| 2 | Eliminar Azure connection string de `.env` si no se usa | Reduce superficie de ataque |
| 3 | Rotar credenciales BCCh y SendGrid | Invalida posibles fugas anteriores |
| 4 | Consolidar carga de credenciales (eliminar duplicación `economy.py`) | Reduce puntos de acceso a secretos |
| 5 | Agregar timeouts a llamadas HTTP (`elmer.py`, `bcentral.py`) | Previene bloqueos por servicios caídos |

---

## Checklist de verificación

| Control | Estado | Notas |
|---------|--------|-------|
| Queries parametrizadas / ORM | N/A | No hay SQL/NoSQL en el proyecto |
| Seguridad de connection strings | **FALLO** | Azure connection string en `.env` sin protección adicional |
| Permisos mínimos de BD | N/A | No hay base de datos |
| Cifrado en reposo | **FALLO** | Parquet/JSON/CSV sin cifrado (depende de FileVault) |
| Manejo de PII / GDPR | PASA | No se almacena PII de usuarios finales |
| Timeouts de queries | N/A | No hay queries SQL |
| Connection pool | N/A | No hay conexiones persistentes a BD |
| Manejo de transacciones | N/A | Operaciones de archivo son atómicas (write_parquet) |
| Audit logging | **FALLO** | No hay logging de acceso a datos sensibles |
| Inyección NoSQL | N/A | No hay NoSQL |
| Aislamiento row/tenant | N/A | Aplicación single-tenant |
| Red / firewall de BD | N/A | No hay BD remota |
| TLS en tránsito | PASA | `requests` valida TLS por defecto; `bcchapi` usa HTTPS |
| Gestión de secretos y rotación | **FALLO** | Secretos en `.env` sin rotación ni secrets manager |
| Schema e integridad | PASA | Schema estricto en `config.SCHEMA` con tipos Polars |
| Minimización de campos | PASA | Se seleccionan columnas específicas en análisis |
| Paginación / límites | N/A | No hay APIs expuestas |
| Seguridad de backups | **FALLO** | No hay política de backup para Parquet |
| Retención y eliminación de datos | **FALLO** | No hay política formal de retención |
| Seguridad de migraciones | N/A | No hay migraciones SQL |
| Raw queries / escape hatches | N/A | No hay ORM |
| Manejo de LIKE / regex | N/A | No hay queries SQL |
| Timeouts y resource guards | **FALLO** | Llamadas HTTP sin timeout explícito |
| Profundidad de auditoría/monitoreo | **FALLO** | Sin logging centralizado |
| PII en logs/métricas | PASA | No hay logging de PII |
| Indexación de datos sensibles | N/A | No hay índices de BD |
| Ciclo de vida de cuentas de servicio | **FALLO** | Credenciales estáticas sin rotación |
| Capas de caché | N/A | Sin Redis/Memcached |
| Exportaciones analytics/ETL | PASA | CSV/Excel generados localmente, sin PII |

---

## Notas de explotabilidad

- **Sin inyección SQL/NoSQL posible:** El proyecto no ejecuta queries contra bases de datos. Todo el procesamiento es via Polars sobre archivos locales.
- **Vector de ataque principal:** Acceso físico o remoto al filesystem donde reside `.env`. Un atacante con acceso al equipo obtendría credenciales de BCCh, SendGrid, y Azure Storage.
- **El `.env` nunca fue commiteado** al historial de git (verificado con `git log --all -- .env`), lo cual reduce significativamente el riesgo de fuga por repositorio.
- **La Azure connection string no se usa activamente** en el código, lo que sugiere que podría ser un remanente — eliminarla reduciría la superficie de ataque sin impacto funcional.
