# Auditoría de Manejo de Archivos y Funcionalidad de Upload

**Fecha:** 2026-03-16
**Alcance:** Revisión completa del codebase `cartolas/` en busca de funcionalidad de carga de archivos y vulnerabilidades asociadas al manejo de archivos.

---

## Hallazgo Principal: No Existe Funcionalidad de File Upload

Este proyecto es una **aplicación CLI/batch** para análisis de fondos mutuos chilenos. **No es una aplicación web** y no tiene endpoints HTTP que acepten archivos de usuarios.

No se encontraron dependencias de frameworks web (Flask, FastAPI, Django, etc.) en `pyproject.toml`.

Sin embargo, el proyecto **sí maneja archivos provenientes de fuentes externas** (CMF, El Mercurio), lo cual presenta superficie de ataque relevante.

---

## Hallazgos de Seguridad en Manejo de Archivos

### 1. Path Traversal en Nombre de Archivo Descargado

| Campo | Valor |
|-------|-------|
| **Severidad** | Media |
| **CWE** | CWE-22 (Improper Limitation of a Pathname to a Restricted Directory) |
| **Archivo** | `cartolas/download.py` |
| **Función** | `fetch_cartola_data()` |
| **Líneas** | 112-113 |

**Evidencia:**

```python
# download.py:112-113
download_path = cartolas_txt_folder / download.suggested_filename
download.save_as(download_path)
```

**Por qué importa:** `download.suggested_filename` proviene del header `Content-Disposition` del servidor CMF. Si el servidor fuera comprometido o se ejecutara un ataque MITM, un filename como `../../etc/cron.d/malicious` permitiría escritura fuera del directorio esperado.

**Explotabilidad:** Baja en la práctica (requiere comprometer el servidor CMF o MITM), pero el patrón es inseguro.

**Remediación:**

```python
from pathlib import PurePosixPath

# Sanitizar el filename: solo usar el componente final, sin path traversal
safe_name = PurePosixPath(download.suggested_filename).name
if not safe_name or safe_name.startswith('.'):
    safe_name = f"cartola_{start_date}_{end_date}.txt"
download_path = cartolas_txt_folder / safe_name
download.save_as(download_path)
```

---

### 2. Sin Validación de Tamaño de Archivo Descargado

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-400 (Uncontrolled Resource Consumption) |
| **Archivo** | `cartolas/download.py` |
| **Función** | `fetch_cartola_data()` |
| **Líneas** | 110-115 |

**Evidencia:**

```python
# download.py:115 — el propio código lo reconoce:
# ACA FALTA CHEQUEAR EL TAMAÑO
```

El archivo se guarda sin verificar su tamaño. Un servidor comprometido podría enviar un archivo arbitrariamente grande.

**Remediación:**

```python
MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50 MB

download.save_as(download_path)
if download_path.stat().st_size > MAX_DOWNLOAD_SIZE:
    download_path.unlink()
    raise ValueError(f"Archivo descargado excede {MAX_DOWNLOAD_SIZE} bytes")
```

---

### 3. Sin Validación de Tipo/Contenido del Archivo Descargado

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-434 (Unrestricted Upload of File with Dangerous Type) — aplicado a descargas |
| **Archivo** | `cartolas/download.py` |
| **Función** | `fetch_cartola_data()` |
| **Líneas** | 112-113 |

**Evidencia:** No se valida que el archivo descargado sea realmente un CSV/TXT antes de procesarlo. El pipeline asume que todo archivo descargado es un CSV delimitado por `;`.

**Remediación:**

```python
# Verificar extensión
if not safe_name.endswith('.txt'):
    download_path.unlink()
    raise ValueError(f"Extensión inesperada: {safe_name}")

# Verificar contenido básico (que sea texto válido)
with open(download_path, 'r', encoding='latin-1') as f:
    first_line = f.readline()
    if ';' not in first_line:
        download_path.unlink()
        raise ValueError("El archivo no parece ser un CSV válido de CMF")
```

---

### 4. Imagen Captcha Sin Validación de Magic Number

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-345 (Insufficient Verification of Data Authenticity) |
| **Archivo** | `cartolas/download.py` |
| **Función** | `get_cartola_from_cmf()` |
| **Líneas** | 61-70 |

**Evidencia:**

```python
# download.py:69-70
with open(temp_file_path, "wb") as temp_file:
    temp_file.write(bytearray(image_data))
```

Los bytes obtenidos del captcha se escriben directamente sin verificar que sean una imagen PNG/JPEG válida.

**Remediación:**

```python
PNG_MAGIC = b'\x89PNG'
JPEG_MAGIC = b'\xff\xd8\xff'

image_bytes = bytearray(image_data)
if not (image_bytes[:4] == PNG_MAGIC or image_bytes[:3] == JPEG_MAGIC):
    raise ValueError("Los datos del captcha no son una imagen válida")
```

