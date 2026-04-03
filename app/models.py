from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Table,
)
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

# Association table for friendships (simplified)
friendships = Table(
    "friendships",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("friend_id", Integer, ForeignKey("users.id")),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(128), nullable=False)
    avatar_url = Column(String(256), nullable=True)
    status = Column(String(20), default="offline")
    online = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships (simplified)
    friends = relationship(
        "User",
        secondary=friendships,
        primaryjoin=id == friendships.c.user_id,
        secondaryjoin=id == friendships.c.friend_id,
        backref="friend_of",
    )


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    is_group = Column(Boolean, default=False)
    title = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="sent")  # sent/delivered/read

    conversation = relationship("Conversation", backref="messages")
    sender = relationship("User")


class BlockedUser(Base):
    __tablename__ = "blocked_users"
    id = Column(Integer, primary_key=True, index=True)
    blocker_id = Column(Integer, ForeignKey("users.id"))
    blocked_id = Column(Integer, ForeignKey("users.id"))


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String(256))
    read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
