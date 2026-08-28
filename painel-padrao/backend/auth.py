import os
import httpx
import jwt
import bcrypt
import time
import logging
from datetime import datetime, timedelta, timezone
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.backends import default_backend
from base64 import b64decode
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TENANT_ID    = os.getenv("AZURE_TENANT_ID")
CLIENT_ID    = os.getenv("AZURE_CLIENT_ID")
JWT_SECRET   = os.getenv("JWT_SECRET")          # segredo para tokens locais
JWT_EXPIRE_H = int(os.getenv("JWT_EXPIRE_H", "8"))

# --- Validação fail-fast no startup (C-4) ---
# Placeholder fraco que NUNCA deve chegar à produção.
_JWT_PLACEHOLDERS = {
    "",
    "troque-por-um-segredo-forte-aqui",
    "changeme",
    "secret",
}
if not JWT_SECRET or JWT_SECRET in _JWT_PLACEHOLDERS or len(JWT_SECRET) < 16:
    raise RuntimeError(
        "JWT_SECRET ausente, placeholder ou muito curto (<16 caracteres). "
        "Defina um segredo forte no .env antes de iniciar o backend."
    )
if not TENANT_ID:
    raise RuntimeError("AZURE_TENANT_ID não definido no .env")
if not CLIENT_ID:
    raise RuntimeError("AZURE_CLIENT_ID não definido no .env")

JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"

bearer_scheme = HTTPBearer()

# ---------- helpers de senha ----------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

# ---------- JWT local ----------

def create_local_token(user_id: str, email: str, name: str, role: str,
                       company: str = "", sector: str = "") -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "name": name,
        "role": role,
        "company": company,
        "sector": sector,
        "provider": "local",
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_H)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def _decode_local_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        return None

# ---------- Azure JWKS — cache com TTL de 1 hora ----------

_JWKS_TTL = 3600  # segundos
_jwks_cache: dict[str, tuple[object, float]] = {}

async def _get_azure_public_key(kid: str):
    entry = _jwks_cache.get(kid)
    if entry and time.time() - entry[1] < _JWKS_TTL:
        return entry[0]

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(JWKS_URL)
        resp.raise_for_status()
    for key in resp.json().get("keys", []):
        if key.get("kid") == kid:
            x5c = key.get("x5c", [])
            if x5c:
                cert = load_der_x509_certificate(b64decode(x5c[0]), default_backend())
                pub = cert.public_key()
                _jwks_cache[kid] = (pub, time.time())
                return pub
    return None

async def _decode_azure_token(token: str) -> dict | None:
    try:
        header = jwt.get_unverified_header(token)
        pub = await _get_azure_public_key(header["kid"])
        if not pub:
            return None
        return jwt.decode(
            token, pub, algorithms=["RS256"],
            audience=CLIENT_ID,
            issuer=f"https://login.microsoftonline.com/{TENANT_ID}/v2.0"
        )
    except Exception:
        return None

# ---------- Dependência principal ----------

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = None   # injetado via wrapper abaixo
) -> dict:
    raise NotImplementedError  # nunca chamado diretamente


class AuthError(Exception):
    """Levantada quando o token é inválido/expirado ou o usuário não tem acesso."""


ALLOWED_ALGS = {"HS256", "RS256"}


async def authenticate_token(token: str, db: AsyncSession, client_ip: str | None = None) -> tuple[object, str]:
    """
    Valida um token JWT local (HS256) ou Azure AD (RS256) e carrega o usuário
    correspondente na tabela users.

    Retorna (user_obj, provider).  Lança AuthError em caso de falha.
    Esta função é compartilhada pela dependência HTTP (require_user) e pelo
    endpoint WebSocket, garantindo a mesma lógica de validação em ambos.
    """
    from models import User

    def _log(reason: str, level: int = logging.WARNING):
        logger.log(level, "[AUTH] ip=%s reason=%s", client_ip or "-", reason)

    # M-1: lê o header e rejeita explicitamente algoritmo inválido/ausente
    # (em especial "none" e qualquer algoritmo que não HS256/RS256).
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "")
    except Exception as e:
        _log(f"header_ilegivel ({e})")
        raise AuthError("Token ilegível")

    if not alg or alg.lower() == "none":
        _log("alg_none_rejeitado")
        raise AuthError("Algoritmo de token não permitido")
    if alg not in ALLOWED_ALGS:
        _log(f"alg_nao_permitido={alg}")
        raise AuthError(f"Algoritmo de token não permitido: {alg}")

    if alg == "HS256":
        payload = _decode_local_token(token)
        if not payload:
            _log("local_invalido_ou_expirado")
            raise AuthError("Token local inválido ou expirado")
        email    = payload.get("email")
        provider = "local"
    else:
        # Token Azure (RS256)
        payload = await _decode_azure_token(token)
        if not payload:
            _log("azure_invalido_ou_expirado")
            raise AuthError("Token Azure inválido ou expirado")
        email = (
            payload.get("preferred_username")
            or payload.get("email")
            or payload.get("upn")
        )
        provider = "microsoft"

    if not email:
        _log("token_sem_email")
        raise AuthError("Token sem e-mail válido")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        _log(f"usuario_inativo_ou_inexistente email={email}")
        raise AuthError("Acesso não autorizado")

    # Usuário Microsoft não usa senha local — garante que o flag não fica preso
    if provider == "microsoft" and user.must_change_password:
        user.must_change_password = False
        await db.commit()

    return user, provider


