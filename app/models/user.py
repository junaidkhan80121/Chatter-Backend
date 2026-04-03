import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum


class UserStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    away = "away"


class AllowMessagesFrom(str, enum.Enum):
    everyone = "everyone"
    friends = "friends"
    nobody = "nobody"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str] = mapped_column(Text, nullable=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    unique_share_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="offline")
    show_online_status: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_messages_from: Mapped[str] = mapped_column(String(20), default="everyone")
    read_receipts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    sent_friendships: Mapped[list["Friendship"]] = relationship(
        "Friendship", foreign_keys="Friendship.requester_id", back_populates="requester"
    )
    received_friendships: Mapped[list["Friendship"]] = relationship(
        "Friendship", foreign_keys="Friendship.addressee_id", back_populates="addressee"
    )
    blocked_users: Mapped[list["BlockedUser"]] = relationship(
        "BlockedUser", foreign_keys="BlockedUser.blocker_id", back_populates="blocker"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
