import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id", "created_at"),
        Index("idx_messages_sender", "sender_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id"), nullable=False
    )
    sender_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    message_type: Mapped[str] = mapped_column(String(20), default="text")  # text/image/file/audio
    file_url: Mapped[str] = mapped_column(Text, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int] = mapped_column(nullable=True)
    reply_to_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id"), nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="sent")  # sent/delivered/read
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
    sender: Mapped["User"] = relationship("User")
    reply_to: Mapped["Message"] = relationship("Message", remote_side="Message.id", foreign_keys=[reply_to_id])
    reads: Mapped[list["MessageRead"]] = relationship("MessageRead", back_populates="message")


class MessageRead(Base):
    __tablename__ = "message_reads"

    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True, index=True)
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    message: Mapped["Message"] = relationship("Message", back_populates="reads")
    user: Mapped["User"] = relationship("User")
