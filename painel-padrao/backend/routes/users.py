from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from database import get_db
from models import User, OpcaoLista, AreaEmpresa, UserSetor
from auth import hash_password, require_user

router = APIRouter(prefix="/usuarios", tags=["usuarios"])
admin_only = require_user(required_role="admin")


async def _opcoes_ativas(db: AsyncSession, tipo: str) -> set[str]:
    result = await db.execute(
        select(OpcaoLista.valor).where(
            OpcaoLista.tipo == tipo, OpcaoLista.ativo == True
        )
    )
    return set(result.scalars().all())


async def _combo_ativo(db: AsyncSession, area: str, empresa: str) -> bool:
    result = await db.execute(
        select(AreaEmpresa.id).where(
            AreaEmpresa.area == area,
            AreaEmpresa.empresa == empresa,
            AreaEmpresa.ativo == True,
        )
    )
    return result.scalar_one_or_none() is not None


class VinculoIn(BaseModel):
    setor: str
    empresa: str
    principal: bool = False


async def _validar_setores(db: AsyncSession, setores: list[VinculoIn]) -> list[dict]:
    """Valida a lista de vínculos e garante exatamente um principal."""
    if not setores:
        raise HTTPException(status_code=422, detail="Informe ao menos um setor/empresa")

    empresas_ativas = await _opcoes_ativas(db, "empresa")
    areas_ativas = await _opcoes_ativas(db, "area")
    seen: set[tuple[str, str]] = set()
    principals = 0
    for v in setores:
        if (v.setor, v.empresa) in seen:
            raise HTTPException(status_code=422, detail=f"Vínculo repetido: {v.setor} + {v.empresa}")
        seen.add((v.setor, v.empresa))
        if v.setor not in areas_ativas:
            raise HTTPException(status_code=422, detail=f"Setor '{v.setor}' inválido")
        if v.empresa not in empresas_ativas:
            raise HTTPException(status_code=422, detail=f"Empresa inválida: {v.empresa}")
        if not await _combo_ativo(db, v.setor, v.empresa):
            raise HTTPException(
                status_code=422,
                detail=f"Combinação '{v.setor}' + '{v.empresa}' não permitida nas configurações",
            )
        if v.principal:
            principals += 1

    if principals > 1:
        raise HTTPException(status_code=422, detail="Marque apenas um setor como principal")
    if principals == 0:
        setores[0].principal = True

    return [{"setor": v.setor, "empresa": v.empresa, "principal": v.principal} for v in setores]


async def _sync_setores(db: AsyncSession, user: User, setores: list[dict]):
    """Substitui os vínculos do usuário e atualiza User.sector/company (principal)."""
    await db.execute(delete(UserSetor).where(UserSetor.user_id == user.id))
    for s in setores:
        db.add(UserSetor(
            user_id=user.id, setor=s["setor"], empresa=s["empresa"], principal=s["principal"]
        ))
    principal = next((s for s in setores if s["principal"]), setores[0])
    user.sector = principal["setor"]
    user.company = principal["empresa"]


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    company: str
    sector: str
    role: str
    auth_provider: str
    matricula: str | None
    turno: str | None
    is_active: bool
    acesso_relatorio: bool
    created_at: str
    setores: list[dict] = []

    @classmethod
    def from_orm(cls, u: User):
        return cls(
            id=str(u.id), email=u.email, name=u.name,
            company=u.company, sector=u.sector, role=u.role,
            auth_provider=u.auth_provider,
            matricula=u.matricula, turno=u.turno,
            is_active=u.is_active,
            acesso_relatorio=u.acesso_relatorio,
            created_at=u.created_at.isoformat(),
            setores=[
                {"setor": s.setor, "empresa": s.empresa, "principal": s.principal}
                for s in (u.setores or [])
            ],
        )


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8)
    auth_provider: Literal["local", "microsoft"] = "local"
    company: str | None = None
    sector: str | None = None
    setores: list[VinculoIn] = []
    role: Literal["admin", "user"] = "user"
    matricula: str | None = None
    turno: Literal["A", "B", "C", "D"] | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    company: str | None = None
    sector: str | None = None
    setores: list[VinculoIn] | None = None
    role: Literal["admin", "user"] | None = None
    matricula: str | None = None
    turno: Literal["A", "B", "C", "D"] | None = None
    password: str | None = Field(default=None, min_length=8)


