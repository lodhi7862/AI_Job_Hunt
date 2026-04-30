import json

import redis

from app.core.config import settings


class CacheService:
    def __init__(self) -> None:
        self.client = None
        try:
            self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            self.client = None

    def get_json(self, key: str) -> dict | None:
        if not self.client:
            return None
        try:
            value = self.client.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    def set_json(self, key: str, payload: dict, ttl_seconds: int = 120) -> None:
        if not self.client:
            return
        try:
            self.client.setex(key, ttl_seconds, json.dumps(payload))
        except Exception:
            return

    def delete(self, key: str) -> None:
        if not self.client:
            return
        try:
            self.client.delete(key)
        except Exception:
            return


cache_service = CacheService()
