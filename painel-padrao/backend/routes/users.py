from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User, OpcaoLista, AreaEmpresa
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

    @classmethod
    def from_orm(cls, u: User):
        return cls(
            id=str(u.id), email=u.email, name=u.name,
            company=u.company, sector=u.sector, role=u.role,
            auth_provider=u.auth_provider,
            matricula=u.matricula, turno=u.turno,
            is_active=u.is_active,
            acesso_relatorio=u.acesso_relatorio,
            created_at=u.created_at.isoformat()
        )


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8)
    auth_provider: Literal["local", "microsoft"] = "local"
    company: str
    sector: str
    role: Literal["admin", "user"] = "user"
    matricula: str | None = None
    turno: Literal["A", "B", "C", "D"] | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    company: str | None = None
    sector: str | None = None
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
    q = select(User).order_by(User.name)
    if company:
        q = q.where(User.company == company)
    if sector:
        q = q.where(User.sector == sector)
    if active is not None:
        q = q.where(User.is_active == active)
    result = await db.execute(q)
    return [UserOut.from_orm(u) for u in result.scalars().all()]


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    empresas_ativas = await _opcoes_ativas(db, "empresa")
    areas_ativas = await _opcoes_ativas(db, "area")
    if body.company not in empresas_ativas:
        raise HTTPException(status_code=422, detail=f"Empresa inválida: {body.company}")
    if body.sector not in areas_ativas:
        raise HTTPException(status_code=422, detail=f"Setor '{body.sector}' inválido")
    if not await _combo_ativo(db, body.sector, body.company):
        raise HTTPException(
            status_code=422,
            detail=f"Combinação '{body.sector}' + '{body.company}' não permitida nas configurações",
        )

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
        company=body.company,
        sector=body.sector,
        role=body.role,
        matricula=body.matricula,
        turno=body.turno,
        must_change_password=True,   # primeiro acesso sempre exige troca de senha
        onboarding_completed=False,  # precisa passar pelo onboarding
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.from_orm(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only)
):
    result = await db.execute(select(User).where(User.id == user_id))
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
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    company = body.company or user.company
    sector = body.sector or user.sector
    if body.company or body.sector:
        empresas_ativas = await _opcoes_ativas(db, "empresa")
        areas_ativas = await _opcoes_ativas(db, "area")
        if company not in empresas_ativas:
            raise HTTPException(status_code=422, detail=f"Empresa inválida: {company}")
        if sector not in areas_ativas:
            raise HTTPException(status_code=422, detail=f"Setor '{sector}' inválido")
        if not await _combo_ativo(db, sector, company):
            raise HTTPException(
                status_code=422,
                detail=f"Combinação '{sector}' + '{company}' não permitida nas configurações",
            )

    if body.name is not None:
        user.name = body.name
    if body.company is not None:
        user.company = body.company
    if body.sector is not None:
        user.sector = body.sector
    if body.role is not None:
        user.role = body.role
    if body.matricula is not None:
        user.matricula = body.matricula
    if body.turno is not None:
        user.turno = body.turno
    if body.password is not None:
        user.password_hash = hash_password(body.password)

    await db.commit()
    await db.refresh(user)
    return UserOut.from_orm(user)


@router.patch("/{user_id}", response_model=UserOut)
async def patch_user(
    user_id: UUID,
    body: UserPatch,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(admin_only),
):
    result = await db.execute(select(User).where(User.id == user_id))
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
