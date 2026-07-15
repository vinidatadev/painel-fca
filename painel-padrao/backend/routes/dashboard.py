import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, extract
from sqlalchemy.orm import selectinload
from database import get_db
from models import FCA, FCAEtapa
from auth import require_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
any_user = require_user()


@router.get("/")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    # FCAs onde é a vez do setor do usuário
    minha_fila_q = (
        select(FCA)
        .options(selectinload(FCA.etapas))
        .join(FCAEtapa, FCAEtapa.fca_id == FCA.id)
        .where(
            FCAEtapa.setor == current["sector"],
            FCAEtapa.empresa == current["company"],
            FCAEtapa.status.in_(["pendente", "em_andamento"]),
        )
        .distinct()
    )

    if current["role"] != "admin":
        pass  # filtro já aplicado acima
    else:
        # Admin vê todos os pendentes
        minha_fila_q = (
            select(FCA)
            .options(selectinload(FCA.etapas))
            .join(FCAEtapa, FCAEtapa.fca_id == FCA.id)
            .where(FCAEtapa.status.in_(["pendente", "em_andamento"]))
            .distinct()
        )

    minha_fila_q = minha_fila_q.order_by(FCA.created_at.asc())
    minha_fila_result = await db.execute(minha_fila_q)
    minha_fila_fcas = minha_fila_result.scalars().unique().all()

    minha_fila_items = []
    for fca in minha_fila_fcas:
        etapa = next(
            (e for e in sorted(fca.etapas, key=lambda e: e.order_index)
             if e.status in ("pendente", "em_andamento")),
            None
        )
        minha_fila_items.append({
            "id": str(fca.id),
            "cod_fca": fca.cod_fca,
            "causa": fca.causa,
            "area_causadora": fca.area_causadora,
            "empresa_causadora": fca.empresa_causadora,
            "uf": fca.uf,
            "status": fca.status,
            "etapa_atual": {
                "setor": etapa.setor,
                "empresa": etapa.empresa,
                "order_index": etapa.order_index,
                "sla_deadline": etapa.sla_deadline.isoformat() if etapa.sla_deadline else None,
            } if etapa else None,
            "created_at": fca.created_at.isoformat(),
        })

    # Contadores de acompanhamento
    base_filter: list = []
    if current["role"] != "admin":
        base_filter = [
            or_(
                and_(
                    FCA.setor_solicitante == current["sector"],
                    FCA.empresa_solicitante == current["company"],
                ),
                and_(
                    FCAEtapa.setor == current["sector"],
                    FCAEtapa.empresa == current["company"],
                )
            )
        ]

    async def count_status(s: str) -> int:
        q = select(func.count(FCA.id.distinct())).select_from(FCA)
        if base_filter:
            q = q.join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True).where(*base_filter)
        q = q.where(FCA.status == s)
        return (await db.execute(q)).scalar() or 0

    abertos = await count_status("aberto")
    em_andamento = await count_status("em_andamento")
    aguardando = await count_status("aguardando_devolutiva")
    encerrados = await count_status("encerrado")

    return {
        "minha_fila": {
            "total": len(minha_fila_items),
            "itens": minha_fila_items,
        },
        "acompanhamento": {
            "abertos": abertos,
            "em_andamento": em_andamento,
            "aguardando_devolutiva": aguardando,
            "encerrados": encerrados,
        }
    }


@router.get("/metricas")
async def dashboard_metricas(
    agrupamento: str = "semana",
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(any_user),
):
    """Retorna série temporal, ranking de áreas causadoras e contador de atrasados."""
    now = datetime.now(timezone.utc)

    # ── Base de visibilidade ──────────────────────────────────────────────────
    def _apply_visibility(stmt):
        if current["role"] != "admin":
            return (
                stmt.join(FCAEtapa, FCAEtapa.fca_id == FCA.id, isouter=True)
                .where(
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
                .distinct()
            )
        return stmt

    # ── Série temporal ────────────────────────────────────────────────────────
    if agrupamento == "mes":
        trunc_fn = func.date_trunc("month", FCA.created_at)
        fmt = "YYYY-MM"
    else:
        trunc_fn = func.date_trunc("week", FCA.created_at)
        fmt = "IYYY-IW"

    serie_stmt = _apply_visibility(
        select(trunc_fn.label("periodo"), func.count(FCA.id.distinct()).label("total"))
        .select_from(FCA)
        .group_by("periodo")
        .order_by("periodo")
    )
    serie_result = await db.execute(serie_stmt)
    serie_temporal = [
        {"periodo": row.periodo.isoformat() if hasattr(row.periodo, "isoformat") else str(row.periodo), "total": row.total}
        for row in serie_result.all()
    ]

    # ── Ranking de áreas causadoras ───────────────────────────────────────────
    ranking_stmt = _apply_visibility(
        select(
            FCA.area_causadora,
            FCA.empresa_causadora,
            func.count(FCA.id.distinct()).label("total"),
        )
        .select_from(FCA)
        .group_by(FCA.area_causadora, FCA.empresa_causadora)
        .order_by(func.count(FCA.id.distinct()).desc())
        .limit(5)
    )
    ranking_result = await db.execute(ranking_stmt)
    ranking_areas = [
        {"area_causadora": row.area_causadora, "empresa_causadora": row.empresa_causadora, "total": row.total}
        for row in ranking_result.all()
    ]

    # ── Atrasados ─────────────────────────────────────────────────────────────
    atrasados_stmt = (
        select(func.count(FCA.id.distinct()))
        .select_from(FCA)
        .join(FCAEtapa, FCAEtapa.fca_id == FCA.id)
        .where(
            FCAEtapa.status.in_(["pendente", "em_andamento"]),
            FCAEtapa.sla_deadline < now,
            FCA.status.notin_(["encerrado", "concluido"]),
        )
    )
    if current["role"] != "admin":
        atrasados_stmt = atrasados_stmt.where(
            FCAEtapa.setor == current["sector"],
            FCAEtapa.empresa == current["company"],
        )
    atrasados = (await db.execute(atrasados_stmt)).scalar() or 0

    return {
        "serie_temporal": serie_temporal,
        "ranking_areas": ranking_areas,
        "atrasados": atrasados,
    }
