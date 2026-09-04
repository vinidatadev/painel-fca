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
    """Retorna IDs de usuários que devem ser notificados sobre um FCA.

    Considera TODOS os usuários ativos que possuem vínculo (UserSetor) com o
    setor/empresa solicitante ou com qualquer etapa do FCA — inclusive usuários
    com mais de um setor no perfil.
    """
    ids: set[uuid.UUID] = set()
    from sqlalchemy import or_, and_
    from models import UserSetor

    setores = {(fca.setor_solicitante, fca.empresa_solicitante)}
    result = await db.execute(
        select(FCAEtapa).where(FCAEtapa.fca_id == fca.id)
    )
    etapas = result.scalars().all()
    setores.update((e.setor, e.empresa) for e in etapas)

    if setores:
        conds = [and_(UserSetor.setor == s, UserSetor.empresa == e) for s, e in setores]
        q = (
            select(User)
            .join(UserSetor, UserSetor.user_id == User.id)
            .where(User.is_active == True, or_(*conds))  # noqa: E712
            .distinct()
        )
        res = await db.execute(q)
        for u in res.scalars().all():
            ids.add(u.id)

    # garante que o criador esteja presente mesmo se estiver inativo
    ids.add(fca.created_by)
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

def _etapa_ativa_fca(fca: FCA) -> FCAEtapa | None:
    pendentes = [e for e in fca.etapas if e.status in ("pendente", "em_andamento")]
    return min(pendentes, key=lambda e: e.order_index) if pendentes else None


def _label_setor(setor: str | None, empresa: str | None) -> str:
    """Formata um setor para exibição (ex: 'Expedição' → 'Expedicao')."""
    return setor or "-"


async def notif_fca_criado(db: AsyncSession, fca: FCA):
    """Notifica quando um FCA é aberto, deixando claro quem abriu e para quem.

    Ex: 'Novo FCA FCA-2026-0009 aberto pela Expedicao → MEP'
    """
    uids = await _uids_envolvidos_fca(db, fca)
    # Quem criou não precisa ser notificado — ele mesmo abriu o FCA
    uids = [uid for uid in uids if uid != fca.created_by]
    if not uids:
        return

    # Destino = setor da etapa ativa (primeira pendente) ou área causadora
    destino = _etapa_ativa_fca(fca)
    destino_setor = destino.setor if destino else fca.area_causadora
    destino_empresa = destino.empresa if destino else fca.empresa_causadora

    solicitante = _label_setor(fca.setor_solicitante, fca.empresa_solicitante)
    dest = _label_setor(destino_setor, destino_empresa)

    titulo = f"Novo FCA {fca.cod_fca} aberto pela {solicitante}"
    mensagem = f"Direcionado para {dest} · {fca.causa}"
    str_ids = await _inserir(db, "fca", titulo, mensagem, f"/fca/{fca.id}", uids)
    await manager.broadcast_notif(str_ids)


async def notif_fca_atualizado(
    db: AsyncSession,
    fca: FCA,
    acao: str,
    autor_nome: str,
    autor_id: uuid.UUID | None = None,
    autor_setor: str | None = None,
    autor_empresa: str | None = None,
):
    """Notifica sobre atualização, mostrando o setor que fez a ação.

    Ex: 'MEP respondeu o FCA FCA-2026-0009'
    """
    uids = await _uids_envolvidos_fca(db, fca)
    if autor_id:
        uids = [uid for uid in uids if uid != autor_id]
    if not uids:
        return

    autor_label = _label_setor(autor_setor, autor_empresa)
    titulo = f"{autor_label} {acao} o FCA {fca.cod_fca}"
    mensagem = f"por {autor_nome}"
    str_ids = await _inserir(db, "fca", titulo, mensagem, f"/fca/{fca.id}", uids)
    await manager.broadcast_notif(str_ids)


async def notif_fca_comentario(
    db: AsyncSession,
    fca: FCA,
    autor_nome: str,
    autor_id: uuid.UUID | None = None,
    autor_setor: str | None = None,
    autor_empresa: str | None = None,
):
    """Notifica sobre novo comentário, mostrando o setor que comentou.

    Ex: 'MEP comentou no FCA FCA-2026-0009'
    """
    uids = await _uids_envolvidos_fca(db, fca)
    if autor_id:
        uids = [uid for uid in uids if uid != autor_id]
    if not uids:
        return

    autor_label = _label_setor(autor_setor, autor_empresa)
    titulo = f"{autor_label} comentou no FCA {fca.cod_fca}"
    mensagem = f"Comentário de {autor_nome} ({autor_label})"
    str_ids = await _inserir(db, "fca", titulo, mensagem, f"/fca/{fca.id}", uids)
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
