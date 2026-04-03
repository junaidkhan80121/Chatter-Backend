from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.friendship import Friendship, BlockedUser
from app.repositories.user_repo import UserRepository
from app.schemas.chat import FriendRequestCreate, FriendshipOut
from app.schemas.user import UserPublic

router = APIRouter(prefix="/friends", tags=["Friends"])


@router.get("", response_model=list[FriendshipOut])
async def get_friends(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Friendship).where(
            or_(
                Friendship.requester_id == current_user.id,
                Friendship.addressee_id == current_user.id,
            ),
            Friendship.status == "accepted",
        )
    )
    friendships = result.scalars().all()

    # Load user data for each friendship
    out = []
    user_repo = UserRepository(db)
    for f in friendships:
        requester = await user_repo.get_by_id(f.requester_id)
        addressee = await user_repo.get_by_id(f.addressee_id)
        out.append(FriendshipOut(
            id=f.id,
            requester_id=f.requester_id,
            addressee_id=f.addressee_id,
            status=f.status,
            created_at=f.created_at,
            requester=UserPublic.model_validate(requester) if requester else None,
            addressee=UserPublic.model_validate(addressee) if addressee else None,
        ))
    return out


@router.get("/requests", response_model=list[FriendshipOut])
async def get_friend_requests(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Friendship).where(
            Friendship.addressee_id == current_user.id,
            Friendship.status == "pending",
        )
    )
    friendships = result.scalars().all()
    user_repo = UserRepository(db)
    out = []
    for f in friendships:
        requester = await user_repo.get_by_id(f.requester_id)
        out.append(FriendshipOut(
            id=f.id,
            requester_id=f.requester_id,
            addressee_id=f.addressee_id,
            status=f.status,
            created_at=f.created_at,
            requester=UserPublic.model_validate(requester) if requester else None,
        ))
    return out


@router.post("/request")
async def send_friend_request(
    data: FriendRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_repo = UserRepository(db)

    # Find target user
    target = None
    if data.addressee_id:
        target = await user_repo.get_by_id(data.addressee_id)
    elif data.username:
        target = await user_repo.get_by_username(data.username)
    elif data.unique_share_id:
        target = await user_repo.get_by_share_id(data.unique_share_id)

    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself")

    # Check existing
    existing = await db.execute(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == target.id),
                and_(Friendship.requester_id == target.id, Friendship.addressee_id == current_user.id),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Friend request already exists")

    friendship = Friendship(
        requester_id=current_user.id,
        addressee_id=target.id,
    )
    db.add(friendship)
    return {"message": "Friend request sent", "friendship_id": friendship.id}


@router.put("/{friendship_id}/accept")
async def accept_friend_request(
    friendship_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Friendship).where(
            Friendship.id == friendship_id,
            Friendship.addressee_id == current_user.id,
            Friendship.status == "pending",
        )
    )
    friendship = result.scalar_one_or_none()
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")

    friendship.status = "accepted"
    return {"message": "Friend request accepted"}


@router.put("/{friendship_id}/reject")
async def reject_friend_request(
    friendship_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Friendship).where(
            Friendship.id == friendship_id,
            Friendship.addressee_id == current_user.id,
            Friendship.status == "pending",
        )
    )
    friendship = result.scalar_one_or_none()
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found")

    friendship.status = "rejected"
    return {"message": "Friend request rejected"}


@router.post("/{user_id}/block")
async def block_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")

    existing = await db.execute(
        select(BlockedUser).where(
            BlockedUser.blocker_id == current_user.id,
            BlockedUser.blocked_id == user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already blocked")

    db.add(BlockedUser(blocker_id=current_user.id, blocked_id=user_id))
    return {"message": "User blocked"}


@router.delete("/{user_id}/block")
async def unblock_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BlockedUser).where(
            BlockedUser.blocker_id == current_user.id,
            BlockedUser.blocked_id == user_id,
        )
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    await db.delete(block)
    return {"message": "User unblocked"}
