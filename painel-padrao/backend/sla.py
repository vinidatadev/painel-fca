"""Lógica de SLA: busca a regra mais específica e calcula o deadline."""
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from models import SlaRegra

logger = logging.getLogger(__name__)

UNIDADE_MINUTOS = {"minuto": 1, "hora": 60, "dia": 1440}


def calcular_prazo_minutos(valor: int, unidade: str) -> int:
    return valor * UNIDADE_MINUTOS.get(unidade, 60)


async def get_sla_deadline(
    db: AsyncSession,
    setor: str,
    empresa: str,
    base: datetime,
) -> datetime | None:
    """
    Hierarquia: setor+empresa > só empresa > global (empresa=None e setor=None).
    Busca cada nível separadamente para garantir a prioridade correta.
    """
    # Nível 1: setor + empresa específicos
    r = await _buscar(db, setor=setor, empresa=empresa)
    if r:
        logger.debug("SLA [setor+empresa] %s/%s → %dmin", setor, empresa, r.prazo_minutos)
        return base + timedelta(minutes=r.prazo_minutos)

    # Nível 2: só empresa (qualquer setor)
    r = await _buscar(db, setor=None, empresa=empresa)
    if r:
        logger.debug("SLA [empresa] %s → %dmin", empresa, r.prazo_minutos)
        return base + timedelta(minutes=r.prazo_minutos)

    # Nível 3: global
    r = await _buscar(db, setor=None, empresa=None)
    if r:
        logger.debug("SLA [global] → %dmin", r.prazo_minutos)
        return base + timedelta(minutes=r.prazo_minutos)

    logger.debug("SLA sem regra para %s/%s", setor, empresa)
    return None


async def _buscar(db: AsyncSession, setor: str | None, empresa: str | None) -> SlaRegra | None:
    """Busca uma regra ativa exatamente com o escopo informado (NULL é NULL, não wildcard)."""
    conditions = [SlaRegra.ativo == True]

    if empresa is None:
        conditions.append(SlaRegra.empresa.is_(None))
    else:
        conditions.append(SlaRegra.empresa == empresa)

    if setor is None:
        conditions.append(SlaRegra.setor.is_(None))
    else:
        conditions.append(SlaRegra.setor == setor)

    result = await db.execute(select(SlaRegra).where(and_(*conditions)).limit(1))
    return result.scalar_one_or_none()
