"""Storage helper dedicado ao bucket de onboarding (fca-arquivos)."""
import os
import uuid
import datetime
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ENDPOINT   = os.getenv("MINIO_ENDPOINT", "minio:9000")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
ONBOARDING_BUCKET = "fca-arquivos"
PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg"}
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB


def _endpoint_url() -> str:
    if ENDPOINT.startswith("http://") or ENDPOINT.startswith("https://"):
        return ENDPOINT
    return f"http://{ENDPOINT}"


def _client():
    return boto3.client(
        "s3",
        endpoint_url=_endpoint_url(),
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
        config=Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 1}),
    )


def ensure_onboarding_bucket():
    s3 = _client()
    try:
        s3.head_bucket(Bucket=ONBOARDING_BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=ONBOARDING_BUCKET)


def upload_video(filename: str, data: bytes, content_type: str) -> str:
    """Faz upload do vídeo e retorna a object_key."""
    today = datetime.date.today()
    uid = str(uuid.uuid4())[:8]
    safe_name = filename.replace(" ", "_")
    key = f"videos/{today.year}/{today.month:02d}/{uid}_{safe_name}"

    s3 = _client()
    s3.put_object(Bucket=ONBOARDING_BUCKET, Key=key, Body=data, ContentType=content_type)
    return key


def get_video_presigned_url(key: str, expires: int = 7200) -> str:
    """Gera URL pré-assinada temporária para streaming do vídeo (2h)."""
    s3 = _client()
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": ONBOARDING_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
    # Substitui host interno pelo PUBLIC_URL
    import re
    url = re.sub(r"http://[^/]+", PUBLIC_URL.rstrip("/"), url, count=1)
    return url


def delete_video(key: str):
    s3 = _client()
    try:
        s3.delete_object(Bucket=ONBOARDING_BUCKET, Key=key)
    except ClientError:
        pass
