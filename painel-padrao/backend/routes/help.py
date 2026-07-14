import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from database import get_db
from models import HelpTicket, HelpMensagem
from auth import require_user
from ws_manager import manager
import storage

router = APIRouter(prefix="/help", tags=["help"])
any_user = require_user()
only_admin = require_user(required_role="admin")

VALID_STATUS = {"aberto", "em_andamento", "resolvido", "fechado"}
MAX_ANEXOS = 5


# ── Schemas ───────────────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    descricao: str = Field(..., min_length=5)
    anexo_keys: list[str] = Field(default_factory=list)


class MensagemCreate(BaseModel):
    texto: str = Field(..., min_length=1)


class StatusUpdate(BaseModel):
    status: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_anexos(keys: list[str] | None) -> list[dict]:
    """Gera URLs pré-assinadas para cada anexo. Retorna lista de {key, url, is_image}."""
    if not keys:
        return []
    result = []
    for k in keys:
        try:
            url = storage.get_presigned_url(k)
        except Exception:
            url = None
        lower = k.lower()
        is_image = any(lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp"))
        result.append({"key": k, "url": url, "is_image": is_image})
    return result


def _fmt_ticket(t: HelpTicket) -> dict:
    return {
        "id": str(t.id),
        "titulo": t.titulo,
        "descricao": t.descricao,
        "anexos": _resolve_anexos(t.anexo_keys),
        "status": t.status,
        "created_by": {"id": str(t.criado_por.id), "name": t.criado_por.name, "email": t.criado_por.email},
        "created_at": t.created_at.isoformat(),
        "updated_at": t.updated_at.isoformat(),
        "mensagens": [
            {
                "id": str(m.id),
                "texto": m.texto,
                "autor": {"id": str(m.autor.id), "name": m.autor.name, "role": m.autor.role},
                "created_at": m.created_at.isoformat(),
            }
            for m in (t.mensagens or [])
        ],
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def criar_ticket(
    body: TicketCreate,
    user: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    if len(body.anexo_keys) > MAX_ANEXOS:
        raise HTTPException(status_code=422, detail=f"Máximo de {MAX_ANEXOS} anexos por ticket.")
    ticket = HelpTicket(
        titulo=body.titulo,
        descricao=body.descricao,
        anexo_keys=body.anexo_keys or None,
        created_by=uuid.UUID(user["user_id"]),
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    await manager.broadcast("help_ticket_novo", destinatarios=None)
    return {"id": str(ticket.id)}


@router.get("/")
async def listar_tickets(
    user: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(HelpTicket)
        .options(
            selectinload(HelpTicket.criado_por),
            selectinload(HelpTicket.mensagens).selectinload(HelpMensagem.autor),
        )
        .order_by(HelpTicket.created_at.desc())
    )
    if user["role"] != "admin":
        q = q.where(HelpTicket.created_by == uuid.UUID(user["user_id"]))

    result = await db.execute(q)
    return [_fmt_ticket(t) for t in result.scalars().all()]


@router.get("/{ticket_id}")
async def detalhe_ticket(
    ticket_id: str,
    user: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    t = await _get_ticket(ticket_id, db)
    if user["role"] != "admin" and str(t.created_by) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return _fmt_ticket(t)


@router.post("/{ticket_id}/mensagens", status_code=201)
async def responder_ticket(
    ticket_id: str,
    body: MensagemCreate,
    user: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    t = await _get_ticket(ticket_id, db)
    if user["role"] != "admin" and str(t.created_by) != user["user_id"]:
        raise HTTPException(status_code=403, detail="Acesso negado")

    msg = HelpMensagem(
        ticket_id=t.id,
        texto=body.texto,
        autor_id=uuid.UUID(user["user_id"]),
    )
    db.add(msg)

    if user["role"] == "admin" and t.status == "aberto":
        t.status = "em_andamento"
    t.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await manager.broadcast("help_ticket_atualizado", destinatarios=None)
    return {"ok": True}


@router.patch("/{ticket_id}/status")
async def atualizar_status(
    ticket_id: str,
    body: StatusUpdate,
    user: dict = Depends(only_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.status not in VALID_STATUS:
        raise HTTPException(status_code=422, detail=f"Status inválido. Use: {VALID_STATUS}")
    t = await _get_ticket(ticket_id, db)
    t.status = body.status
    t.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await manager.broadcast("help_ticket_atualizado", destinatarios=None)
    return {"ok": True}


# ── Util ──────────────────────────────────────────────────────────────────────

async def _get_ticket(ticket_id: str, db: AsyncSession) -> HelpTicket:
    try:
        tid = uuid.UUID(ticket_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="ID inválido")
    result = await db.execute(
        select(HelpTicket)
        .options(
            selectinload(HelpTicket.criado_por),
            selectinload(HelpTicket.mensagens).selectinload(HelpMensagem.autor),
        )
        .where(HelpTicket.id == tid)
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    return t
