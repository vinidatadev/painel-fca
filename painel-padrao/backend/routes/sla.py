from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import SlaRegra
from auth import require_user
from sla import calcular_prazo_minutos
from business import COMPANIES, SECTORS_BY_COMPANY, validate_company_sector

router = APIRouter(prefix="/sla", tags=["sla"])
admin_only = require_user(required_role="admin")
any_user   = require_user()

UNIDADES = {"minuto", "hora", "dia"}


class SlaOut(BaseModel):
    id: str
    empresa: str | None
    setor: str | None
    valor: int
    unidade: str
    prazo_minutos: int
    ativo: bool
    escopo: str  # label legível

    @classmethod
    def from_orm(cls, r: SlaRegra):
        if r.setor and r.empresa:
            escopo = f"{r.setor} / {r.empresa}"
        elif r.empresa:
            escopo = f"Toda a empresa {r.empresa}"
        else:
            escopo = "Global (padrão)"
        return cls(
            id=str(r.id), empresa=r.empresa, setor=r.setor,
            valor=r.valor, unidade=r.unidade,
            prazo_minutos=r.prazo_minutos, ativo=r.ativo,
            escopo=escopo
        )


class SlaCreate(BaseModel):
    empresa: str | None = None
    setor: str | None = None
    valor: int = Field(..., gt=0)
    unidade: str  # minuto | hora | dia


class SlaUpdate(BaseModel):
    valor: int | None = Field(default=None, gt=0)
    unidade: str | None = None
    ativo: bool | None = None


@router.get("/", response_model=list[SlaOut])
async def list_sla(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(
        select(SlaRegra).order_by(
            SlaRegra.empresa.nulls_last(),
            SlaRegra.setor.nulls_last()
        )
    )
    return [SlaOut.from_orm(r) for r in result.scalars().all()]


@router.post("/", response_model=SlaOut, status_code=201)
async def create_sla(
    body: SlaCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    if body.unidade not in UNIDADES:
        raise HTTPException(status_code=422, detail=f"Unidade inválida. Use: {UNIDADES}")

    if body.empresa and body.empresa not in COMPANIES:
        raise HTTPException(status_code=422, detail="Empresa inválida")

    if body.setor and body.empresa:
        if not validate_company_sector(body.empresa, body.setor):
            raise HTTPException(status_code=422, detail=f"Setor '{body.setor}' inválido para '{body.empresa}'")

    if body.setor and not body.empresa:
        raise HTTPException(status_code=422, detail="Informe a empresa ao definir um setor")

    # Verifica duplicata ativa
    q = select(SlaRegra).where(
        SlaRegra.ativo == True,
        SlaRegra.empresa == body.empresa,
        SlaRegra.setor == body.setor,
    )
    dup = (await db.execute(q)).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=400, detail="Já existe uma regra ativa para este escopo")

    prazo = calcular_prazo_minutos(body.valor, body.unidade)
    regra = SlaRegra(
        empresa=body.empresa,
        setor=body.setor,
        valor=body.valor,
        unidade=body.unidade,
        prazo_minutos=prazo,
    )
    db.add(regra)
    await db.commit()
    await db.refresh(regra)
    return SlaOut.from_orm(regra)


@router.put("/{sla_id}", response_model=SlaOut)
async def update_sla(
    sla_id: UUID,
    body: SlaUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(select(SlaRegra).where(SlaRegra.id == sla_id))
    regra = result.scalar_one_or_none()
    if not regra:
        raise HTTPException(status_code=404, detail="Regra não encontrada")

    if body.unidade is not None:
        if body.unidade not in UNIDADES:
            raise HTTPException(status_code=422, detail="Unidade inválida")
        regra.unidade = body.unidade
    if body.valor is not None:
        regra.valor = body.valor
    if body.ativo is not None:
        regra.ativo = body.ativo

    regra.prazo_minutos = calcular_prazo_minutos(regra.valor, regra.unidade)
    await db.commit()
    await db.refresh(regra)
    return SlaOut.from_orm(regra)


@router.delete("/{sla_id}", status_code=204)
async def delete_sla(
    sla_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(select(SlaRegra).where(SlaRegra.id == sla_id))
    regra = result.scalar_one_or_none()
    if not regra:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    await db.delete(regra)
    await db.commit()
