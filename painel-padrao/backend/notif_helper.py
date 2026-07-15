"""
Helpers para criar notificações automáticas a partir de eventos do sistema.
Importado por routes/fcas.py e routes/help.py.
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import Notificacao, User, FCA, FCAEtapa, HelpTicket
from ws_manager import manager


async def _uids_envolvidos_fca(db: AsyncSession, fca: FCA) -> list[uuid.UUID]:
    """Retorna IDs de usuários que devem ser notificados sobre um FCA."""
    ids: set[uuid.UUID] = set()
    # quem criou
    ids.add(fca.created_by)
    # usuários das etapas
    result = await db.execute(
        select(FCAEtapa).where(FCAEtapa.fca_id == fca.id)
    )
    etapas = result.scalars().all()
    setores = {(e.setor, e.empresa) for e in etapas}
    if setores:
        q = select(User).where(User.is_active == True)  # noqa: E712
        from sqlalchemy import or_, and_
        conds = [and_(User.sector == s, User.company == e) for s, e in setores]
        q = q.where(or_(*conds))
        res = await db.execute(q)
        for u in res.scalars().all():
            ids.add(u.id)
    return list(ids)


async def _inserir(
    db: AsyncSession,
    tipo: str,
    titulo: str,
    mensagem: str | None,
    link_rota: str | None,
    user_ids: list[uuid.UUID],
) -> list[str]:
    """Insere linhas de notificação e retorna lista de str(user_id) para WS."""
    for uid in user_ids:
        db.add(Notificacao(
            user_id=uid,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            link_rota=link_rota,
            lida=False,
        ))
    return [str(uid) for uid in user_ids]


# ── FCAs ──────────────────────────────────────────────────────────────────────

async def notif_fca_criado(db: AsyncSession, fca: FCA):
    uids = await _uids_envolvidos_fca(db, fca)
    # Quem criou não precisa ser notificado — ele mesmo abriu o FCA
    uids = [uid for uid in uids if uid != fca.created_by]
    if not uids:
        return
    str_ids = await _inserir(
        db, "fca", f"Novo FCA: {fca.cod_fca}",
        fca.causa, f"/fca/{fca.id}", uids,
    )
    await manager.broadcast_notif(str_ids)


async def notif_fca_atualizado(db: AsyncSession, fca: FCA, acao: str, autor_nome: str, autor_id: uuid.UUID | None = None):
    uids = await _uids_envolvidos_fca(db, fca)
    if autor_id:
        uids = [uid for uid in uids if uid != autor_id]
    if not uids:
        return
    str_ids = await _inserir(
        db, "fca", f"FCA {fca.cod_fca} atualizado",
        f"{acao} por {autor_nome}", f"/fca/{fca.id}", uids,
    )
    await manager.broadcast_notif(str_ids)


async def notif_fca_comentario(db: AsyncSession, fca: FCA, autor_nome: str, autor_id: uuid.UUID | None = None):
    uids = await _uids_envolvidos_fca(db, fca)
    if autor_id:
        uids = [uid for uid in uids if uid != autor_id]
    if not uids:
        return
    str_ids = await _inserir(
        db, "fca", f"Novo comentário em {fca.cod_fca}",
        f"Comentário de {autor_nome}", f"/fca/{fca.id}", uids,
    )
    await manager.broadcast_notif(str_ids)


# ── Help ──────────────────────────────────────────────────────────────────────

async def notif_help_novo(db: AsyncSession, ticket: HelpTicket):
    """Notifica todos os admins sobre novo ticket."""
    result = await db.execute(
        select(User).where(User.role == "admin", User.is_active == True)  # noqa: E712
    )
    admins = result.scalars().all()
    if not admins:
        return
    str_ids = await _inserir(
        db, "help", f"Novo ticket: {ticket.titulo}",
        None, f"/admin/help", [u.id for u in admins],
    )
    await manager.broadcast_notif(str_ids)


async def notif_help_atualizado(db: AsyncSession, ticket: HelpTicket, autor_nome: str, acao: str, autor_id: uuid.UUID | None = None):
    """Notifica o criador do ticket (e admins) sobre atualização."""
    ids: set[uuid.UUID] = {ticket.created_by}
    result = await db.execute(
        select(User).where(User.role == "admin", User.is_active == True)  # noqa: E712
    )
    for u in result.scalars().all():
        ids.add(u.id)
    # Quem fez a ação não precisa ser notificado
    if autor_id:
        ids.discard(autor_id)
    if not ids:
        return
    str_ids = await _inserir(
        db, "help", f"Ticket '{ticket.titulo}' atualizado",
        f"{acao} por {autor_nome}", f"/help", list(ids),
    )
    await manager.broadcast_notif(str_ids)
