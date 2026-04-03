from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp,
)
from app.core.redis import get_redis, RedisKeys
from app.repositories.user_repo import UserRepository
from app.schemas.user import (
    UserRegister,
    UserLogin,
    OTPRequest,
    OTPVerify,
    TokenRefresh,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)

    if await repo.get_by_email(data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await repo.get_by_username(data.username):
        raise HTTPException(status_code=400, detail="Username already taken")

    user = await repo.create(
        username=data.username,
        email=data.email,
        password=data.password,
        display_name=data.display_name,
    )

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})

    # Store refresh token in Redis
    redis = await get_redis()
    await redis.setex(RedisKeys.refresh_token(refresh_token), 30 * 86400, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    user = await repo.get_by_email(data.email)

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})

    redis = await get_redis()
    await redis.setex(RedisKeys.refresh_token(refresh_token), 30 * 86400, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(data: TokenRefresh, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    redis = await get_redis()
    user_id = await redis.get(RedisKeys.refresh_token(data.refresh_token))
    if not user_id:
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate tokens
    await redis.delete(RedisKeys.refresh_token(data.refresh_token))
    new_access = create_access_token({"sub": user.id})
    new_refresh = create_refresh_token({"sub": user.id})
    await redis.setex(RedisKeys.refresh_token(new_refresh), 30 * 86400, user.id)

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=UserOut.model_validate(user),
    )


@router.post("/logout")
async def logout(
    data: TokenRefresh,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    redis = await get_redis()
    await redis.delete(RedisKeys.refresh_token(data.refresh_token))
    return {"message": "Logged out successfully"}


@router.post("/otp/request")
async def request_otp(data: OTPRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    otp = generate_otp()
    redis = await get_redis()
    await redis.setex(RedisKeys.otp(data.email), 600, otp)  # 10 min expiry

    # In production, send actual email. For dev, return OTP in response
    return {"message": "OTP sent to email", "dev_otp": otp}


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(data: OTPVerify, db: AsyncSession = Depends(get_db)):
    redis = await get_redis()
    stored_otp = await redis.get(RedisKeys.otp(data.email))

    if not stored_otp or stored_otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    await redis.delete(RedisKeys.otp(data.email))

    repo = UserRepository(db)
    user = await repo.get_by_email(data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token({"sub": user.id})
    await redis.setex(RedisKeys.refresh_token(refresh_token), 30 * 86400, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )
