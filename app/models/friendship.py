import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Friendship(Base):
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requester_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    addressee_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/accepted/rejected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    requester: Mapped["User"] = relationship("User", foreign_keys=[requester_id], back_populates="sent_friendships")
    addressee: Mapped["User"] = relationship("User", foreign_keys=[addressee_id], back_populates="received_friendships")


class BlockedUser(Base):
    __tablename__ = "blocked_users"

    blocker_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    blocked_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    blocker: Mapped["User"] = relationship("User", foreign_keys=[blocker_id], back_populates="blocked_users")
    blocked: Mapped["User"] = relationship("User", foreign_keys=[blocked_id])
