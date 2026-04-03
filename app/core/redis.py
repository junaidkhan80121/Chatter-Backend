import redis.asyncio as aioredis
from app.core.config import settings

redis_client: aioredis.Redis = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


class RedisKeys:
    @staticmethod
    def user_status(user_id: str) -> str:
        return f"user:status:{user_id}"

    @staticmethod
    def user_socket(user_id: str) -> str:
        return f"user:socket:{user_id}"

    @staticmethod
    def otp(email: str) -> str:
        return f"otp:{email}"

    @staticmethod
    def refresh_token(token: str) -> str:
        return f"refresh:{token}"

    @staticmethod
    def conversation_cache(conv_id: str) -> str:
        return f"conv:{conv_id}"

    @staticmethod
    def unread_count(user_id: str, conv_id: str) -> str:
        return f"unread:{user_id}:{conv_id}"
