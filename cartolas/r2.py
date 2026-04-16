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


def upload_to_r2(path: Path) -> bool:
    """Sube un archivo Parquet anual a Cloudflare R2 bajo el prefijo ``yearly/``.

    Usa hasta 3 intentos con ``retry_function``. Si el cliente R2 no está
    disponible o falla tras los reintentos, retorna ``False`` y emite un
    warning; nunca lanza excepción.

    Args:
        path: Ruta local del archivo a subir.

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

    key = f"yearly/{path.name}"

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
