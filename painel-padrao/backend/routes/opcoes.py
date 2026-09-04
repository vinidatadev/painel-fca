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
from models import OpcaoLista, AreaEmpresa, CampoDica
from auth import require_user
from business import CAUSAS, ACOES, UFS, COMPANIES, SECTORS_BY_COMPANY, AREAS, DEFAULT_AREA_EMPRESAS

router = APIRouter(prefix="/opcoes", tags=["opcoes"])
any_user  = require_user()
admin_only = require_user(required_role="admin")

TIPOS_VALIDOS = {"causa", "subsetor_causador", "acao", "uf", "empresa", "area"}


# ── seed automático ──────────────────────────────────────────────────────────

async def seed_opcoes(db: AsyncSession):
    """Popula as listas na primeira inicialização (por tipo, seguro re-executar)."""
    # Lista de subsetor_causador começa vazia — o admin cadastra as opções na tela.
    for tipo, valores in (
        ("causa", CAUSAS),
        ("acao", ACOES),
        ("uf", UFS),
        ("empresa", COMPANIES),
        ("area", AREAS),
    ):
        count = await db.execute(
            select(func.count()).select_from(OpcaoLista).where(OpcaoLista.tipo == tipo)
        )
        if count.scalar() > 0:
            continue
        db.add_all(OpcaoLista(tipo=tipo, valor=v, ordem=i) for i, v in enumerate(valores))
        await db.commit()


async def seed_areas_empresas(db: AsyncSession):
    """Popula os vínculos área↔empresa na primeira inicialização (seguro re-executar).

    Usa o mapeamento empresa→setores do business.py como padrão inicial. Depois
    o admin gerencia livremente em Configurações → "Empresas por Área".
    """
    count = await db.execute(select(func.count()).select_from(AreaEmpresa))
    if count.scalar() > 0:
        return
    db.add_all(
        AreaEmpresa(area=area, empresa=empresa, ordem=ordem)
        for area, empresas in DEFAULT_AREA_EMPRESAS.items()
        for ordem, empresa in enumerate(empresas)
    )
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


class AreaEmpresaOut(BaseModel):
    id: str
    area: str
    empresa: str
    ativo: bool
    ordem: int


class AreaEmpresaCreate(BaseModel):
    area: str = Field(..., min_length=1)
    empresa: str = Field(..., min_length=1)
    ordem: int = 999


class AreaEmpresaUpdate(BaseModel):
    ativo: bool | None = None
    ordem: int | None = None


class CampoDicaOut(BaseModel):
    id: str
    campo: str
    titulo: str | None
    texto: str
    ativo: bool
    ordem: int


class CampoDicaCreate(BaseModel):
    campo: str = Field(..., min_length=1)
    titulo: str | None = None
    texto: str = Field(..., min_length=1)
    ordem: int = 999


class CampoDicaUpdate(BaseModel):
    titulo: str | None = None
    texto: str | None = Field(default=None, min_length=1)
    ativo: bool | None = None
    ordem: int | None = None


# ── Rotas ────────────────────────────────────────────────────────────────────

