import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models import User
from auth import hash_password, verify_password, create_local_token, require_user
from limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class SetupRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class MeResponse(BaseModel):
    id: str
    email: str
    name: str
    company: str
    sector: str
    matricula: str | None
    turno: str | None
    role: str
    provider: str
    notif_push: bool
    notif_som: str
    avatar_url: str | None
    acesso_relatorio: bool
    must_change_password: bool
    onboarding_completed: bool


@router.get("/me", response_model=MeResponse)
async def me(
    current: dict = Depends(require_user()),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.email == current["email"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return MeResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        company=user.company,
        sector=user.sector,
        matricula=user.matricula,
        turno=user.turno,
        role=user.role,
        provider=current["provider"],
        notif_push=user.notif_push,
        notif_som=user.notif_som if user.notif_som else "som1",
        avatar_url=user.avatar_url,
        acesso_relatorio=user.acesso_relatorio,
        must_change_password=user.must_change_password,
        onboarding_completed=user.onboarding_completed,
    )


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if (
        not user
        or user.auth_provider != "local"
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token = create_local_token(str(user.id), user.email, user.name, user.role,
                               user.company, user.sector)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "company": user.company,
            "sector": user.sector,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "acesso_relatorio": user.acesso_relatorio,
            "must_change_password": user.must_change_password,
            "onboarding_completed": user.onboarding_completed,
        }
    }


@router.post("/setup", status_code=status.HTTP_201_CREATED)
async def setup_first_admin(request: Request, body: SetupRequest, db: AsyncSession = Depends(get_db)):
    """Cria o primeiro admin (Customer Service / ACC). Bloqueado após primeiro uso."""
    count = await db.execute(select(func.count()).select_from(User))
    if count.scalar() > 0:
        logger.warning("[SETUP] Tentativa bloqueada de %s", request.client.host)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Setup já realizado")
    admin = User(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        auth_provider="local",
        company="ACC",
        sector="Customer_Service",
        role="admin",
        is_active=True,
        must_change_password=False,
        onboarding_completed=True,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)

    token = create_local_token(str(admin.id), admin.email, admin.name, admin.role,
                               admin.company, admin.sector)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(admin.id),
            "name": admin.name,
            "email": admin.email,
            "company": admin.company,
            "sector": admin.sector,
            "role": admin.role,
        }
    }

@router.get("/setup/status")
async def setup_status(db: AsyncSession = Depends(get_db)):
    """Retorna se o setup inicial ainda está disponível (banco sem usuários)."""
    count = await db.execute(select(func.count()).select_from(User))
    return {"setup_disponivel": count.scalar() == 0}


class ChangePasswordRequest(BaseModel):
    nova_senha: str = Field(..., min_length=8, max_length=100)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current: dict = Depends(require_user()),
    db: AsyncSession = Depends(get_db),
):
    """Troca a senha do usuário logado. Limpa o flag must_change_password."""
    result = await db.execute(select(User).where(User.email == current["email"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if user.auth_provider != "local":
        raise HTTPException(status_code=400, detail="Conta Microsoft não usa senha local")

    user.password_hash = hash_password(body.nova_senha)
    user.must_change_password = False
    await db.commit()
    return {"ok": True}
