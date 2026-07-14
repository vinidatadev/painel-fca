from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from auth import require_user
import storage

router = APIRouter(prefix="/upload", tags=["upload"])
any_user = require_user()


@router.post("/", status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    _: dict = Depends(any_user)
):
    if file.content_type not in storage.ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Tipo não permitido. Use JPEG, PNG, WEBP ou PDF.")

    data = await file.read()
    if len(data) > storage.MAX_SIZE:
        raise HTTPException(status_code=413, detail="Arquivo maior que 20 MB.")

    key = storage.upload_file(file.filename or "arquivo", data, file.content_type)
    return {
        "object_key": key,
        "filename": file.filename,
        "size_bytes": len(data),
        "content_type": file.content_type,
    }


@router.get("/{object_key:path}/url")
async def get_presigned_url(
    object_key: str,
    _: dict = Depends(any_user)
):
    if not storage.object_exists(object_key):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    url = storage.get_presigned_url(object_key)
    return {"url": url, "expires_in_seconds": 3600}
