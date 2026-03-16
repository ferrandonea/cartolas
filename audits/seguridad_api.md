# Auditoría de Seguridad API - Cartolas

**Fecha:** 2026-03-16
**Alcance:** Configuraciones de seguridad API del proyecto Cartolas
**Contexto:** Este proyecto es una herramienta CLI de procesamiento batch, **no un servidor web ni una API REST**. No expone endpoints HTTP. Interactúa como *cliente* con APIs externas (CMF, BCCh, El Mercurio, SendGrid).

---

## Hallazgos

### 1. Descarga de archivos sin validación de nombre

| Campo | Detalle |
|-------|---------|
| **Severidad** | Media |
| **CWE** | CWE-22 (Path Traversal) |
| **Evidencia** | `cartolas/download.py`, función `download_cartola`, líneas ~107-114 |
| **Por qué importa** | Un nombre de archivo sugerido por el servidor podría contener secuencias de path traversal (`../`) y escribir fuera del directorio esperado. |

**Código actual:**
```python
download_path = cartolas_txt_folder / download.suggested_filename
download.save_as(download_path)
```

**Explotabilidad:** Baja. Requiere que el servidor CMF devuelva un filename malicioso, lo cual es improbable pero no imposible si el servidor es comprometido.

**Remediación:**
```python
from pathlib import PurePosixPath

safe_name = PurePosixPath(download.suggested_filename).name  # Elimina componentes de ruta
if not safe_name:
    safe_name = "descarga_cmf.txt"
download_path = cartolas_txt_folder / safe_name
download.save_as(download_path)
```

---

### 2. Credenciales cargadas al inicio sin validación

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-798 (Hard-coded Credentials — variante: sin rotación) |
| **Evidencia** | `eco/bcentral.py`, líneas ~20-32 |
| **Por qué importa** | Las credenciales se cargan a nivel de módulo. Si `.env` está mal configurado, el error se propaga silenciosamente o con un `KeyError` no manejado que expone el nombre de la variable. |

**Código actual:**
```python
env_variables = dotenv_values(".env")
BCCH_PASS = env_variables["BCCH_PASS"]
BCCH_USER = env_variables["BCCH_USER"]
BCCh = bcchapi.Sieci(usr=BCCH_USER, pwd=BCCH_PASS)
```

**Remediación:**
```python
env_variables = dotenv_values(".env")
BCCH_USER = env_variables.get("BCCH_USER")
BCCH_PASS = env_variables.get("BCCH_PASS")

if not BCCH_USER or not BCCH_PASS:
    raise EnvironmentError("Faltan credenciales BCCH_USER/BCCH_PASS en .env")

BCCh = bcchapi.Sieci(usr=BCCH_USER, pwd=BCCH_PASS)
```

**Defensa en profundidad:** Considerar no instanciar `BCCh` a nivel de módulo, sino bajo demanda (lazy init), para evitar que un import falle por credenciales faltantes.

---

### 3. Exposición de detalles de excepción

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-209 (Information Exposure Through Error Message) |
| **Evidencia** | `cartolas/download.py`, líneas ~116-120 |
| **Por qué importa** | `print(f"Detalles: {e}")` puede revelar rutas internas, credenciales en URLs, o detalles de red. En una herramienta CLI local esto es bajo riesgo, pero si los logs se comparten o centralizan, se convierte en un vector de fuga. |

**Código actual:**
```python
except Exception as e:
    print("Error en la descarga") if verbose else None
    print(f"Detalles: {e}") if verbose else None
    temp_file_path.rename(error_folder / f"{prediction}.png")
    raise e
```

**Remediación:**
```python
except Exception as e:
    if verbose:
        print(f"Error en la descarga: {type(e).__name__}")
    temp_file_path.rename(error_folder / f"{prediction}.png")
    raise
```

---

### 4. Sin rate limiting en llamadas a APIs externas

| Campo | Detalle |
|-------|---------|
| **Severidad** | Media |
| **CWE** | CWE-799 (Improper Control of Interaction Frequency) |
| **Evidencia** | `comparador/elmer.py`, líneas ~70-101 (loop de categorías sin delay); `cartolas/download.py` línea ~138 (`sleep(1)` hardcoded) |
| **Por qué importa** | Las llamadas sin throttling a El Mercurio pueden resultar en IP bans o throttling del servidor. El `sleep(1)` de CMF es fijo y no se adapta a respuestas del servidor (ej. HTTP 429). |

**Remediación para `elmer.py`:**
```python
from time import sleep

for category_id in categories:
    result = requests.get(url + str(category_id))
    sleep(0.5)  # Throttle básico
    # ... procesamiento
```

