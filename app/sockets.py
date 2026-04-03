import asyncio
import json
from typing import Dict
from fastapi import WebSocket
import aioredis


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, user_id: int, message: str):
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_text(message)


class RedisGateway:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.pub: aioredis.Redis | None = None
        self.subs: Dict[str, aioredis.Redis] = {}

    async def connect(self):
        self.pub = await aioredis.from_url(self.redis_url)

    async def subscribe_user(self, user_id: int, callback):
        if not self.pub:
            await self.connect()
        channel = f"ws:recv:{user_id}"
        pubsub = self.pub.pubsub()
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message is None:
                continue
            if message[0].decode() == channel:
                data = message[1].decode()
                await callback(data)
