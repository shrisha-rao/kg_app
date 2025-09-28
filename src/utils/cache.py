# # src/utils/cache.py
# import redis
# import json
# from src.config import settings

# def get_cache_client():
#     """Get a Redis cache client"""
#     return redis.Redis(host=settings.redis_host,
#                        port=settings.redis_port,
#                        decode_responses=True)

# src/utils/cache.py
from redis.asyncio import Redis
import json
from src.config import settings


def get_cache_client() -> Redis:
    """Get an async Redis client"""
    return Redis(host=settings.redis_host,
                 port=settings.redis_port,
                 decode_responses=True)
