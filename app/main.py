from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import socketio
import os

from app.core.config import settings
from app.core.database import create_tables
from app.core.redis import get_redis, close_redis
from app.api.router import api_router
from app.socket.manager import sio

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="PulseChat API",
    description="Real-time chat application API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router)

# Static file serving for uploads
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.on_event("startup")
async def startup():
    await create_tables()
    await get_redis()
    print("✅ PulseChat API started")


@app.on_event("shutdown")
async def shutdown():
    await close_redis()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pulsechat-api"}


# Mount Socket.IO as ASGI sub-application
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)
