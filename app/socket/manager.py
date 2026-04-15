"""
Socket.IO server with Redis pub/sub for horizontal scaling.
Handles: messaging, typing, read receipts, WebRTC signaling, calls.
"""
import socketio
import json
from datetime import datetime, timezone

from app.core.config import settings
from app.core.redis import get_redis, RedisKeys
from app.core.security import decode_token
from app.core.database import AsyncSessionLocal
from app.repositories.user_repo import UserRepository
from app.repositories.message_repo import MessageRepository, ConversationRepository
from app.models.notification import Notification

# Redis-backed message queue for pub/sub scaling
mgr = socketio.AsyncRedisManager(settings.REDIS_URL)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    client_manager=mgr,
    logger=False,
    engineio_logger=False,
)

# Track socket_id -> user_id mapping (local instance)
socket_user_map: dict[str, str] = {}


async def authenticate_socket(token: str) -> str | None:
    """Validate JWT and return user_id"""
    payload = decode_token(token)
    if payload and payload.get("type") == "access":
        return payload.get("sub")
    return None


@sio.event
async def connect(sid, environ, auth):
    token = (auth or {}).get("token") or ""
    if not token:
        # Try query params
        query = environ.get("QUERY_STRING", "")
        for part in query.split("&"):
            if part.startswith("token="):
                token = part[6:]

    user_id = await authenticate_socket(token)
    if not user_id:
        raise ConnectionRefusedError("Authentication failed")

    socket_user_map[sid] = user_id
    redis = await get_redis()
    await redis.set(RedisKeys.user_socket(user_id), sid, ex=86400)
    await redis.set(RedisKeys.user_status(user_id), "online")

    # Update DB status
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        if user:
            user.status = "online"
            await db.commit()

    # Notify friends of online status
    await sio.emit("user_status_changed", {"user_id": user_id, "status": "online"})
    print(f"[Socket] User {user_id} connected ({sid})")


@sio.event
async def disconnect(sid):
    user_id = socket_user_map.pop(sid, None)
    if not user_id:
        return

    redis = await get_redis()
    await redis.delete(RedisKeys.user_socket(user_id))
    await redis.set(RedisKeys.user_status(user_id), "offline")

    # Update DB
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)
        user = await repo.get_by_id(user_id)
        if user:
            user.status = "offline"
            user.last_seen = datetime.now(timezone.utc)
            await db.commit()

    await sio.emit("user_status_changed", {"user_id": user_id, "status": "offline"})
    print(f"[Socket] User {user_id} disconnected")


@sio.event
async def join_room(sid, data):
    """Join a conversation room"""
    conv_id = data.get("conversation_id")
    if conv_id:
        await sio.enter_room(sid, f"conv_{conv_id}")


@sio.event
async def leave_room(sid, data):
    conv_id = data.get("conversation_id")
    if conv_id:
        await sio.leave_room(sid, f"conv_{conv_id}")


@sio.event
async def send_message(sid, data):
    """Handle new message: save to DB and broadcast"""
    user_id = socket_user_map.get(sid)
    if not user_id:
        return

    conv_id = data.get("conversation_id")
    content = data.get("content")
    message_type = data.get("message_type", "text")
    reply_to_id = data.get("reply_to_id")
    file_url = data.get("file_url")
    file_name = data.get("file_name")
    file_size = data.get("file_size")

    async with AsyncSessionLocal() as db:
        # Verify user is participant
        conv_repo = ConversationRepository(db)
        conv = await conv_repo.get_by_id(conv_id, user_id=user_id)
        if not conv:
            await sio.emit("error", {"message": "Conversation not found"}, to=sid)
            return

        msg_repo = MessageRepository(db)
        msg = await msg_repo.create(
            conversation_id=conv_id,
            sender_id=user_id,
            content=content,
            message_type=message_type,
            reply_to_id=reply_to_id,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
        )

        recipient_ids = [p.user_id for p in conv.participants if p.user_id != user_id]
        sender_name = (
            msg.sender.display_name
            or msg.sender.username
            if msg.sender
            else "Someone"
        )

        preview_text = (
            content
            if content
            else ("Sent an image" if message_type == "image" else "Sent an attachment")
        )
        for recipient_id in recipient_ids:
            db.add(
                Notification(
                    user_id=recipient_id,
                    type="message",
                    title=f"New message from {sender_name}",
                    body=preview_text,
                    data={
                        "conversation_id": conv_id,
                        "sender_id": user_id,
                        "message_id": msg.id,
                        "message_type": message_type,
                    },
                )
            )

        await db.commit()

        msg_data = {
            "id": msg.id,
            "conversation_id": conv_id,
            "sender_id": user_id,
            "content": content,
            "message_type": message_type,
            "file_url": file_url,
            "file_name": file_name,
            "file_size": file_size,
            "reply_to_id": reply_to_id,
            "is_edited": False,
            "status": "sent",
            "created_at": msg.created_at.isoformat(),
            "sender": {
                "id": msg.sender.id,
                "username": msg.sender.username,
                "display_name": msg.sender.display_name,
                "avatar_url": msg.sender.avatar_url,
            } if msg.sender else None,
        }

    # Broadcast to room except sender (sender gets ack separately)
    await sio.emit("message_new", msg_data, room=f"conv_{conv_id}", skip_sid=sid)
    # Send ack to sender
    await sio.emit("message_sent", msg_data, to=sid)

    # Emit notification event to recipients
    redis = await get_redis()
    for recipient_id in recipient_ids:
        recipient_sid = await redis.get(RedisKeys.user_socket(recipient_id))
        if recipient_sid:
            await sio.emit(
                "notification_new",
                {
                    "type": "message",
                    "title": f"New message from {sender_name}",
                    "body": preview_text,
                    "data": {"conversation_id": conv_id, "sender_id": user_id},
                    "created_at": msg.created_at.isoformat(),
                },
                to=recipient_sid,
            )