def require_user(required_role: str | None = None):
    """
    Retorna uma dependência FastAPI que:
    1. Aceita token Azure (idToken) ou token local (JWT HS256)
    2. Verifica se o usuário existe e está ativo na tabela users
    3. Opcionalmente exige um role mínimo
    """
    from database import get_db  # import local evita circular

    # Rotas isentas das travas de primeiro acesso (C-3).
    # Observação: /api/auth/me precisa ficar livre para que o frontend
    # descubra o perfil e os flags após login (especial Microsoft/SSO).
    _MUST_CHANGE_EXEMPT = {"/api/auth/me", "/api/auth/change-password"}
    _ONBOARDING_PREFIXES = ("/api/onboarding", "/api/perfil")
    _ONBOARDING_EXEMPT = {"/api/auth/me", "/api/auth/change-password"}

    async def _dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: AsyncSession = Depends(get_db)
    ) -> dict:
        credentials_exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

        token = credentials.credentials
        client_ip = request.client.host if request.client else None

        try:
            user, provider = await authenticate_token(token, db, client_ip)
        except AuthError:
            raise credentials_exc

        if required_role == "admin" and user.role != "admin":
            logger.warning(
                "[AUTH] ip=%s user=%s rota=%s razao=rbac_admin_negado",
                client_ip or "-", user.email, request.url.path,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente"
            )

        # ── C-3: Travas rígidas de primeiro acesso ──────────────────────────
        path = request.url.path

        # Trava 1: troca de senha obrigatória (somente contas locais; contas
        # Microsoft não possuem senha local, então o flag não se aplica).
        if (
            user.auth_provider == "local"
            and user.must_change_password
            and path not in _MUST_CHANGE_EXEMPT
        ):
            logger.warning(
                "[AUTH] ip=%s user=%s rota=%s razao=must_change_password",
                client_ip or "-", user.email, path,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Troca de senha obrigatória antes de usar o sistema",
                headers={"X-Reason": "must_change_password"},
            )

        # Trava 2: onboarding incompleto (admin é isento, conforme UX do
        # frontend; demais usuários só liberam rotas de onboarding/perfil/me).
        if (
            user.role != "admin"
            and not user.onboarding_completed
            and path not in _ONBOARDING_EXEMPT
            and not any(path.startswith(p) for p in _ONBOARDING_PREFIXES)
        ):
            # Verifica dinamicamente se há vídeos ativos — se não houver,
            # marca o onboarding como completo e libera o acesso.
            from models import OnboardingVideo
            total_result = await db.execute(
                select(OnboardingVideo).where(OnboardingVideo.ativo == True)
            )
            if not total_result.scalars().all():
                user.onboarding_completed = True
                await db.commit()
            else:
                logger.warning(
                    "[AUTH] ip=%s user=%s rota=%s razao=onboarding_incompleto",
                    client_ip or "-", user.email, path,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Conclua o onboarding antes de usar o sistema",
                    headers={"X-Reason": "onboarding_incompleto"},
                )

        return {
            "user_id": str(user.id),
            "email": str(user.email),
            "name": user.name,
            "role": user.role,
            "company": user.company,
            "sector": user.sector,
            "provider": provider,
            "acesso_relatorio": user.acesso_relatorio,
        }

    return _dependency
