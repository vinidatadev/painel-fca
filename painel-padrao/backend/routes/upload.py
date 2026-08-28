from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from database import get_db
from models import FCA, FCAEtapa, HelpTicket, User as UserModel
from auth import require_user
import storage

router = APIRouter(prefix="/upload", tags=["upload"])
any_user = require_user()


@router.post("/", status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    _: dict = Depends(any_user)
):
    if file.content_type not in storage.ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Tipo não permitido. Use JPEG, PNG, WEBP ou PDF.")

    # A-3: valida extensão do filename (Content-Type do header é spoofável)
    try:
        storage.validate_extension(file.filename or "")
    except ValueError:
        raise HTTPException(status_code=415, detail="Extensão não permitida.")

    # A-3: checa tamanho ANTES de ler o arquivo inteiro (mitiga DoS por RAM).
    declared = file.size
    if declared is not None and declared > storage.MAX_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo maior que 20 MB.")

    # Lê em chunks respeitando o limite, evitando carregar arquivos enormes
    buf = bytearray()
    remaining = storage.MAX_SIZE + 1
    while chunk := await file.read(1024 * 1024):
        buf.extend(chunk)
        if len(buf) > storage.MAX_SIZE:
            raise HTTPException(status_code=413, detail="Arquivo maior que 20 MB.")
    data = bytes(buf)

    # A-3: valida assinatura (magic bytes) — não confia só no Content-Type
    if not _magic_ok(data, file.content_type):
        raise HTTPException(status_code=415, detail="Conteúdo não corresponde ao tipo declarado.")

    safe_name = storage.sanitize_filename(file.filename or "arquivo")
    key = storage.upload_file(safe_name, data, file.content_type)
    return {
        "object_key": key,
        "filename": safe_name,
        "size_bytes": len(data),
        "content_type": file.content_type,
    }


# A-3: assinaturas mágicas para validar o conteúdo real do arquivo
_MAGIC = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png":  (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF", b"WEBP"),
    "application/pdf": (b"%PDF",),
}


def _magic_ok(data: bytes, content_type: str) -> bool:
    sigs = _MAGIC.get(content_type)
    if not sigs:
        return False
    head = data[:16]
    if content_type == "image/webp":
        return head.startswith(b"RIFF") and b"WEBP" in data[:16]
    return any(head.startswith(s) for s in sigs)


async def _pode_acessar_key(object_key: str, current: dict, db) -> bool:
    """
    Verifica se o usuário autenticado pode acessar a object_key:
      - Avatar: a key contém 'avatars/{seu_user_id}' → só o dono
      - Anexo de FCA: a key está em FCA.anexo_urls e o usuário tem _can_view
      - Anexo de Help Ticket: a key está em HelpTicket.anexo_keys e o usuário
        é admin ou o criador do ticket
    Não encontrar a key em nenhum lugar → nega (fail-closed).
    """
    uid = current["user_id"]

    # 1) Avatar — substring 'avatars/<user_id>'
    if f"avatars/{uid}" in object_key:
        # Garante que não haja avatar de outro user "escondido" usando o
        # prefixo do usuário corrente: o user_id deve estar logo após 'avatars/'
        import re
        m = re.search(r"avatars/([0-9a-fA-F-]{36})", object_key)
        if m and m.group(1) == uid:
            return True
        return False

    # 2) Anexo de FCA — FCA.anexo_urls (array) ou anexo_url (legado escalar)
    fca_q = (
        select(FCA)
        .options(selectinload(FCA.etapas))
        .where(or_(FCA.anexo_urls.any(object_key), FCA.anexo_url == object_key))
    )
    result = await db.execute(fca_q)
    fcas = result.scalars().unique().all()
    if fcas:
        from routes.fcas import _can_view
        for fca in fcas:
            if _can_view(fca, fca.etapas, current):
                return True
        return False

    # 3) Anexo de Help Ticket
    ticket_q = select(HelpTicket).where(HelpTicket.anexo_keys.any(object_key))
    t_result = await db.execute(ticket_q)
    tickets = t_result.scalars().all()
    if tickets:
        if current["role"] == "admin":
            return True
        for t in tickets:
            if str(t.created_by) == uid:
                return True
        return False

    # Objeto existe no MinIO mas não está referenciado no banco → nega
    return False


@router.get("/{object_key:path}/url")
async def get_presigned_url(
    object_key: str,
    current: dict = Depends(any_user),
    db=Depends(get_db),
):
    if not storage.object_exists(object_key):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    if not await _pode_acessar_key(object_key, current, db):
        raise HTTPException(status_code=403, detail="Acesso negado a este arquivo")

    url = storage.get_presigned_url(object_key)
    return {"url": url, "expires_in_seconds": 3600}