@sio.event
async def typing_start(sid, data):
    user_id = socket_user_map.get(sid)
    conv_id = data.get("conversation_id")
    if user_id and conv_id:
        await sio.emit(
            "user_typing",
            {"user_id": user_id, "conversation_id": conv_id, "typing": True},
            room=f"conv_{conv_id}",
            skip_sid=sid,
        )


@sio.event
async def typing_stop(sid, data):
    user_id = socket_user_map.get(sid)
    conv_id = data.get("conversation_id")
    if user_id and conv_id:
        await sio.emit(
            "user_typing",
            {"user_id": user_id, "conversation_id": conv_id, "typing": False},
            room=f"conv_{conv_id}",
            skip_sid=sid,
        )


@sio.event
async def message_read(sid, data):
    user_id = socket_user_map.get(sid)
    message_ids = data.get("message_ids", [])
    conv_id = data.get("conversation_id")

    if not user_id or not message_ids:
        return

    async with AsyncSessionLocal() as db:
        msg_repo = MessageRepository(db)
        await msg_repo.mark_read(message_ids, user_id)
        await db.commit()

    await sio.emit(
        "message_read_by",
        {"user_id": user_id, "message_ids": message_ids, "conversation_id": conv_id},
        room=f"conv_{conv_id}",
        skip_sid=sid,
    )


# ── WebRTC Signaling ──────────────────────────────────────────────

@sio.event
async def call_initiate(sid, data):
    """Initiate a call to another user"""
    user_id = socket_user_map.get(sid)
    target_user_id = data.get("target_user_id")
    call_type = data.get("call_type", "video")  # video/audio

    if not user_id or not target_user_id:
        return

    redis = await get_redis()
    target_sid = await redis.get(RedisKeys.user_socket(target_user_id))

    if not target_sid:
        await sio.emit("call_failed", {"reason": "User offline"}, to=sid)
        return

    call_data = {
        "caller_id": user_id,
        "call_type": call_type,
        "conversation_id": data.get("conversation_id"),
    }
    await sio.emit("call_incoming", call_data, to=target_sid)
    await sio.emit("call_ringing", {"target_user_id": target_user_id}, to=sid)


@sio.event
async def call_accept(sid, data):
    user_id = socket_user_map.get(sid)
    caller_id = data.get("caller_id")

    redis = await get_redis()
    caller_sid = await redis.get(RedisKeys.user_socket(caller_id))
    if caller_sid:
        await sio.emit("call_accepted", {"accepter_id": user_id}, to=caller_sid)


@sio.event
async def call_reject(sid, data):
    user_id = socket_user_map.get(sid)
    caller_id = data.get("caller_id")

    redis = await get_redis()
    caller_sid = await redis.get(RedisKeys.user_socket(caller_id))
    if caller_sid:
        await sio.emit("call_rejected", {"rejector_id": user_id}, to=caller_sid)


@sio.event
async def call_end(sid, data):
    user_id = socket_user_map.get(sid)
    peer_id = data.get("peer_id")

    redis = await get_redis()
    peer_sid = await redis.get(RedisKeys.user_socket(peer_id))
    if peer_sid:
        await sio.emit("call_ended", {"ender_id": user_id}, to=peer_sid)


@sio.event
async def webrtc_offer(sid, data):
    """Relay WebRTC offer to target peer"""
    target_user_id = data.get("target_user_id")
    redis = await get_redis()
    target_sid = await redis.get(RedisKeys.user_socket(target_user_id))
    if target_sid:
        user_id = socket_user_map.get(sid)
        await sio.emit("webrtc_offer", {**data, "from_user_id": user_id}, to=target_sid)


@sio.event
async def webrtc_answer(sid, data):
    """Relay WebRTC answer to caller"""
    target_user_id = data.get("target_user_id")
    redis = await get_redis()
    target_sid = await redis.get(RedisKeys.user_socket(target_user_id))
    if target_sid:
        user_id = socket_user_map.get(sid)
        await sio.emit("webrtc_answer", {**data, "from_user_id": user_id}, to=target_sid)


@sio.event
async def webrtc_ice_candidate(sid, data):
    """Relay ICE candidate"""
    target_user_id = data.get("target_user_id")
    redis = await get_redis()
    target_sid = await redis.get(RedisKeys.user_socket(target_user_id))
    if target_sid:
        user_id = socket_user_map.get(sid)
        await sio.emit("webrtc_ice_candidate", {**data, "from_user_id": user_id}, to=target_sid)
