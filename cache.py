import redis
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def build_cache_key(company: str, role: str) -> str:
    return f"lookup:{company.lower()}:{role.lower()}"


def get_cached_result(company: str, role: str):
    key = build_cache_key(company, role)
    try:
        data = redis_client.get(key)
    except Exception:
        # Fail-soft if Redis is unavailable
        return None
    if not data:
        return None

    try:
        result = json.loads(data)
    except Exception:
        return None

    if isinstance(result, dict):
        # Mark responses served from cache
        result["cache"] = True
    return result


def set_cached_result(company: str, role: str, result: dict, ttl: int = 86400):
    """
    Store successful lookup results in Redis.

    - Skips caching error payloads.
    - Strips any existing 'cache' flag; that field is added dynamically
      when reading from the cache.
    - ttl default = 24 hours.
    """
    if not isinstance(result, dict):
        return

    # Do not cache error responses
    if result.get("error"):
        return

    # Only cache when we actually have a resolved person
    first = result.get("first_name")
    last = result.get("last_name")
    if not first or not last:
        return

    key = build_cache_key(company, role)
    to_store = dict(result)
    to_store.pop("cache", None)
    try:
        redis_client.setex(key, ttl, json.dumps(to_store))
    except Exception:
        # Ignore cache write failures so lookups still succeed
        return