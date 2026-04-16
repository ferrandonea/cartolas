import logging
from typing import TYPE_CHECKING

from cartolas import config

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
