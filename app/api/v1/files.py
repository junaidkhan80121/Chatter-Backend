from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid, os, aiofiles

from app.core.database import get_db
from app.core.config import settings
from app.api.v1.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/files", tags=["Files"])

ALLOWED_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "application/pdf", "text/plain", "application/zip", "application/json",
    "video/mp4", "video/webm", "video/quicktime", "video/x-matroska",
    "audio/mpeg", "audio/ogg", "audio/wav", "audio/webm", "audio/mp4",
}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {file.content_type}")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_FILE_SIZE_MB}MB")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    # Determine message_type
    if file.content_type.startswith("image/"):
        msg_type = "image"
    elif file.content_type.startswith("video/"):
        msg_type = "video"
    elif file.content_type.startswith("audio/"):
        msg_type = "audio"
    else:
        msg_type = "file"

    return {
        "file_url": f"/uploads/{filename}",
        "file_name": file.filename,
        "file_size": len(content),
        "message_type": msg_type,
        "content_type": file.content_type,
    }
