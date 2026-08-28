from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User
from auth import require_user
import storage

router = APIRouter(prefix="/perfil", tags=["perfil"])
any_user = require_user()

ALLOWED_AVATAR = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_AVATAR_EXT = {".jpg", ".jpeg", ".png", ".webp"}

# A-3: assinaturas mágicas para avatar
_AVATAR_MAGIC = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png":  (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF", b"WEBP"),
}


def _avatar_magic_ok(data: bytes, content_type: str) -> bool:
    sigs = _AVATAR_MAGIC.get(content_type)
    if not sigs:
        return False
    head = data[:16]
    if content_type == "image/webp":
        return head.startswith(b"RIFF") and b"WEBP" in data[:16]
    return any(head.startswith(s) for s in sigs)


class PerfilOut(BaseModel):
    id: str
    name: str
    email: str
    company: str
    sector: str
    role: str
    matricula: str | None
    turno: str | None
    telefone: str | None
    avatar_url: str | None
    notif_email: bool
    notif_sms: bool
    notif_push: bool
    notif_som: str


class PerfilUpdate(BaseModel):
    matricula: str | None = None
    turno: Literal["A", "B", "C", "D"] | None = None
    telefone: str | None = None
    notif_email: bool | None = None
    notif_sms: bool | None = None
    notif_push: bool | None = None
    notif_som: Literal["none", "som1", "som2", "som3", "som4"] | None = None


@router.get("/", response_model=PerfilOut)
async def get_perfil(
    current: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == current["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return _to_out(user)


@router.patch("/", response_model=PerfilOut)
async def update_perfil(
    body: PerfilUpdate,
    current: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db)
):
    import uuid as _uuid
    result = await db.execute(select(User).where(User.id == _uuid.UUID(current["user_id"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if body.matricula is not None: user.matricula = body.matricula
    if body.turno     is not None: user.turno     = body.turno
    if body.telefone  is not None: user.telefone  = body.telefone
    if body.notif_email is not None: user.notif_email = body.notif_email
    if body.notif_sms   is not None: user.notif_sms   = body.notif_sms
    if body.notif_push  is not None: user.notif_push  = body.notif_push
    if body.notif_som   is not None: user.notif_som   = body.notif_som

    await db.commit()
    await db.refresh(user)
    return _to_out(user)


@router.post("/avatar", response_model=PerfilOut)
async def upload_avatar(
    file: UploadFile = File(...),
    current: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db)
):
    import uuid as _uuid
    if file.content_type not in ALLOWED_AVATAR:
        raise HTTPException(status_code=415, detail="Use JPEG, PNG ou WEBP")

    # A-3: valida extensão (header Content-Type é spoofável)
    try:
        storage.validate_extension(file.filename or "", ALLOWED_AVATAR_EXT)
    except ValueError:
        raise HTTPException(status_code=415, detail="Extensão não permitida para avatar.")

    # A-3: checa tamanho declarado antes de ler (mitiga DoS por RAM)
    if file.size is not None and file.size > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=413, detail="Imagem maior que 2 MB")

    buf = bytearray()
    while chunk := await file.read(1024 * 1024):
        buf.extend(chunk)
        if len(buf) > MAX_AVATAR_SIZE:
            raise HTTPException(status_code=413, detail="Imagem maior que 2 MB")
    data = bytes(buf)

    # A-3: valida assinatura mágica
    if not _avatar_magic_ok(data, file.content_type):
        raise HTTPException(status_code=415, detail="Conteúdo não corresponde a uma imagem válida.")

    result = await db.execute(select(User).where(User.id == _uuid.UUID(current["user_id"])))
    user = result.scalar_one_or_none()

    # Remove avatar antigo
    if user.avatar_url:
        storage.delete_file(user.avatar_url)

    # A-3: prefixo controlado pelo servidor (não sanitizado) + extensão validada
    ext = _ext(file.filename)
    key = storage.upload_file(
        f"{current['user_id']}{ext}",
        data,
        file.content_type,
        prefix="avatars",
    )
    user.avatar_url = key
    await db.commit()
    await db.refresh(user)
    return _to_out(user)


@router.delete("/avatar", response_model=PerfilOut)
async def delete_avatar(
    current: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db)
):
    import uuid as _uuid
    result = await db.execute(select(User).where(User.id == _uuid.UUID(current["user_id"])))
    user = result.scalar_one_or_none()
    if user.avatar_url:
        storage.delete_file(user.avatar_url)
        user.avatar_url = None
        await db.commit()
        await db.refresh(user)
    return _to_out(user)


def _to_out(u: User) -> PerfilOut:
    return PerfilOut(
        id=str(u.id), name=u.name, email=u.email,
        company=u.company, sector=u.sector, role=u.role,
        matricula=u.matricula, turno=u.turno, telefone=u.telefone,
        avatar_url=u.avatar_url,
        notif_email=u.notif_email, notif_sms=u.notif_sms, notif_push=u.notif_push,
        notif_som=u.notif_som if u.notif_som else "som1",
    )

def _ext(filename: str | None) -> str:
    if filename and "." in filename:
        return "." + filename.rsplit(".", 1)[-1].lower()
    return ".jpg"
