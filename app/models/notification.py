import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship, MappedColumn
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # message/friend_request/call/system
    title: Mapped[str] = mapped_column(Text, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    data: Mapped[dict] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    user: Mapped["User"] = relationship("User", back_populates="notifications")
