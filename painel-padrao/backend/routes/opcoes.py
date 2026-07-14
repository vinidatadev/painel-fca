"""
Listas configuráveis: causas, ações, UFs.
Leitura pública (qualquer autenticado), escrita somente admin.
Na primeira carga, semeia os valores padrão do business.py se o banco estiver vazio.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import OpcaoLista
from auth import require_user
from business import CAUSAS, ACOES, UFS, COMPANIES, SECTORS_BY_COMPANY

router = APIRouter(prefix="/opcoes", tags=["opcoes"])
any_user  = require_user()
admin_only = require_user(required_role="admin")

TIPOS_VALIDOS = {"causa", "acao", "uf"}


# ── seed automático ──────────────────────────────────────────────────────────

async def seed_opcoes(db: AsyncSession):
    """Popula as tabelas na primeira inicialização."""
    count = await db.execute(select(func.count()).select_from(OpcaoLista))
    if count.scalar() > 0:
        return
    itens = (
        [OpcaoLista(tipo="causa", valor=v, ordem=i) for i, v in enumerate(CAUSAS)] +
        [OpcaoLista(tipo="acao",  valor=v, ordem=i) for i, v in enumerate(ACOES)]  +
        [OpcaoLista(tipo="uf",    valor=v, ordem=i) for i, v in enumerate(UFS)]
    )
    db.add_all(itens)
    await db.commit()


# ── Schemas ──────────────────────────────────────────────────────────────────

class OpcaoOut(BaseModel):
    id: str
    tipo: str
    valor: str
    ativo: bool
    ordem: int

    @classmethod
    def from_orm(cls, o: OpcaoLista):
        return cls(id=str(o.id), tipo=o.tipo, valor=o.valor, ativo=o.ativo, ordem=o.ordem)


class OpcaoCreate(BaseModel):
    tipo: str
    valor: str = Field(..., min_length=1)
    ordem: int = 999


class OpcaoUpdate(BaseModel):
    valor: str | None = Field(default=None, min_length=1)
    ativo: bool | None = None
    ordem: int | None = None


# ── Rotas ────────────────────────────────────────────────────────────────────

@router.get("/")
async def get_opcoes(db: AsyncSession = Depends(get_db), _: dict = Depends(any_user)):
    """Retorna todas as listas para o formulário de abertura de FCA."""
    await seed_opcoes(db)

    result = await db.execute(
        select(OpcaoLista)
        .where(OpcaoLista.ativo == True)
        .order_by(OpcaoLista.tipo, OpcaoLista.ordem, OpcaoLista.valor)
    )
    itens = result.scalars().all()

    causas = [o.valor for o in itens if o.tipo == "causa"]
    acoes  = [o.valor for o in itens if o.tipo == "acao"]
    ufs    = [o.valor for o in itens if o.tipo == "uf"]

    return {
        "causas": causas,
        "acoes":  acoes,
        "ufs":    ufs,
        "empresas": COMPANIES,
        "setores_por_empresa": SECTORS_BY_COMPANY,
    }


@router.get("/admin", response_model=list[OpcaoOut])
async def list_opcoes_admin(
    tipo: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    """Lista todas as opções (incluindo inativas) para gestão pelo admin."""
    await seed_opcoes(db)
    q = select(OpcaoLista).order_by(OpcaoLista.tipo, OpcaoLista.ordem, OpcaoLista.valor)
    if tipo:
        q = q.where(OpcaoLista.tipo == tipo)
    result = await db.execute(q)
    return [OpcaoOut.from_orm(o) for o in result.scalars().all()]


@router.post("/", response_model=OpcaoOut, status_code=201)
async def create_opcao(
    body: OpcaoCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    if body.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"Tipo inválido. Use: {TIPOS_VALIDOS}")

    # Verifica duplicata ativa
    dup = await db.execute(
        select(OpcaoLista).where(
            OpcaoLista.tipo == body.tipo,
            OpcaoLista.valor == body.valor,
            OpcaoLista.ativo == True
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Valor já existe nesta lista")

    opcao = OpcaoLista(tipo=body.tipo, valor=body.valor, ordem=body.ordem)
    db.add(opcao)
    await db.commit()
    await db.refresh(opcao)
    return OpcaoOut.from_orm(opcao)


@router.put("/{opcao_id}", response_model=OpcaoOut)
async def update_opcao(
    opcao_id: UUID,
    body: OpcaoUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(select(OpcaoLista).where(OpcaoLista.id == opcao_id))
    opcao = result.scalar_one_or_none()
    if not opcao:
        raise HTTPException(status_code=404, detail="Opção não encontrada")

    if body.valor is not None:
        opcao.valor = body.valor
    if body.ativo is not None:
        opcao.ativo = body.ativo
    if body.ordem is not None:
        opcao.ordem = body.ordem

    await db.commit()
    await db.refresh(opcao)
    return OpcaoOut.from_orm(opcao)


@router.delete("/{opcao_id}", status_code=204)
async def delete_opcao(
    opcao_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(select(OpcaoLista).where(OpcaoLista.id == opcao_id))
    opcao = result.scalar_one_or_none()
    if not opcao:
        raise HTTPException(status_code=404, detail="Opção não encontrada")
    # Soft delete — desativa em vez de remover (preserva histórico dos FCAs)
    opcao.ativo = False
    await db.commit()
