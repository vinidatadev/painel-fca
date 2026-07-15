from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, and_
from database import get_db
from models import FCAEtapa
from auth import require_user

router = APIRouter(prefix="/admin", tags=["admin"])
admin_user = require_user(required_role="admin")


@router.get("/relatorio")
async def relatorio_desempenho(
    data_inicio: str | None = None,
    data_fim: str | None = None,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(admin_user),
):
    """Relatório de desempenho por setor+empresa: tempo médio, % SLA, total de etapas."""
    stmt = (
        select(
            FCAEtapa.setor,
            FCAEtapa.empresa,
            func.count(FCAEtapa.id).label("total_etapas"),
            func.avg(
                func.extract("epoch", FCAEtapa.concluded_at - FCAEtapa.entered_at) / 3600
            ).label("tempo_medio_horas"),
            func.sum(
                case(
                    (FCAEtapa.concluded_at <= FCAEtapa.sla_deadline, 1),
                    else_=0,
                )
            ).label("dentro_sla"),
        )
        .where(FCAEtapa.status == "concluido")
        .group_by(FCAEtapa.setor, FCAEtapa.empresa)
        .order_by(func.avg(
            func.extract("epoch", FCAEtapa.concluded_at - FCAEtapa.entered_at) / 3600
        ).desc())
    )

    if data_inicio:
        stmt = stmt.where(FCAEtapa.entered_at >= datetime.fromisoformat(data_inicio))
    if data_fim:
        stmt = stmt.where(FCAEtapa.entered_at <= datetime.fromisoformat(data_fim))

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "setor": row.setor,
            "empresa": row.empresa,
            "tempo_medio_horas": round(float(row.tempo_medio_horas), 2) if row.tempo_medio_horas else 0.0,
            "pct_dentro_sla": round(float(row.dentro_sla) / float(row.total_etapas) * 100, 1) if row.total_etapas else 0.0,
            "total_etapas": row.total_etapas,
        }
        for row in rows
    ]