---

### 5. Predicción de Captcha Usada en Nombre de Archivo Sin Sanitizar

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-22 (Path Traversal) |
| **Archivo** | `cartolas/download.py` |
| **Función** | `get_cartola_from_cmf()` / `fetch_cartola_data()` |
| **Líneas** | 77, 119 |

**Evidencia:**

```python
# download.py:77
temp_file_path.rename(error_folder / f"{prediction}.png")
# download.py:119
temp_file_path.rename(error_folder / f"{prediction}.png")
```

Si `predict()` retornara un string con caracteres de path (`../`), se podría escribir fuera del directorio. En la práctica, `captchapass` probablemente retorna solo alfanuméricos, pero no hay validación explícita.

**Remediación:**

```python
import re
if not re.match(r'^[a-zA-Z0-9]+$', prediction):
    raise ValueError(f"Predicción de captcha contiene caracteres inválidos: {prediction}")
```

---

### 6. Respuesta JSON de El Mercurio Sin Validación de Esquema

| Campo | Valor |
|-------|-------|
| **Severidad** | Baja |
| **CWE** | CWE-20 (Improper Input Validation) |
| **Archivo** | `comparador/elmer.py` |
| **Función** | `filter_elmer_data()` |
| **Líneas** | 106-139 |

**Evidencia:** Los datos JSON de El Mercurio se procesan asumiendo que tienen la estructura esperada. Un cambio en la API o una respuesta manipulada causaría excepciones no controladas (KeyError).

**Remediación:** Validar la presencia de las claves esperadas antes de procesarlas:

```python
required_keys = {"categoria", "num_categoria", "rows"}
if not required_keys.issubset(datos.keys()):
    raise ValueError(f"Respuesta de El Mercurio con estructura inesperada: {datos.keys()}")
```

---

## Puntuación de Riesgo Global

**Riesgo: 3/10**

Justificación: No existe funcionalidad de file upload. Los riesgos se limitan a archivos descargados de fuentes específicas (CMF, El Mercurio) con baja probabilidad de explotación (requiere comprometer servidores gubernamentales o ejecutar MITM).

---

## Top 5 Fixes Priorizados

| # | Fix | Impacto | Esfuerzo |
|---|-----|---------|----------|
| 1 | Sanitizar `download.suggested_filename` (Path Traversal) | Alto | Bajo |
| 2 | Agregar límite de tamaño a descargas | Medio | Bajo |
| 3 | Validar extensión y contenido del archivo descargado | Medio | Bajo |
| 4 | Sanitizar `prediction` antes de usarlo en nombres de archivo | Bajo | Bajo |
| 5 | Validar magic number de imagen captcha | Bajo | Bajo |

---

## Checklist de Controles de File Upload

| Control | Estado | Notas |
|---------|--------|-------|
| Validación de tipo de archivo (whitelist) | **No Aplica** | No hay uploads de usuario. Las descargas de CMF no validan tipo. |
| Límites de tamaño de archivo | **Falla** | `download.py:115` reconoce explícitamente que falta (`# ACA FALTA CHEQUEAR EL TAMAÑO`) |
| Sanitización de nombre de archivo | **Falla** | `download.suggested_filename` se usa sin sanitizar (`download.py:112`) |
| Integración de antivirus | **No Aplica** | No hay uploads de usuario; los archivos son CSVs de texto plano de la CMF |
| Almacenamiento fuera de webroot | **No Aplica** | No existe webroot — no es una aplicación web |
| Prevención de ejecución directa | **No Aplica** | No hay servidor web que pueda servir archivos subidos |
| Validación de MIME type | **Falla** | No se valida el tipo de contenido del archivo descargado |
| Verificación de magic number | **Falla** | Imagen captcha escrita sin verificar magic bytes (`download.py:69-70`) |
| Vulnerabilidades de librería de imágenes | **No Aplica** | No se usa PIL/Pillow para procesar imágenes |
| Protección contra ZIP bombs | **No Aplica** | No se procesan archivos ZIP/TAR en ninguna parte del código |

---

## Defensa en Profundidad

Aunque este proyecto no tiene uploads de usuario, se recomienda como buena práctica:

1. **Conexiones HTTPS verificadas:** Asegurar que las conexiones a CMF y El Mercurio usen TLS con verificación de certificados (Playwright lo hace por defecto, `requests` también).
2. **Directorio de descarga con permisos restrictivos:** Configurar `cartolas/data/txt/` con permisos `700`.
3. **Timeout en descargas:** Ya implementado via `TIMEOUT` en Playwright.
4. **Limpieza automática:** Ya implementada en `clean_txt_folder()` — elimina archivos < 1KB.
