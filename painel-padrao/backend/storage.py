import os
import uuid
import datetime
import boto3
from botocore.exceptions import ClientError

ENDPOINT   = os.getenv("MINIO_ENDPOINT", "minio:9000")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
BUCKET     = os.getenv("MINIO_BUCKET", "fca-anexos")
PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")

# Monta a URL do endpoint: se já vier com protocolo, usa como está; senão adiciona http://
def _endpoint_url() -> str:
    if ENDPOINT.startswith("http://") or ENDPOINT.startswith("https://"):
        return ENDPOINT
    return f"http://{ENDPOINT}"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_SIZE = 20 * 1024 * 1024  # 20 MB


def _client():
    return boto3.client(
        "s3",
        endpoint_url=_endpoint_url(),
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
    )


def ensure_bucket():
    s3 = _client()
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=BUCKET)


def upload_file(filename: str, data: bytes, content_type: str) -> str:
    """Faz upload e retorna a object_key."""
    today = datetime.date.today()
    uid = str(uuid.uuid4())[:8]
    safe_name = filename.replace(" ", "_")
    key = f"{today.year}/{today.month:02d}/{today.day:02d}/{uid}_{safe_name}"

    s3 = _client()
    s3.put_object(Bucket=BUCKET, Key=key, Body=data, ContentType=content_type)
    return key


def get_presigned_url(key: str, expires: int = 3600) -> str:
    """Gera URL pré-assinada temporária. Substitui host interno pelo PUBLIC_URL."""
    s3 = _client()
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": key},
        ExpiresIn=expires,
    )
    # O endpoint interno (minio:9000) não é acessível pelo browser.
    # Substitui pelo PUBLIC_URL configurado no .env
    internal = _endpoint_url()
    if PUBLIC_URL and url.startswith(internal):
        url = url.replace(internal, PUBLIC_URL, 1)
    return url


def object_exists(key: str) -> bool:
    s3 = _client()
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except ClientError:
        return False


def delete_file(key: str):
    s3 = _client()
    try:
        s3.delete_object(Bucket=BUCKET, Key=key)
    except ClientError:
        pass
