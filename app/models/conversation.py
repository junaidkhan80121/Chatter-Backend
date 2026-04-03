import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(String(10), default="direct")  # direct/group
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    pinned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    participants: Mapped[list["ConversationParticipant"]] = relationship(
        "ConversationParticipant", back_populates="conversation"
    )
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation")


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    role: Mapped[str] = mapped_column(String(10), default="member")  # admin/member

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="participants")
    user: Mapped["User"] = relationship("User")
