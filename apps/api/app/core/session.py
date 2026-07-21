from typing import Any

import redis
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.core.config import settings

_serializer = URLSafeTimedSerializer(settings.app_secret_key)
_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def create_session_token(user_id: str, role: str | None = None) -> str:
    payload: dict[str, str] = {"user_id": user_id}
    if role:
        payload["role"] = role
    return _serializer.dumps(payload)


def decode_session_token(token: str) -> dict[str, Any] | None:
    try:
        data = _serializer.loads(token, max_age=settings.session_max_age_seconds)
        if isinstance(data, dict) and "user_id" in data:
            return data
    except BadSignature:
        return None
    return None


def check_login_rate_limit(client_ip: str, limit: int = 5, window_seconds: int = 60) -> bool:
    """Return True if request is allowed, False if rate limited."""
    try:
        r = get_redis()
        key = f"login_rate:{client_ip}"
        current = r.incr(key)
        if current == 1:
            r.expire(key, window_seconds)
        return current <= limit
    except redis.RedisError:
        # Fail open if Redis unavailable in dev
        return True


def ping_redis() -> bool:
    try:
        return get_redis().ping()
    except redis.RedisError:
        return False