@router.get("/")
async def get_opcoes(db: AsyncSession = Depends(get_db), _: dict = Depends(any_user)):
    """Retorna todas as listas para o formulário de abertura de FCA."""
    await seed_opcoes(db)
    await seed_areas_empresas(db)

    result = await db.execute(
        select(OpcaoLista)
        .where(OpcaoLista.ativo == True)
        .order_by(OpcaoLista.tipo, OpcaoLista.ordem, OpcaoLista.valor)
    )
    itens = result.scalars().all()

    causas = [o.valor for o in itens if o.tipo == "causa"]
    subsetores = [o.valor for o in itens if o.tipo == "subsetor_causador"]
    acoes  = [o.valor for o in itens if o.tipo == "acao"]
    ufs    = [o.valor for o in itens if o.tipo == "uf"]
    empresas = [o.valor for o in itens if o.tipo == "empresa"]
    areas  = [o.valor for o in itens if o.tipo == "area"]

    # Vínculos área ↔ empresa configuráveis (só combos ativos e empresas ativas).
    empresas_ativas = set(empresas)
    combos = await db.execute(
        select(AreaEmpresa).where(AreaEmpresa.ativo == True)
    )
    empresas_por_area: dict[str, list[str]] = {}
    for c in combos.scalars().all():
        if c.empresa in empresas_ativas:
            empresas_por_area.setdefault(c.area, []).append(c.empresa)

    # Dicas de orientação por campo (tooltip "i")
    dicas_result = await db.execute(
        select(CampoDica).where(CampoDica.ativo == True)
    )
    dicas = {
        d.campo: {"titulo": d.titulo, "texto": d.texto}
        for d in dicas_result.scalars().all()
    }

    return {
        "causas": causas,
        "subsetores_causadores": subsetores,
        "acoes":  acoes,
        "ufs":    ufs,
        "empresas": empresas,
        "areas": areas,
        "empresas_por_area": empresas_por_area,
        "dicas": dicas,
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


# ── Vínculos Área ↔ Empresa ──────────────────────────────────────────────────

@router.get("/areas-empresas", response_model=list[AreaEmpresaOut])
async def list_areas_empresas(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    """Lista todos os vínculos (incluindo inativos) para gestão pelo admin."""
    await seed_areas_empresas(db)
    result = await db.execute(
        select(AreaEmpresa).order_by(AreaEmpresa.area, AreaEmpresa.ordem, AreaEmpresa.empresa)
    )
    return [
        AreaEmpresaOut(id=str(v.id), area=v.area, empresa=v.empresa, ativo=v.ativo, ordem=v.ordem)
        for v in result.scalars().all()
    ]


@router.post("/areas-empresas", response_model=AreaEmpresaOut, status_code=201)
async def create_area_empresa(
    body: AreaEmpresaCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    # Valida que área e empresa existem nas listas configuráveis ativas
    opcoes = await db.execute(
        select(OpcaoLista.valor, OpcaoLista.tipo).where(OpcaoLista.ativo == True)
    )
    ativas: dict[str, set[str]] = {}
    for valor, tipo in opcoes.all():
        ativas.setdefault(tipo, set()).add(valor)
    if body.area not in ativas.get("area", set()):
        raise HTTPException(status_code=422, detail=f"Área inválida: {body.area}")
    if body.empresa not in ativas.get("empresa", set()):
        raise HTTPException(status_code=422, detail=f"Empresa inválida: {body.empresa}")

    dup = await db.execute(
        select(AreaEmpresa).where(
            AreaEmpresa.area == body.area,
            AreaEmpresa.empresa == body.empresa,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Este vínculo já existe")

    vinculo = AreaEmpresa(area=body.area, empresa=body.empresa, ordem=body.ordem)
    db.add(vinculo)
    await db.commit()
    await db.refresh(vinculo)
    return AreaEmpresaOut(
        id=str(vinculo.id), area=vinculo.area, empresa=vinculo.empresa,
        ativo=vinculo.ativo, ordem=vinculo.ordem,
    )


@router.put("/areas-empresas/{vinculo_id}", response_model=AreaEmpresaOut)
async def update_area_empresa(
    vinculo_id: UUID,
    body: AreaEmpresaUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(select(AreaEmpresa).where(AreaEmpresa.id == vinculo_id))
    vinculo = result.scalar_one_or_none()
    if not vinculo:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")

    if body.ativo is not None:
        vinculo.ativo = body.ativo
    if body.ordem is not None:
        vinculo.ordem = body.ordem

    await db.commit()
    await db.refresh(vinculo)
    return AreaEmpresaOut(
        id=str(vinculo.id), area=vinculo.area, empresa=vinculo.empresa,
        ativo=vinculo.ativo, ordem=vinculo.ordem,
    )


@router.delete("/areas-empresas/{vinculo_id}", status_code=204)
async def delete_area_empresa(
    vinculo_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(select(AreaEmpresa).where(AreaEmpresa.id == vinculo_id))
    vinculo = result.scalar_one_or_none()
    if not vinculo:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")
    # Soft delete — desativa em vez de remover (preserva histórico dos FCAs)
    vinculo.ativo = False
    await db.commit()


# ── Dicas de orientação por campo (tooltip "i") ──────────────────────────────

@router.get("/dicas/admin", response_model=list[CampoDicaOut])
async def list_dicas_admin(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    """Lista todas as dicas (incluindo inativas) para gestão pelo admin."""
    result = await db.execute(
        select(CampoDica).order_by(CampoDica.ordem, CampoDica.campo)
    )
    return [
        CampoDicaOut(
            id=str(d.id), campo=d.campo, titulo=d.titulo, texto=d.texto,
            ativo=d.ativo, ordem=d.ordem,
        )
        for d in result.scalars().all()
    ]


@router.post("/dicas", response_model=CampoDicaOut, status_code=201)
async def create_dica(
    body: CampoDicaCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    dup = await db.execute(select(CampoDica).where(CampoDica.campo == body.campo))
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Já existe uma dica para este campo")

    dica = CampoDica(campo=body.campo, titulo=body.titulo, texto=body.texto, ordem=body.ordem)
    db.add(dica)
    await db.commit()
    await db.refresh(dica)
    return CampoDicaOut(
        id=str(dica.id), campo=dica.campo, titulo=dica.titulo, texto=dica.texto,
        ativo=dica.ativo, ordem=dica.ordem,
    )


@router.put("/dicas/{dica_id}", response_model=CampoDicaOut)
async def update_dica(
    dica_id: UUID,
    body: CampoDicaUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(select(CampoDica).where(CampoDica.id == dica_id))
    dica = result.scalar_one_or_none()
    if not dica:
        raise HTTPException(status_code=404, detail="Dica não encontrada")

    if body.titulo is not None:
        dica.titulo = body.titulo
    if body.texto is not None:
        dica.texto = body.texto
    if body.ativo is not None:
        dica.ativo = body.ativo
    if body.ordem is not None:
        dica.ordem = body.ordem

    await db.commit()
    await db.refresh(dica)
    return CampoDicaOut(
        id=str(dica.id), campo=dica.campo, titulo=dica.titulo, texto=dica.texto,
        ativo=dica.ativo, ordem=dica.ordem,
    )


@router.delete("/dicas/{dica_id}", status_code=204)
async def delete_dica(
    dica_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(select(CampoDica).where(CampoDica.id == dica_id))
    dica = result.scalar_one_or_none()
    if not dica:
        raise HTTPException(status_code=404, detail="Dica não encontrada")
    # Soft delete — desativa em vez de remover
    dica.ativo = False
    await db.commit()
