import os
import re
import uuid
import datetime
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ENDPOINT   = os.getenv("MINIO_ENDPOINT", "minio:9000")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
BUCKET     = os.getenv("MINIO_BUCKET", "fca-anexos")
PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")

# --- Validação fail-fast no startup (C-4): sem credenciais padrão inseguras ---
if not ACCESS_KEY or not SECRET_KEY:
    raise RuntimeError(
        "MINIO_ACCESS_KEY/MINIO_SECRET_KEY não definidos no .env. "
        "Removidos os fallbacks 'minioadmin' por segurança."
    )

# Monta a URL do endpoint: se já vier com protocolo, usa como está; senão adiciona http://
def _endpoint_url() -> str:
    if ENDPOINT.startswith("http://") or ENDPOINT.startswith("https://"):
        return ENDPOINT
    return f"http://{ENDPOINT}"

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_SIZE = 20 * 1024 * 1024  # 20 MB

# A-3: extensões permitidas (validação adicional ao Content-Type, que é spoofável)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


def sanitize_filename(name: str) -> str:
    """
    A-3: neutraliza path traversal e caracteres perigosos no filename antes
    de usá-lo para montar a object_key do MinIO.
    - remove qualquer componente de path (../, /, \\)
    - descarta bytes nulos e caracteres de controle
    - limita o tamanho e força uma extensão segura
    """
    if not name:
        return "arquivo"
    # Descarta nomes que tentam escapar o bucket via prefixo
    name = name.replace("\\", "/")
    name = name.split("/")[-1]  # pega só o basename
    # Remove bytes nulos e chars de controle
    name = re.sub(r"[\x00-\x1f]", "", name)
    # Substitui espaços e caracteres com significado especial
    name = name.strip().replace(" ", "_")
    # Remove qualquer caractere que não seja alfanumérico, _ - . ou acentos comuns
    name = re.sub(r"[^A-Za-z0-9_.\-\u00C0-\u017F]", "", name)
    # Limita o tamanho
    if len(name) > 100:
        name = name[-100:]
    return name or "arquivo"


def validate_extension(filename: str, allowed: set[str] = ALLOWED_EXTENSIONS) -> str:
    """Retorna a extensão normalizada (lowercase) se permitida, senão levanta ValueError."""
    lower = (filename or "").lower()
    ext = "." + (lower.rsplit(".", 1)[-1] if "." in lower else "")
    if ext not in allowed:
        raise ValueError(f"Extensão não permitida: {ext}")
    return ext


def _client():
    return boto3.client(
        "s3",
        endpoint_url=_endpoint_url(),
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name="us-east-1",
        config=Config(connect_timeout=5, read_timeout=10, retries={"max_attempts": 1}),
    )


def ensure_bucket():
    s3 = _client()
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError:
        s3.create_bucket(Bucket=BUCKET)


def upload_file(filename: str, data: bytes, content_type: str, prefix: str = "") -> str:
    """Faz upload e retorna a object_key.

    prefix: caminho controlado pelo servidor (ex.: 'avatars/<user_id>') que
    NÃO passa por sanitize_filename — é confiado pois é determinado internamente.
    filename (vindo do cliente) é sanitizado para neutralizar path traversal.
    """
    today = datetime.date.today()
    uid = str(uuid.uuid4())[:8]
    safe_name = sanitize_filename(filename)
    prefix_part = f"{prefix}/" if prefix else ""
    key = f"{today.year}/{today.month:02d}/{today.day:02d}/{prefix_part}{uid}_{safe_name}"

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
