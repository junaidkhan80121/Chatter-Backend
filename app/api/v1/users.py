from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserOut, UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)


@router.put("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = UserRepository(db)
    updated = await repo.update(current_user, **data.model_dump(exclude_none=True))
    return UserOut.model_validate(updated)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import os, aiofiles, uuid
    from app.core.config import settings

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1]
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(settings.UPLOAD_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        content = await file.read()
        await f.write(content)

    avatar_url = f"/uploads/{filename}"
    repo = UserRepository(db)
    updated = await repo.update(current_user, avatar_url=avatar_url)
    return UserOut.model_validate(updated)


@router.get("/search", response_model=list[UserPublic])
async def search_users(
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if len(q) < 2:
        raise HTTPException(status_code=400, detail="Search query too short")
    repo = UserRepository(db)
    users = await repo.search(q, exclude_user_id=current_user.id)
    return [UserPublic.model_validate(u) for u in users]


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if blocked
    from sqlalchemy import select
    from app.models.friendship import BlockedUser
    block = await db.execute(
        select(BlockedUser).where(
            BlockedUser.blocker_id == user_id,
            BlockedUser.blocked_id == current_user.id,
        )
    )
    if block.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Access denied")

    # Respect privacy setting
    if not user.show_online_status:
        user.status = "offline"
        user.last_seen = None

    return UserPublic.model_validate(user)
