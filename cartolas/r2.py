import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cartolas import config
from utiles.decorators import retry_function

if TYPE_CHECKING:
    import boto3 as boto3_type

logger = logging.getLogger(__name__)


def get_r2_client():
    """Construye y retorna un cliente boto3 apuntando al endpoint de Cloudflare R2.

    Retorna None si alguna de las credenciales requeridas no está configurada en .env,
    emitiendo un warning en el log.

    Returns:
        Cliente boto3 S3 configurado para R2, o None si faltan credenciales.
    """
    import boto3

    required = {
        "R2_ENDPOINT_URL": config.R2_ENDPOINT_URL,
        "R2_BUCKET_NAME": config.R2_BUCKET_NAME,
        "R2_ACCESS_KEY_ID": config.R2_ACCESS_KEY_ID,
        "R2_SECRET_ACCESS_KEY": config.R2_SECRET_ACCESS_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        logger.warning(
            "Credenciales R2 no configuradas: %s. "
            "Agrega las variables al .env para habilitar el backup a R2.",
            ", ".join(missing),
        )
        return None

    return boto3.client(
        "s3",
        endpoint_url=config.R2_ENDPOINT_URL,
        aws_access_key_id=config.R2_ACCESS_KEY_ID,
        aws_secret_access_key=config.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def sync_all_to_r2(base_dir: Path) -> bool:
    """Sube todos los parquets anuales existentes en *base_dir* a Cloudflare R2.

    Itera todos los archivos ``cartolas_YYYY.parquet`` en *base_dir* y llama
    :func:`upload_to_r2` para cada uno. Permite poblar el bucket con el
    historial completo la primera vez.

    Si el cliente R2 no está disponible (faltan credenciales), emite un
    warning y retorna ``False`` sin lanzar excepción.

    Args:
        base_dir: Directorio que contiene los archivos ``cartolas_YYYY.parquet``.

    Returns:
        ``True`` si todos los archivos se subieron correctamente, ``False`` si
        alguno falló o el cliente no estaba disponible.
    """
    parquets = sorted(base_dir.glob("cartolas_*.parquet"))
    if not parquets:
        logger.info("sync_all_to_r2: no hay archivos en '%s', nada que sincronizar.", base_dir)
        return True

    client = get_r2_client()
    if client is None:
        logger.warning(
            "sync_all_to_r2: cliente R2 no disponible (faltan credenciales). "
            "Agrega las variables al .env para habilitar el backup a R2."
        )
        return False

    key_prefix = base_dir.name
    failed = []
    for path in parquets:
        logger.info("Subiendo a R2: %s …", path.name)
        if not upload_to_r2(path, key_prefix=key_prefix):
            failed.append(path.name)

    if failed:
        logger.warning(
            "sync_all_to_r2: %d archivo(s) no se pudieron subir: %s",
            len(failed),
            ", ".join(failed),
        )
        return False
    return True


def download_from_r2(year: int, dest_dir: Path) -> bool:
    """Descarga el parquet anual de un año específico desde Cloudflare R2.

    Args:
        year: Año a descargar (ej. 2024).
        dest_dir: Directorio local donde guardar el archivo.

    Returns:
        True si la descarga fue exitosa, False si el cliente no está disponible
        o el archivo no existe en R2.
    """
    client = get_r2_client()
    if client is None:
        logger.warning(
            "download_from_r2: cliente R2 no disponible (faltan credenciales). "
            "Agrega las variables al .env para habilitar la descarga desde R2."
        )
        return False

    filename = f"cartolas_{year}.parquet"
    key = f"yearly/{filename}"
    dest_path = dest_dir / filename

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        client.download_file(config.R2_BUCKET_NAME, key, str(dest_path))
        logger.info("Archivo descargado desde R2: %s → %s", key, dest_path)
        return True
    except client.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ("404", "NoSuchKey"):
            logger.warning("Archivo no encontrado en R2: %s", key)
        else:
            logger.warning("Error al descargar '%s' desde R2: %s", key, e)
        return False
    except Exception as e:
        logger.warning("Error al descargar '%s' desde R2: %s", key, e)
        return False


def download_all_from_r2(dest_dir: Path) -> bool:
    """Descarga todos los parquets anuales disponibles en R2 al directorio destino.

    Lista los objetos bajo el prefijo ``yearly/`` en el bucket y descarga
    cada uno con :func:`download_from_r2`.

    Args:
        dest_dir: Directorio local donde guardar los archivos.

    Returns:
        True si todos los archivos se descargaron correctamente, False si
        alguno falló o el cliente no estaba disponible.
    """
    client = get_r2_client()
    if client is None:
        logger.warning(
            "download_all_from_r2: cliente R2 no disponible (faltan credenciales). "
            "Agrega las variables al .env para habilitar la descarga desde R2."
        )
        return False

    prefix = "yearly/"
    try:
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=config.R2_BUCKET_NAME, Prefix=prefix)
        keys = [
            obj["Key"]
            for page in pages
            for obj in page.get("Contents", [])
        ]
    except Exception as e:
        logger.warning("Error al listar objetos en R2 bajo '%s': %s", prefix, e)
        return False

    if not keys:
        logger.info("download_all_from_r2: no se encontraron archivos en R2 bajo '%s'.", prefix)
        return True

    dest_dir.mkdir(parents=True, exist_ok=True)
    failed = []
    for key in keys:
        filename = key.split("/")[-1]
        dest_path = dest_dir / filename
        try:
            client.download_file(config.R2_BUCKET_NAME, key, str(dest_path))
            logger.info("Descargado desde R2: %s → %s", key, dest_path)
        except Exception as e:
            logger.warning("Error al descargar '%s' desde R2: %s", key, e)
            failed.append(key)

    if failed:
        logger.warning(
            "download_all_from_r2: %d archivo(s) no se pudieron descargar: %s",
            len(failed),
            ", ".join(failed),
        )
        return False
    return True


def upload_to_r2(path: Path, key_prefix: str = "yearly") -> bool:
    """Sube un archivo Parquet anual a Cloudflare R2 bajo el prefijo indicado.

    Usa hasta 3 intentos con ``retry_function``. Si el cliente R2 no está
    disponible o falla tras los reintentos, retorna ``False`` y emite un
    warning; nunca lanza excepción.

    Args:
        path: Ruta local del archivo a subir.
        key_prefix: Prefijo del objeto en R2 (ej. ``"yearly"`` o
            ``"custom/path"``). Se deriva del directorio base del dataset
            para que distintos datasets no se sobreescriban entre sí.

    Returns:
        True si la subida fue exitosa, False en caso contrario.
    """
    client = get_r2_client()
    if client is None:
        logger.warning(
            "No se puede subir '%s' a R2: cliente no disponible (faltan credenciales).",
            path.name,
        )
        return False

    key = f"{key_prefix}/{path.name}"

    def _do_upload():
        client.upload_file(str(path), config.R2_BUCKET_NAME, key)

    _do_upload_with_retry = retry_function(_do_upload, max_attempts=3, delay=5)

    try:
        _do_upload_with_retry()
        logger.info("Archivo subido a R2: %s", key)
        return True
    except Exception as e:
        logger.warning(
            "Fallo al subir '%s' a R2 tras 3 intentos: %s",
            path.name,
            e,
        )
        return False
