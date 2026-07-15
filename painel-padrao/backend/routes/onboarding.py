"""
Rotas de Onboarding.

Admin:
  GET    /onboarding/admin/videos             → lista todos os vídeos (ativos e inativos)
  POST   /onboarding/admin/videos             → cria vídeo (upload do arquivo)
  PUT    /onboarding/admin/videos/{id}        → atualiza título/descrição/ordem/ativo
  DELETE /onboarding/admin/videos/{id}        → remove vídeo + arquivo do MinIO
  POST   /onboarding/admin/videos/reorder     → reordena lista

User:
  GET    /onboarding/videos                   → lista vídeos ativos com status de progresso
  POST   /onboarding/videos/{id}/concluir     → marca vídeo como assistido
  GET    /onboarding/status                   → retorna se onboarding está completo
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from database import get_db
from models import OnboardingVideo, OnboardingProgresso, User
from auth import require_user
import onboarding_storage

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
any_user = require_user()
only_admin = require_user(required_role="admin")

MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 MB


# ── Schemas ───────────────────────────────────────────────────────────────────

class VideoUpdate(BaseModel):
    titulo: str | None = None
    descricao: str | None = None
    ordem: int | None = None
    ativo: bool | None = None


class ReorderItem(BaseModel):
    id: str
    ordem: int


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/videos")
async def admin_list_videos(
    current: dict = Depends(only_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OnboardingVideo).order_by(OnboardingVideo.ordem, OnboardingVideo.created_at)
    )
    videos = result.scalars().all()
    return [_fmt_admin(v) for v in videos]


@router.post("/admin/videos", status_code=201)
async def admin_create_video(
    titulo: str = Form(...),
    descricao: str = Form(""),
    ordem: int = Form(0),
    video: UploadFile = File(...),
    current: dict = Depends(only_admin),
    db: AsyncSession = Depends(get_db),
):
    if video.content_type not in onboarding_storage.ALLOWED_VIDEO_TYPES:
        raise HTTPException(400, "Tipo de arquivo não suportado. Use MP4, WebM ou OGG.")

    data = await video.read()
    if len(data) > MAX_VIDEO_SIZE:
        raise HTTPException(413, "Arquivo excede o limite de 500 MB.")

    key = onboarding_storage.upload_video(video.filename or "video.mp4", data, video.content_type)

    novo = OnboardingVideo(
        titulo=titulo,
        descricao=descricao or None,
        video_key=key,
        ordem=ordem,
    )
    db.add(novo)
    await db.commit()
    await db.refresh(novo)
    return _fmt_admin(novo)


@router.put("/admin/videos/{video_id}")
async def admin_update_video(
    video_id: str,
    body: VideoUpdate,
    current: dict = Depends(only_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OnboardingVideo).where(OnboardingVideo.id == uuid.UUID(video_id)))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Vídeo não encontrado")

    if body.titulo is not None:
        video.titulo = body.titulo
    if body.descricao is not None:
        video.descricao = body.descricao
    if body.ordem is not None:
        video.ordem = body.ordem
    if body.ativo is not None:
        video.ativo = body.ativo

    await db.commit()
    await db.refresh(video)
    return _fmt_admin(video)


@router.delete("/admin/videos/{video_id}", status_code=204)
async def admin_delete_video(
    video_id: str,
    current: dict = Depends(only_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(OnboardingVideo).where(OnboardingVideo.id == uuid.UUID(video_id)))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Vídeo não encontrado")

    # Remove do MinIO
    onboarding_storage.delete_video(video.video_key)

    await db.execute(delete(OnboardingVideo).where(OnboardingVideo.id == video.id))
    await db.commit()


@router.post("/admin/videos/reorder")
async def admin_reorder_videos(
    body: list[ReorderItem],
    current: dict = Depends(only_admin),
    db: AsyncSession = Depends(get_db),
):
    for item in body:
        result = await db.execute(select(OnboardingVideo).where(OnboardingVideo.id == uuid.UUID(item.id)))
        video = result.scalar_one_or_none()
        if video:
            video.ordem = item.ordem
    await db.commit()
    return {"ok": True}


# ── User endpoints ────────────────────────────────────────────────────────────

@router.get("/videos")
async def list_videos_user(
    current: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna vídeos ativos com status de assistido para o usuário logado."""
    user_id = uuid.UUID(current["user_id"])

    videos_result = await db.execute(
        select(OnboardingVideo)
        .where(OnboardingVideo.ativo == True)
        .order_by(OnboardingVideo.ordem, OnboardingVideo.created_at)
    )
    videos = videos_result.scalars().all()

    # Progressos do usuário
    prog_result = await db.execute(
        select(OnboardingProgresso.video_id).where(OnboardingProgresso.user_id == user_id)
    )
    assistidos = {row[0] for row in prog_result.fetchall()}

    resultado = []
    for i, v in enumerate(videos):
        # Só pode assistir em ordem: libera se todos anteriores já foram assistidos
        anteriores_ok = all(videos[j].id in assistidos for j in range(i))
        resultado.append({
            **_fmt_user(v),
            "assistido": v.id in assistidos,
            "liberado": i == 0 or anteriores_ok,
        })

    return resultado


