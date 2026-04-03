from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.repositories.message_repo import ConversationRepository, MessageRepository
from app.schemas.chat import (
    ConversationCreate,
    ConversationOut,
    MessageCreate,
    MessageOut,
    PaginatedMessages,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("", response_model=list[ConversationOut])
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv_repo = ConversationRepository(db)
    msg_repo = MessageRepository(db)
    conversations = await conv_repo.get_user_conversations(current_user.id)

    result = []
    for conv in conversations:
        last_msg = await conv_repo.get_last_message(conv.id)
        participants = [
            UserPublic.model_validate(p.user)
            for p in conv.participants
            if p.user
        ]
        result.append(ConversationOut(
            id=conv.id,
            type=conv.type,
            name=conv.name,
            avatar_url=conv.avatar_url,
            created_by=conv.created_by,
            created_at=conv.created_at,
            archived_at=conv.archived_at,
            pinned_at=conv.pinned_at,
            participants=participants,
            last_message=MessageOut.model_validate(last_msg) if last_msg else None,
            unread_count=0,
        ))
    return result


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv_repo = ConversationRepository(db)

    # For direct chats, check if already exists
    if data.type == "direct" and len(data.participant_ids) == 1:
        other_id = data.participant_ids[0]
        existing = await conv_repo.find_direct(current_user.id, other_id)
        if existing:
            participants = [
                UserPublic.model_validate(p.user)
                for p in existing.participants
                if p.user
            ]
            last_msg = await conv_repo.get_last_message(existing.id)
            return ConversationOut(
                id=existing.id, type=existing.type,
                name=existing.name, avatar_url=existing.avatar_url,
                created_by=existing.created_by, created_at=existing.created_at,
                archived_at=existing.archived_at, pinned_at=existing.pinned_at,
                participants=participants,
                last_message=MessageOut.model_validate(last_msg) if last_msg else None,
            )

    all_participant_ids = list(set([current_user.id] + data.participant_ids))
    conv = await conv_repo.create(
        type=data.type,
        created_by=current_user.id,
        participant_ids=all_participant_ids,
        name=data.name,
    )

    participants = [
        UserPublic.model_validate(p.user)
        for p in conv.participants
        if p.user
    ]
    return ConversationOut(
        id=conv.id, type=conv.type, name=conv.name,
        avatar_url=conv.avatar_url, created_by=conv.created_by,
        created_at=conv.created_at, archived_at=conv.archived_at,
        pinned_at=conv.pinned_at, participants=participants,
    )


@router.get("/{conv_id}/messages", response_model=PaginatedMessages)
async def get_messages(
    conv_id: str,
    limit: int = Query(50, le=100),
    before_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_by_id(conv_id, user_id=current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_repo = MessageRepository(db)
    messages = await msg_repo.get_paginated(conv_id, limit=limit, before_id=before_id)

    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    next_cursor = messages[-1].id if has_more and messages else None

    return PaginatedMessages(
        items=[MessageOut.model_validate(m) for m in reversed(messages)],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.post("/{conv_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    conv_id: str,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_by_id(conv_id, user_id=current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_repo = MessageRepository(db)
    msg = await msg_repo.create(
        conversation_id=conv_id,
        sender_id=current_user.id,
        content=data.content,
        message_type=data.message_type,
        reply_to_id=data.reply_to_id,
    )
    return MessageOut.model_validate(msg)


@router.put("/{conv_id}/archive")
async def archive_conversation(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_by_id(conv_id, user_id=current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.archived_at = datetime.now(timezone.utc)
    return {"message": "Conversation archived"}


@router.put("/{conv_id}/pin")
async def pin_conversation(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_by_id(conv_id, user_id=current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.pinned_at = None if conv.pinned_at else datetime.now(timezone.utc)
    return {"message": "Conversation pin toggled"}


@router.get("/{conv_id}/messages/search", response_model=list[MessageOut])
async def search_messages(
    conv_id: str,
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_by_id(conv_id, user_id=current_user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msg_repo = MessageRepository(db)
    messages = await msg_repo.search(conv_id, q)
    return [MessageOut.model_validate(m) for m in messages]
