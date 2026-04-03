from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.user import UserPublic


class MessageCreate(BaseModel):
    content: Optional[str] = None
    message_type: str = "text"
    reply_to_id: Optional[str] = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    sender_id: str
    content: Optional[str]
    message_type: str
    file_url: Optional[str]
    file_name: Optional[str]
    file_size: Optional[int]
    reply_to_id: Optional[str]
    is_edited: bool
    status: str
    created_at: datetime
    sender: Optional[UserPublic] = None


class ConversationCreate(BaseModel):
    type: str = "direct"
    name: Optional[str] = None
    participant_ids: List[str]


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    name: Optional[str]
    avatar_url: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    archived_at: Optional[datetime]
    pinned_at: Optional[datetime]
    participants: List[UserPublic] = []
    last_message: Optional[MessageOut] = None
    unread_count: int = 0


class FriendRequestCreate(BaseModel):
    addressee_id: Optional[str] = None
    username: Optional[str] = None
    unique_share_id: Optional[str] = None


class FriendshipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    requester_id: str
    addressee_id: str
    status: str
    created_at: datetime
    requester: Optional[UserPublic] = None
    addressee: Optional[UserPublic] = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    type: str
    title: Optional[str]
    body: Optional[str]
    data: Optional[dict]
    is_read: bool
    created_at: datetime


class PaginatedMessages(BaseModel):
    items: List[MessageOut]
    next_cursor: Optional[str]
    has_more: bool
