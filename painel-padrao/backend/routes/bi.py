from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, and_, func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from auth import require_user
from database import get_db
from models import FCA, FCAEtapa

router = APIRouter(prefix="/bi", tags=["bi"])
any_user = require_user()


@router.get("/fca")
async def get_fca_bi(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    empresa: Optional[str] = None,
    setor: Optional[str] = None,
    uf: Optional[str] = None,
    causa: Optional[str] = None,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    agrupamento: str = "semana",
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    """
    Endpoint de BI para FCAs. Retorna dados agregados para o painel de relatório.

    Controle de acesso:
    - admin: acesso irrestrito a todos os dados
    - acesso_relatorio=True: acesso com escopo limitado ao setor+empresa do usuário
    - demais: HTTP 403
    """
    # ── Verificação de acesso ─────────────────────────────────────────────────
    is_admin = current["role"] == "admin"
    has_relatorio_access = current.get("acesso_relatorio", False)

    if not is_admin and not has_relatorio_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado ao relatório BI",
        )

    # Usuários com acesso_relatorio veem tudo (igual admin nesta tela)
    is_admin = is_admin or has_relatorio_access

    # ── Recorte temporal ──────────────────────────────────────────────────────
    if not data_inicio:
        dt_inicio = datetime.now(timezone.utc) - timedelta(days=30)
    else:
        dt_inicio = datetime.fromisoformat(data_inicio).replace(tzinfo=timezone.utc)

    if not data_fim:
        dt_fim = datetime.now(timezone.utc)
    else:
        dt_fim = datetime.fromisoformat(data_fim).replace(tzinfo=timezone.utc)

    # ── Predicados base sobre FCA ─────────────────────────────────────────────
    base_predicates = [
        FCA.created_at >= dt_inicio,
        FCA.created_at <= dt_fim,
    ]
    if empresa:
        base_predicates.append(FCA.empresa_causadora == empresa)
    if setor:
        base_predicates.append(FCA.setor_solicitante == setor)
    if uf:
        base_predicates.append(FCA.uf == uf)
    if causa:
        base_predicates.append(FCA.causa == causa)
    if status_filter:
        base_predicates.append(FCA.status == status_filter)

    # ── Visibilidade: não-admin filtrado por setor+empresa ────────────────────
    # Quando não-admin, precisa join com FCAEtapa para filtrar por escopo
    requires_etapa_join = not is_admin

    if not is_admin:
        base_predicates.append(
            or_(
                and_(
                    FCA.setor_solicitante == current["sector"],
                    FCA.empresa_solicitante == current["company"],
                ),
                and_(
                    FCAEtapa.setor == current["sector"],
                    FCAEtapa.empresa == current["company"],
                ),
            )
        )

    # ── KPIs ──────────────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)

    if requires_etapa_join:
        # Não-admin: JOIN com FCAEtapa porque base_predicates inclui predicados sobre FCAEtapa
        # Usa isouter=True e count(distinct) para evitar duplicatas por múltiplas etapas
        total_q = (
            select(func.count(FCA.id.distinct()))
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates)
        )
        encerrados_q = (
            select(func.count(FCA.id.distinct()))
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates, FCA.status == "encerrado")
        )
        em_aberto_q = (
            select(func.count(FCA.id.distinct()))
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates, FCA.status.in_(["aberto", "em_andamento"]))
        )
    else:
        # Admin: queries simples sem JOIN
        total_q = select(func.count(FCA.id)).where(*base_predicates)
        encerrados_q = select(func.count(FCA.id)).where(*base_predicates, FCA.status == "encerrado")
        em_aberto_q = select(func.count(FCA.id)).where(
            *base_predicates, FCA.status.in_(["aberto", "em_andamento"])
        )

    # Atrasados: FCAs com etapa ativa com sla_deadline vencido (sempre usa JOIN)
    atrasados_q = (
        select(func.count(FCA.id.distinct()))
        .select_from(FCA)
        .join(FCAEtapa, FCAEtapa.fca_id == FCA.id)
        .where(
            *base_predicates,
            FCAEtapa.status.in_(["pendente", "em_andamento"]),
            FCAEtapa.sla_deadline < now,
            FCA.status.notin_(["encerrado"]),
        )
    )

    total = (await db.execute(total_q)).scalar() or 0
    encerrados = (await db.execute(encerrados_q)).scalar() or 0
    em_aberto = (await db.execute(em_aberto_q)).scalar() or 0
    atrasados = (await db.execute(atrasados_q)).scalar() or 0

    taxa_resolucao = round(encerrados / total * 100, 1) if total > 0 else 0.0

    # ── Por status ───────────────────────────────────────────────────────────
    if requires_etapa_join:
        por_status_q = (
            select(FCA.status, func.count(FCA.id.distinct()).label("total"))
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates)
            .group_by(FCA.status)
        )
    else:
        por_status_q = (
            select(FCA.status, func.count(FCA.id).label("total"))
            .select_from(FCA)
            .where(*base_predicates)
            .group_by(FCA.status)
        )

    por_status_rows = (await db.execute(por_status_q)).all()
    por_status = [{"status": r.status, "total": r.total} for r in por_status_rows]

    # ── Evolução temporal ────────────────────────────────────────────────────
    if agrupamento == "mes":
        trunc_fn = func.date_trunc("month", FCA.created_at)
    else:
        trunc_fn = func.date_trunc("week", FCA.created_at)

    if requires_etapa_join:
        abertos_evol_q = (
            select(trunc_fn.label("periodo"), func.count(FCA.id.distinct()).label("total"))
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates, FCA.status.in_(["aberto", "em_andamento", "aguardando_devolutiva"]))
            .group_by("periodo")
            .order_by("periodo")
            .limit(12)
        )
        encerrados_evol_q = (
            select(trunc_fn.label("periodo"), func.count(FCA.id.distinct()).label("total"))
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates, FCA.status == "encerrado")
            .group_by("periodo")
            .order_by("periodo")
            .limit(12)
        )
    else:
        abertos_evol_q = (
            select(trunc_fn.label("periodo"), func.count(FCA.id).label("total"))
            .select_from(FCA)
            .where(*base_predicates, FCA.status.in_(["aberto", "em_andamento", "aguardando_devolutiva"]))
            .group_by("periodo")
            .order_by("periodo")
            .limit(12)
        )
        encerrados_evol_q = (
            select(trunc_fn.label("periodo"), func.count(FCA.id).label("total"))
            .select_from(FCA)
            .where(*base_predicates, FCA.status == "encerrado")
            .group_by("periodo")
            .order_by("periodo")
            .limit(12)
        )

    abertos_evol_rows = (await db.execute(abertos_evol_q)).all()
    encerrados_evol_rows = (await db.execute(encerrados_evol_q)).all()

    # Merge em Python: dict por período
    evol_map: dict = {}
    for r in abertos_evol_rows:
        periodo_key = str(r.periodo)
        if periodo_key not in evol_map:
            evol_map[periodo_key] = {"periodo": periodo_key, "abertos": 0, "encerrados": 0}
        evol_map[periodo_key]["abertos"] = r.total
    for r in encerrados_evol_rows:
        periodo_key = str(r.periodo)
        if periodo_key not in evol_map:
            evol_map[periodo_key] = {"periodo": periodo_key, "abertos": 0, "encerrados": 0}
        evol_map[periodo_key]["encerrados"] = r.total

    evolucao_temporal = sorted(evol_map.values(), key=lambda x: x["periodo"])

    # ── Ranking causas ───────────────────────────────────────────────────────
    if requires_etapa_join:
        ranking_causas_q = (
            select(FCA.causa, func.count(FCA.id.distinct()).label("total"))
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates)
            .group_by(FCA.causa)
            .order_by(func.count(FCA.id.distinct()).desc())
            .limit(10)
        )
    else:
        ranking_causas_q = (
            select(FCA.causa, func.count(FCA.id).label("total"))
            .select_from(FCA)
            .where(*base_predicates)
            .group_by(FCA.causa)
            .order_by(func.count(FCA.id).desc())
            .limit(10)
        )

    ranking_causas_rows = (await db.execute(ranking_causas_q)).all()
    ranking_causas = [{"causa": r.causa, "total": r.total} for r in ranking_causas_rows]

    # ── Ranking áreas ────────────────────────────────────────────────────────
    if requires_etapa_join:
        ranking_areas_q = (
            select(
                FCA.area_causadora,
                FCA.empresa_causadora,
                func.count(FCA.id.distinct()).label("total"),
            )
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates)
            .group_by(FCA.area_causadora, FCA.empresa_causadora)
            .order_by(func.count(FCA.id.distinct()).desc())
            .limit(10)
        )
    else:
        ranking_areas_q = (
            select(
                FCA.area_causadora,
                FCA.empresa_causadora,
                func.count(FCA.id).label("total"),
            )
            .select_from(FCA)
            .where(*base_predicates)
            .group_by(FCA.area_causadora, FCA.empresa_causadora)
            .order_by(func.count(FCA.id).desc())
            .limit(10)
        )

    ranking_areas_rows = (await db.execute(ranking_areas_q)).all()
    ranking_areas = [
        {"area_causadora": r.area_causadora, "empresa_causadora": r.empresa_causadora, "total": r.total}
        for r in ranking_areas_rows
    ]

    # ── Por UF ───────────────────────────────────────────────────────────────
    if requires_etapa_join:
        por_uf_q = (
            select(FCA.uf, func.count(FCA.id.distinct()).label("total"))
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates)
            .group_by(FCA.uf)
            .order_by(func.count(FCA.id.distinct()).desc())
        )
    else:
        por_uf_q = (
            select(FCA.uf, func.count(FCA.id).label("total"))
            .select_from(FCA)
            .where(*base_predicates)
            .group_by(FCA.uf)
            .order_by(func.count(FCA.id).desc())
        )

    por_uf_rows = (await db.execute(por_uf_q)).all()
    por_uf = [{"uf": r.uf, "total": r.total} for r in por_uf_rows]

    # ── Por empresa ──────────────────────────────────────────────────────────
    if requires_etapa_join:
        por_empresa_q = (
            select(FCA.empresa_causadora, func.count(FCA.id.distinct()).label("total"))
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
            .where(*base_predicates)
            .group_by(FCA.empresa_causadora)
            .order_by(func.count(FCA.id.distinct()).desc())
        )
    else:
        por_empresa_q = (
            select(FCA.empresa_causadora, func.count(FCA.id).label("total"))
            .select_from(FCA)
            .where(*base_predicates)
            .group_by(FCA.empresa_causadora)
            .order_by(func.count(FCA.id).desc())
        )

    por_empresa_rows = (await db.execute(por_empresa_q)).all()
    por_empresa = [{"empresa_causadora": r.empresa_causadora, "total": r.total} for r in por_empresa_rows]

    # ── Solução por área ──────────────────────────────────────────────────────
    # Sempre usa JOIN com FCAEtapa (acessa FCAEtapa.problema_solucionado)
    solucao_predicates = list(base_predicates)
    if not is_admin:
        # Para não-admin, substituímos o predicado de visibilidade por um filtro adicional
        # sem o or_ já em base_predicates — a visibilidade é aplicada via predicados diretos
        # sobre FCAEtapa dado que o join é INNER (não isouter)
        # Filtramos apenas FCAEtapas de escopo do usuário como predicado adicional
        solucao_predicates.append(
            or_(
                and_(
                    FCAEtapa.setor == current["sector"],
                    FCAEtapa.empresa == current["company"],
                ),
            )
        )

    solucao_por_area_q = (
        select(
            FCA.area_causadora,
            func.sum(case((FCAEtapa.problema_solucionado == True, 1), else_=0)).label("solucionado"),
            func.sum(case((FCAEtapa.problema_solucionado == False, 1), else_=0)).label("nao_solucionado"),
        )
        .select_from(FCA)
        .join(FCAEtapa, FCAEtapa.fca_id == FCA.id)
        .where(
            *solucao_predicates,
            FCAEtapa.problema_solucionado.isnot(None),
        )
        .group_by(FCA.area_causadora)
        .order_by(FCA.area_causadora)
    )

    solucao_por_area_rows = (await db.execute(solucao_por_area_q)).all()
    solucao_por_area = [
        {
            "area_causadora": r.area_causadora,
            "solucionado": r.solucionado or 0,
            "nao_solucionado": r.nao_solucionado or 0,
        }
        for r in solucao_por_area_rows
    ]

    # ── Tempo médio por setor (FCAEtapa) ──────────────────────────────────────
    tempo_q = (
        select(
            FCAEtapa.setor,
            func.avg(
                func.extract("epoch", FCAEtapa.concluded_at - FCAEtapa.entered_at) / 3600
            ).label("tempo_medio_horas"),
        )
        .where(
            FCAEtapa.status == "concluido",
            FCAEtapa.entered_at >= dt_inicio,
            FCAEtapa.entered_at <= dt_fim,
        )
        .group_by(FCAEtapa.setor)
        .order_by(
            func.avg(
                func.extract("epoch", FCAEtapa.concluded_at - FCAEtapa.entered_at) / 3600
            ).desc()
        )
    )
    if not is_admin:
        tempo_q = tempo_q.where(
            FCAEtapa.setor == current["sector"],
            FCAEtapa.empresa == current["company"],
        )

    tempo_rows = (await db.execute(tempo_q)).all()
    tempo_medio_setor = [
        {"setor": r.setor, "tempo_medio_horas": round(r.tempo_medio_horas, 2) if r.tempo_medio_horas is not None else 0.0}
        for r in tempo_rows
    ]

    # ── SLA por setor ─────────────────────────────────────────────────────────
    sla_q = (
        select(
            FCAEtapa.setor,
            func.sum(case((FCAEtapa.concluded_at <= FCAEtapa.sla_deadline, 1), else_=0)).label("ok"),
            func.sum(case((FCAEtapa.concluded_at > FCAEtapa.sla_deadline, 1), else_=0)).label("nok"),
        )
        .where(
            FCAEtapa.sla_deadline.isnot(None),
            FCAEtapa.status == "concluido",
            FCAEtapa.entered_at >= dt_inicio,
            FCAEtapa.entered_at <= dt_fim,
        )
        .group_by(FCAEtapa.setor)
    )
    if not is_admin:
        sla_q = sla_q.where(
            FCAEtapa.setor == current["sector"],
            FCAEtapa.empresa == current["company"],
        )

    sla_rows = (await db.execute(sla_q)).all()
    sla_por_setor = [
        {"setor": r.setor, "ok": int(r.ok or 0), "nok": int(r.nok or 0)}
        for r in sla_rows
    ]

    # ── Tabela empresa × causa ────────────────────────────────────────────────
    if not is_admin:
        tabela_empresa_causa_q = (
            select(
                FCA.empresa_causadora,
                FCA.causa,
                func.count(FCA.id.distinct()).label("total"),
            )
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id)
            .where(
                *base_predicates,
                FCAEtapa.setor == current["sector"],
                FCAEtapa.empresa == current["company"],
            )
            .group_by(FCA.empresa_causadora, FCA.causa)
            .order_by(func.count(FCA.id.distinct()).desc())
        )
    else:
        tabela_empresa_causa_q = (
            select(
                FCA.empresa_causadora,
                FCA.causa,
                func.count(FCA.id).label("total"),
            )
            .select_from(FCA)
            .where(*base_predicates)
            .group_by(FCA.empresa_causadora, FCA.causa)
            .order_by(func.count(FCA.id).desc())
        )

    tabela_empresa_causa_rows = (await db.execute(tabela_empresa_causa_q)).all()
    tabela_empresa_causa = [
        {"empresa_causadora": r.empresa_causadora, "causa": r.causa, "total": r.total}
        for r in tabela_empresa_causa_rows
    ]

    # ── Tabela setor × empresa × causa ───────────────────────────────────────
    if not is_admin:
        tabela_setor_empresa_causa_q = (
            select(
                FCA.setor_solicitante,
                FCA.empresa_solicitante,
                FCA.causa,
                func.count(FCA.id.distinct()).label("total"),
            )
            .select_from(FCA)
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id)
            .where(
                *base_predicates,
                FCAEtapa.setor == current["sector"],
                FCAEtapa.empresa == current["company"],
            )
            .group_by(FCA.setor_solicitante, FCA.empresa_solicitante, FCA.causa)
            .order_by(func.count(FCA.id.distinct()).desc())
        )
    else:
        tabela_setor_empresa_causa_q = (
            select(
                FCA.setor_solicitante,
                FCA.empresa_solicitante,
                FCA.causa,
                func.count(FCA.id).label("total"),
            )
            .select_from(FCA)
            .where(*base_predicates)
            .group_by(FCA.setor_solicitante, FCA.empresa_solicitante, FCA.causa)
            .order_by(func.count(FCA.id).desc())
        )

    tabela_setor_empresa_causa_rows = (await db.execute(tabela_setor_empresa_causa_q)).all()
    tabela_setor_empresa_causa = [
        {
            "setor": r.setor_solicitante,
            "empresa": r.empresa_solicitante,
            "causa": r.causa,
            "total": r.total,
        }
        for r in tabela_setor_empresa_causa_rows
    ]

    return {
        "kpis": {
            "total": total,
            "encerrados": encerrados,
            "em_aberto": em_aberto,
            "atrasados": atrasados,
            "taxa_resolucao": taxa_resolucao,
        },
        "por_status": por_status,
        "evolucao_temporal": evolucao_temporal,
        "ranking_causas": ranking_causas,
        "ranking_areas": ranking_areas,
        "por_uf": por_uf,
        "por_empresa": por_empresa,
        "solucao_por_area": solucao_por_area,
        "tempo_medio_setor": tempo_medio_setor,
        "sla_por_setor": sla_por_setor,
        "tabela_empresa_causa": tabela_empresa_causa,
        "tabela_setor_empresa_causa": tabela_setor_empresa_causa,
    }