**Remediación para `download.py`:** Manejar HTTP 429 con backoff:
```python
# Ya existe @retry_function — asegurar que detecte rate limiting
# y aumente el delay dinámicamente
```

---

### 5. Deserialización JSON sin validación de esquema

| Campo | Detalle |
|-------|---------|
| **Severidad** | Baja |
| **CWE** | CWE-502 (Deserialization of Untrusted Data) |
| **Evidencia** | `utiles/file_tools.py` (función `read_json`), `comparador/elmer.py` (respuestas HTTP) |
| **Por qué importa** | Se confía ciegamente en la estructura del JSON recibido de APIs externas. Un cambio en la API o una respuesta manipulada podría causar comportamiento inesperado. |

**Remediación:** Para datos de APIs externas, validar campos esperados antes de procesarlos:
```python
data = response.json()
if not isinstance(data, list) or not all("RUN" in item for item in data):
    raise ValueError(f"Respuesta inesperada de El Mercurio para categoría {category_id}")
```

---

### 6. Todas las conexiones externas usan HTTPS

| Campo | Detalle |
|-------|---------|
| **Severidad** | Informativo (positivo) |
| **Evidencia** | `cartolas/config.py` (URLs CMF), `comparador/elmer.py` (URL El Mercurio), `eco/bcentral.py` (bcchapi) |

Todas las URLs externas usan `https://`. No se encontraron conexiones HTTP planas.

---

## Puntaje de Riesgo Global

### **3 / 10** (Riesgo Bajo)

**Justificación:** El proyecto no es un servidor web, no expone endpoints, y no maneja datos de usuarios externos. Los riesgos son limitados a la interacción como cliente con APIs externas y al manejo de credenciales locales, ambos implementados de forma razonable.

---

## Top 5 Correcciones Prioritarias

| Prioridad | Hallazgo | Esfuerzo | Impacto |
|-----------|----------|----------|---------|
| 1 | Validar nombres de archivo en descargas CMF | 5 min | Elimina path traversal potencial |
| 2 | Agregar throttling a llamadas El Mercurio | 5 min | Previene IP bans |
| 3 | Validar credenciales al cargarlas | 5 min | Errores claros si `.env` incompleto |
| 4 | Reducir verbosidad de excepciones en download | 5 min | Menos fuga de info en logs |
| 5 | Validar esquema de respuestas JSON externas | 15 min | Resiliencia ante cambios de API |

---

## Checklist de Verificación

| Control | Estado | Notas |
|---------|--------|-------|
| **Configuración CORS** | N/A | No es un servidor web |
| Wildcard (*) en producción | N/A | — |
| Validación de origen | N/A | — |
| Manejo de credentials CORS | N/A | — |
| **Rate Limiting** | FALLA | Solo `sleep(1)` hardcoded en CMF; sin throttling en El Mercurio |
| En todos los endpoints | N/A | No hay endpoints |
| Límites diferenciados por operación | N/A | — |
| Rate limiting distribuido | N/A | — |
| **Versionado de API** | N/A | No es una API |
| Manejo de versiones deprecadas | N/A | — |
| Gestión de breaking changes | N/A | — |
| **Límites de tamaño de request** | N/A | No recibe requests |
| Límites de body parser | N/A | — |
| Restricciones de upload | N/A | — |
| Límites de profundidad JSON | N/A | — |
| **Headers de seguridad HTTP** | N/A | No es un servidor web |
| Helmet.js / equivalente | N/A | — |
| CSP headers | N/A | — |
| X-Frame-Options | N/A | — |
| X-Content-Type-Options | N/A | — |
| Strict-Transport-Security | N/A | — |
| **Gestión de API keys/tokens** | PASA (con observaciones) | `.env` en `.gitignore`, carga correcta, sin rotación |
| Almacenamiento seguro | PASA | `.env` excluido de git |
| Política de rotación | FALLA | No hay mecanismo de rotación |
| Limitación de alcance (scopes) | N/A | APIs externas definen los scopes |
| **Manejo de errores** | PASA (con observaciones) | Generalmente bien, pero `download.py` expone detalles de excepción |
| Sin stack traces en producción | PASA | Solo se imprime con `verbose=True` |
| Mensajes genéricos de error | FALLA | `f"Detalles: {e}"` expone info interna |
| Códigos de estado apropiados | N/A | No es un servidor |
| **Conexiones HTTPS** | PASA | Todas las URLs externas usan HTTPS |
| **Validación de datos externos** | FALLA | JSON de APIs externas se procesa sin validar esquema |
| **Validación de nombres de archivo** | FALLA | `download.suggested_filename` se usa sin sanitizar |
