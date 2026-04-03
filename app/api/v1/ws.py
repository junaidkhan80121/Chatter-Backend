from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt
from ..config import settings

router = APIRouter()
ALGORITHM = "HS256"
SECRET_KEY = settings.SECRET_KEY


class ConnectionManager:
    def __init__(self):
        self.active: dict[int, WebSocket] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active[user_id] = ws

    def disconnect(self, user_id: int):
        self.active.pop(user_id, None)

    async def send(self, user_id: int, data: str):
        ws = self.active.get(user_id)
        if ws:
            await ws.send_text(data)


manager = ConnectionManager()


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except Exception:
        return None


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = None):
    user_id = decode_token(token) if token else None
    if not user_id:
        await ws.close(code=1008)
        return
    await manager.connect(user_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            # Simple pass-through: expect JSON with recipient_id and message
            try:
                import json as _json

                payload = _json.loads(data)
                recipient = payload.get("recipient_id")
                message = payload.get("content")
                if recipient and message:
                    await manager.send(
                        int(recipient),
                        _json.dumps({"from": user_id, "content": message}),
                    )
            except Exception:
                continue
    except WebSocketDisconnect:
        manager.disconnect(user_id)