@router.post("/videos/{video_id}/concluir")
async def concluir_video(
    video_id: str,
    current: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current["user_id"])
    vid_uuid = uuid.UUID(video_id)

    # Verifica se o vídeo existe e está ativo
    result = await db.execute(
        select(OnboardingVideo).where(OnboardingVideo.id == vid_uuid, OnboardingVideo.ativo == True)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Vídeo não encontrado")

    # Verifica se já assistiu
    prog_result = await db.execute(
        select(OnboardingProgresso).where(
            OnboardingProgresso.user_id == user_id,
            OnboardingProgresso.video_id == vid_uuid,
        )
    )
    if prog_result.scalar_one_or_none():
        return {"ok": True, "onboarding_completed": await _check_completed(user_id, db)}

    # Verifica se pode assistir (ordem)
    all_videos_result = await db.execute(
        select(OnboardingVideo)
        .where(OnboardingVideo.ativo == True)
        .order_by(OnboardingVideo.ordem, OnboardingVideo.created_at)
    )
    all_videos = all_videos_result.scalars().all()

    video_index = next((i for i, v in enumerate(all_videos) if v.id == vid_uuid), None)
    if video_index is None:
        raise HTTPException(404, "Vídeo não encontrado")

    if video_index > 0:
        prev_id = all_videos[video_index - 1].id
        prev_result = await db.execute(
            select(OnboardingProgresso).where(
                OnboardingProgresso.user_id == user_id,
                OnboardingProgresso.video_id == prev_id,
            )
        )
        if not prev_result.scalar_one_or_none():
            raise HTTPException(400, "Assista os vídeos anteriores primeiro.")

    db.add(OnboardingProgresso(user_id=user_id, video_id=vid_uuid))
    await db.flush()

    completed = await _check_completed(user_id, db)
    if completed:
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user and not user.onboarding_completed:
            user.onboarding_completed = True

    await db.commit()
    return {"ok": True, "onboarding_completed": completed}


@router.get("/status")
async def onboarding_status(
    current: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    user_id = uuid.UUID(current["user_id"])
    completed = await _check_completed(user_id, db)
    return {"onboarding_completed": completed}


@router.get("/videos/{video_id}/url")
async def get_video_url(
    video_id: str,
    current: dict = Depends(any_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna URL pré-assinada para streaming do vídeo."""
    user_id = uuid.UUID(current["user_id"])
    vid_uuid = uuid.UUID(video_id)

    result = await db.execute(
        select(OnboardingVideo).where(OnboardingVideo.id == vid_uuid, OnboardingVideo.ativo == True)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(404, "Vídeo não encontrado")

    # Verifica se está liberado para este usuário
    all_videos_result = await db.execute(
        select(OnboardingVideo)
        .where(OnboardingVideo.ativo == True)
        .order_by(OnboardingVideo.ordem, OnboardingVideo.created_at)
    )
    all_videos = all_videos_result.scalars().all()
    video_index = next((i for i, v in enumerate(all_videos) if v.id == vid_uuid), None)

    if video_index is None:
        raise HTTPException(404, "Vídeo não encontrado")

    if video_index > 0:
        prog_result = await db.execute(
            select(OnboardingProgresso.video_id).where(OnboardingProgresso.user_id == user_id)
        )
        assistidos = {row[0] for row in prog_result.fetchall()}
        if all_videos[video_index - 1].id not in assistidos:
            raise HTTPException(403, "Assista os vídeos anteriores primeiro.")

    url = onboarding_storage.get_video_presigned_url(video.video_key)
    return {"url": url, "expires_in": 7200}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _check_completed(user_id: uuid.UUID, db: AsyncSession) -> bool:
    """Retorna True se não há vídeos ativos ou se o usuário assistiu todos."""
    total_result = await db.execute(
        select(OnboardingVideo).where(OnboardingVideo.ativo == True)
    )
    total_videos = total_result.scalars().all()
    if not total_videos:
        return True

    prog_result = await db.execute(
        select(OnboardingProgresso.video_id).where(OnboardingProgresso.user_id == user_id)
    )
    assistidos = {row[0] for row in prog_result.fetchall()}
    return all(v.id in assistidos for v in total_videos)


def _fmt_admin(v: OnboardingVideo) -> dict:
    return {
        "id": str(v.id),
        "titulo": v.titulo,
        "descricao": v.descricao,
        "video_key": v.video_key,
        "ordem": v.ordem,
        "ativo": v.ativo,
        "created_at": v.created_at.isoformat(),
    }


def _fmt_user(v: OnboardingVideo) -> dict:
    return {
        "id": str(v.id),
        "titulo": v.titulo,
        "descricao": v.descricao,
        "ordem": v.ordem,
    }
