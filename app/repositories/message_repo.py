from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, desc, exists
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional
import uuid
from datetime import datetime, timezone

from app.models.conversation import Conversation, ConversationParticipant
from app.models.message import Message, MessageRead, MessageHidden
from app.models.user import User


class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        conversation_id: str,
        sender_id: str,
        content: Optional[str],
        message_type: str = "text",
        reply_to_id: Optional[str] = None,
        file_url: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None,
    ) -> Message:
        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            reply_to_id=reply_to_id,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
        )
        self.db.add(msg)
        await self.db.flush()

        # Eager load sender
        await self.db.refresh(msg, ["sender"])
        return msg

    async def get_paginated(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
    ) -> list[Message]:
        hidden_subquery = (
            select(MessageHidden.message_id)
            .where(
                MessageHidden.message_id == Message.id,
                MessageHidden.user_id == user_id,
            )
            .exists()
        )

        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
                ~hidden_subquery,
            )
            .options(selectinload(Message.sender))
            .order_by(desc(Message.created_at))
            .limit(limit + 1)
        )

        if before_id:
            # Get cursor message timestamp
            cursor_stmt = select(Message.created_at).where(Message.id == before_id)
            cursor_result = await self.db.execute(cursor_stmt)
            cursor_ts = cursor_result.scalar_one_or_none()
            if cursor_ts:
                stmt = stmt.where(Message.created_at < cursor_ts)

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def search(self, conversation_id: str, user_id: str, query: str, limit: int = 30) -> list[Message]:
        hidden_subquery = (
            select(MessageHidden.message_id)
            .where(
                MessageHidden.message_id == Message.id,
                MessageHidden.user_id == user_id,
            )
            .exists()
        )
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.content.ilike(f"%{query}%"),
                Message.deleted_at.is_(None),
                ~hidden_subquery,
            )
            .options(selectinload(Message.sender))
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def mark_read(self, message_ids: list[str], user_id: str):
        for msg_id in message_ids:
            existing = await self.db.execute(
                select(MessageRead).where(
                    MessageRead.message_id == msg_id,
                    MessageRead.user_id == user_id,
                )
            )
            if not existing.scalar_one_or_none():
                self.db.add(MessageRead(message_id=msg_id, user_id=user_id))
        await self.db.flush()

    async def get_by_id(self, message_id: str) -> Optional[Message]:
        result = await self.db.execute(
            select(Message)
            .where(Message.id == message_id)
            .options(selectinload(Message.sender))
        )
        return result.scalar_one_or_none()

    async def hide_for_user(self, message_id: str, user_id: str):
        existing = await self.db.execute(
            select(MessageHidden).where(
                MessageHidden.message_id == message_id,
                MessageHidden.user_id == user_id,
            )
        )
        if existing.scalar_one_or_none():
            return
        self.db.add(MessageHidden(message_id=message_id, user_id=user_id))
        await self.db.flush()

    async def delete_for_everyone(self, message: Message):
        message.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()


class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_conversations(self, user_id: str) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.id,
            )
            .where(ConversationParticipant.user_id == user_id)
            .options(
                selectinload(Conversation.participants).selectinload(
                    ConversationParticipant.user
                )
            )
            .order_by(desc(Conversation.pinned_at.is_(None)), desc(Conversation.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().unique().all()

    async def get_by_id(self, conv_id: str, user_id: str = None) -> Optional[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.id == conv_id)
            .options(
                selectinload(Conversation.participants).selectinload(
                    ConversationParticipant.user
                )
            )
        )
        result = await self.db.execute(stmt)
        conv = result.scalar_one_or_none()

        if conv and user_id:
            # Verify user is a participant
            is_participant = any(p.user_id == user_id for p in conv.participants)
            return conv if is_participant else None
        return conv

    async def create(
        self,
        type: str,
        created_by: str,
        participant_ids: list[str],
        name: Optional[str] = None,
    ) -> Conversation:
        conv = Conversation(
            id=str(uuid.uuid4()),
            type=type,
            name=name,
            created_by=created_by,
        )
        self.db.add(conv)
        await self.db.flush()

        for uid in participant_ids:
            role = "admin" if uid == created_by else "member"
            participant = ConversationParticipant(
                conversation_id=conv.id,
                user_id=uid,
                role=role,
            )
            self.db.add(participant)

        await self.db.flush()
        await self.db.refresh(conv, ["participants"])
        return conv

    async def find_direct(self, user1_id: str, user2_id: str) -> Optional[Conversation]:
        """Find existing direct conversation between two users"""
        stmt = """
            SELECT c.id FROM conversations c
            JOIN conversation_participants cp1 ON cp1.conversation_id = c.id AND cp1.user_id = :u1
            JOIN conversation_participants cp2 ON cp2.conversation_id = c.id AND cp2.user_id = :u2
            WHERE c.type = 'direct'
            LIMIT 1
        """
        from sqlalchemy import text
        result = await self.db.execute(
            text(stmt), {"u1": user1_id, "u2": user2_id}
        )
        row = result.fetchone()
        if row:
            return await self.get_by_id(row[0])
        return None

    async def get_last_message(self, conversation_id: str, user_id: Optional[str] = None) -> Optional[Message]:
        from app.models.message import Message
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
            .options(selectinload(Message.sender))
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        if user_id:
            hidden_subquery = (
                select(MessageHidden.message_id)
                .where(
                    MessageHidden.message_id == Message.id,
                    MessageHidden.user_id == user_id,
                )
                .exists()
            )
            stmt = stmt.where(~hidden_subquery)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
