"""
Redis 缓存模块 — Redis Cache Layer

提供基于 Redis 的异步缓存操作，用于存储和检索占卜结果。
如果 Redis 不可用，所有操作均优雅降级返回 None/False。
"""

import json

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.config import settings
from app.debug import log

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    """获取 Redis 连接（惰性初始化）。

    如果 Redis 不可用，返回 None。不会抛出异常。
    """
    global _redis
    if _redis is None:
        log(50, "get_redis: initializing new connection")
        try:
            _redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await _redis.ping()
            log(51, "get_redis: connection OK")
        except (RedisError, ConnectionError, OSError) as e:
            _redis = None
            log(52, f"get_redis: connection failed, graceful degradation", level="WARN", error=e)
    return _redis


async def cache_set(key: str, value: dict, ttl: int = 3600) -> bool:
    """Set a dict in Redis cache. Returns True if successful."""
    log(53, f"cache_set: start key='{key}', ttl={ttl}")
    r = await get_redis()
    if r is None:
        log(54, f"cache_set: redis unavailable, skip key='{key}'", level="WARN")
        return False
    try:
        await r.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
        log(55, f"cache_set: OK key='{key}'")
        return True
    except (RedisError, ConnectionError) as e:
        log(56, f"cache_set: failed key='{key}'", level="ERROR", error=e)
        return False


async def cache_get(key: str) -> dict | None:
    """Get a dict from Redis cache. Returns None if not found or unavailable."""
    log(57, f"cache_get: start key='{key}'")
    r = await get_redis()
    if r is None:
        log(58, f"cache_get: redis unavailable key='{key}'", level="WARN")
        return None
    try:
        data = await r.get(key)
        if data:
            log(59, f"cache_get: hit key='{key}'")
            return json.loads(data)
        log(60, f"cache_get: miss key='{key}'")
        return None
    except (RedisError, ConnectionError) as e:
        log(61, f"cache_get: failed key='{key}'", level="ERROR", error=e)
        return None


async def cache_delete(key: str) -> bool:
    """Delete a key from Redis cache. Returns True if successful."""
    log(62, f"cache_delete: start key='{key}'")
    r = await get_redis()
    if r is None:
        log(63, f"cache_delete: redis unavailable key='{key}'", level="WARN")
        return False
    try:
        await r.delete(key)
        log(64, f"cache_delete: OK key='{key}'")
        return True
    except (RedisError, ConnectionError) as e:
        log(65, f"cache_delete: failed key='{key}'", level="ERROR", error=e)
        return False


async def close_redis() -> None:
    """Close the Redis connection gracefully."""
    global _redis
    if _redis is not None:
        log(66, "close_redis: closing connection")
        try:
            await _redis.close()
            log(67, "close_redis: connection closed OK")
        except (RedisError, ConnectionError) as e:
            log(68, "close_redis: error during close", level="WARN", error=e)
        finally:
            _redis = None
    else:
        log(69, "close_redis: no connection to close")
