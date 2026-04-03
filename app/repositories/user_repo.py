from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional
import uuid
import random
import string

from app.models.user import User
from app.core.security import hash_password


def generate_share_id(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "PC-" + "".join(random.choices(chars, k=length))


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.username == username.lower(), User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_by_share_id(self, share_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.unique_share_id == share_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create(self, username: str, email: str, password: str, display_name: Optional[str] = None) -> User:
        user = User(
            id=str(uuid.uuid4()),
            username=username.lower(),
            email=email.lower(),
            display_name=display_name or username,
            password_hash=hash_password(password),
            unique_share_id=generate_share_id(),
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def search(self, query: str, limit: int = 20, exclude_user_id: str = None) -> list[User]:
        stmt = select(User).where(
            User.deleted_at.is_(None),
            or_(
                User.username.ilike(f"%{query}%"),
                User.display_name.ilike(f"%{query}%"),
                User.unique_share_id == query.upper(),
            ),
        )
        if exclude_user_id:
            stmt = stmt.where(User.id != exclude_user_id)
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def update(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        await self.db.flush()
        return user