class UserPatch(BaseModel):
    acesso_relatorio: bool | None = None


@router.get("/", response_model=list[UserOut])
async def list_users(
    company: str | None = None,
    sector: str | None = None,
    active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    q = select(User).options(selectinload(User.setores)).order_by(User.name)
    if company or sector:
        q = q.join(UserSetor, UserSetor.user_id == User.id)
        if company:
            q = q.where(UserSetor.empresa == company)
        if sector:
            q = q.where(UserSetor.setor == sector)
    if active is not None:
        q = q.where(User.is_active == active)
    result = await db.execute(q)
    return [UserOut.from_orm(u) for u in result.scalars().unique().all()]


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    if not body.setores:
        if body.company and body.sector:
            body.setores = [VinculoIn(setor=body.sector, empresa=body.company, principal=True)]
        else:
            raise HTTPException(status_code=422, detail="Informe ao menos um setor/empresa")

    setores = await _validar_setores(db, body.setores)
    principal = next((s for s in setores if s["principal"]), setores[0])

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    if body.auth_provider == "local" and not body.password:
        raise HTTPException(status_code=422, detail="Senha obrigatória para login local")

    user = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password) if body.password else None,
        auth_provider=body.auth_provider,
        company=principal["empresa"],
        sector=principal["setor"],
        role=body.role,
        matricula=body.matricula,
        turno=body.turno,
        must_change_password=True,   # primeiro acesso sempre exige troca de senha
        onboarding_completed=False,  # precisa passar pelo onboarding
    )
    db.add(user)
    await db.flush()
    for s in setores:
        db.add(UserSetor(
            user_id=user.id, setor=s["setor"], empresa=s["empresa"], principal=s["principal"]
        ))
    await db.commit()

    result = await db.execute(
        select(User).options(selectinload(User.setores)).where(User.id == user.id)
    )
    return UserOut.from_orm(result.scalar_one())


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(
        select(User).options(selectinload(User.setores)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return UserOut.from_orm(user)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(
        select(User).options(selectinload(User.setores)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if body.name is not None:
        user.name = body.name
    if body.role is not None:
        user.role = body.role
    if body.matricula is not None:
        user.matricula = body.matricula
    if body.turno is not None:
        user.turno = body.turno
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    if body.setores is not None:
        setores = await _validar_setores(db, body.setores)
        await _sync_setores(db, user, setores)
    elif body.company is not None or body.sector is not None:
        # Compatibilidade: atualiza o vínculo único
        vinculos = [VinculoIn(
            setor=body.sector or user.sector,
            empresa=body.company or user.company,
            principal=True,
        )]
        setores = await _validar_setores(db, vinculos)
        await _sync_setores(db, user, setores)

    await db.commit()
    # Recarrega com a relação de setores (populate_existing evita que a coleção
    # já carregada na sessão volte "velha" após o _sync_setores)
    result = await db.execute(
        select(User)
        .options(selectinload(User.setores))
        .execution_options(populate_existing=True)
        .where(User.id == user.id)
    )
    return UserOut.from_orm(result.scalar_one())


@router.patch("/{user_id}", response_model=UserOut)
async def patch_user(
    user_id: UUID,
    body: UserPatch,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only),
):
    result = await db.execute(
        select(User).options(selectinload(User.setores)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if body.acesso_relatorio is not None:
        user.acesso_relatorio = body.acesso_relatorio
    await db.commit()
    await db.refresh(user)
    return UserOut.from_orm(user)


@router.patch("/{user_id}/desativar", response_model=dict)
async def desativar_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: dict = Depends(admin_only)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if str(user.id) == current["user_id"]:
        raise HTTPException(status_code=400, detail="Não é possível desativar sua própria conta")
    user.is_active = False
    await db.commit()
    return {"active": False}
