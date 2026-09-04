"""
Rotas de notificações.

GET  /notifications/          → lista as últimas 50 notificações do usuário logado
POST /notifications/{id}/read → marca uma notificação como lida
POST /notifications/read-all  → marca todas como lidas
GET  /notifications/unread-count → retorna contagem de não lidas

POST /notifications/comunicado → (admin) cria comunicado manual
"""
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from database import get_db
from models import Notificacao, User, UserSetor
from auth import require_user
from ws_manager import manager
import storage

router = APIRouter(prefix="/notifications", tags=["notifications"])
any_user = require_user()
only_admin = require_user(required_role="admin")
logger = logging.getLogger(__name__)

LIMIT = 50


# ── Schemas ───────────────────────────────────────────────────────────────────

class ComunicadoCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    mensagem: str | None = Field(None)
    imagem_key: str | None = Field(None)   # object_key no MinIO
    link_rota: str | None = Field(None)    # ex: /fca, /help
    # Destinatários
    destino: str = Field("todos")          # todos | setor | usuario
    setor: str | None = None
    empresa: str | None = None
    user_id: str | None = None             # para destino=usuario


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(n: Notificacao) -> dict:
    # Resolve a URL sob demanda a partir da object_key (não persiste presigned,
    # que expira e quebra com mudança de endpoint do MinIO).
    imagem_url: str | None = n.imagem_url
    if n.imagem_key:
        try:
            imagem_url = storage.get_presigned_url(n.imagem_key)
        except Exception:
            logger.exception("Falha ao gerar URL pré-assinada p/ notificação key=%s", n.imagem_key)
    return {
        "id": str(n.id),
        "tipo": n.tipo,
        "titulo": n.titulo,
        "mensagem": n.mensagem,
        "imagem_url": imagem_url,
        "link_rota": n.link_rota,
        "lida": n.lida,
        "created_at": n.created_at.isoformat(),
    }


async def _criar_notificacoes(
    db: AsyncSession,
    tipo: str,
    titulo: str,
    mensagem: str | None,
    link_rota: str | None,
    user_ids: list[uuid.UUID],
    imagem_key: str | None = None,
) -> list[str]:
    """Cria uma linha de notificação por user_id e retorna a lista de str ids para WS."""
    rows = [
        Notificacao(
            user_id=uid,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            imagem_key=imagem_key,
            link_rota=link_rota,
            lida=False,
        )
        for uid in user_ids
    ]
    for r in rows:
        db.add(r)
    await db.flush()  # necessário para ter os ids antes do commit
    return [str(uid) for uid in user_ids]


# ── Endpoints públicos ────────────────────────────────────────────────────────

@router.get("/")
async def listar(
    user: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user["user_id"])
    result = await db.execute(
        select(Notificacao)
        .where(Notificacao.user_id == uid)
        .order_by(Notificacao.created_at.desc())
        .limit(LIMIT)
    )
    return [_fmt(n) for n in result.scalars().all()]


@router.get("/unread-count")
async def unread_count(
    user: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user["user_id"])
    result = await db.execute(
        select(func.count()).select_from(Notificacao).where(
            Notificacao.user_id == uid,
            Notificacao.lida == False,  # noqa: E712
        )
    )
    return {"count": result.scalar() or 0}


@router.post("/{notif_id}/read")
async def marcar_lida(
    notif_id: str,
    user: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        nid = uuid.UUID(notif_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="ID inválido")
    uid = uuid.UUID(user["user_id"])
    await db.execute(
        update(Notificacao)
        .where(Notificacao.id == nid, Notificacao.user_id == uid)
        .values(lida=True)
    )
    await db.commit()
    return {"ok": True}


@router.post("/read-all")
async def marcar_todas_lidas(
    user: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user["user_id"])
    await db.execute(
        update(Notificacao)
        .where(Notificacao.user_id == uid, Notificacao.lida == False)  # noqa: E712
        .values(lida=True)
    )
    await db.commit()
    return {"ok": True}


# ── Comunicado admin ──────────────────────────────────────────────────────────

@router.post("/comunicado", status_code=201)
async def criar_comunicado(
    body: ComunicadoCreate,
    user: dict = Depends(only_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin cria comunicado manual (nova funcionalidade, aviso, etc.)."""
    # A imagem do comunicado é armazenada como object_key (NÃO como presigned URL,
    # que expira e quebra quando o endpoint do MinIO muda). A URL é resolvida sob
    # demanda em GET /notifications/ via _fmt → storage.get_presigned_url.

    # Resolve destinatários
    q = select(User).where(User.is_active == True)  # noqa: E712
    if body.destino == "setor" and body.setor and body.empresa:
        # Considera usuários com o setor/empresa em qualquer vínculo do perfil
        q = (
            q.join(UserSetor, UserSetor.user_id == User.id)
            .where(UserSetor.setor == body.setor, UserSetor.empresa == body.empresa)
            .distinct()
        )
    elif body.destino == "usuario" and body.user_id:
        q = q.where(User.id == uuid.UUID(body.user_id))
    # 'todos' → sem filtro adicional

    result = await db.execute(q)
    users = result.scalars().all()
    if not users:
        raise HTTPException(status_code=404, detail="Nenhum destinatário encontrado")

    user_ids = [u.id for u in users]
    notif_user_str_ids = await _criar_notificacoes(
        db,
        tipo="comunicado",
        titulo=body.titulo,
        mensagem=body.mensagem,
        link_rota=body.link_rota,
        user_ids=user_ids,
        imagem_key=body.imagem_key,
    )
    await db.commit()

    # Sinaliza via WS para usuários online
    await manager.broadcast_notif(notif_user_str_ids)
    return {"ok": True, "total": len(user_ids)}
