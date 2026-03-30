import json
import redis
from dotenv import load_dotenv
import os

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "rag_agent")
REDIS_CACHE_TTL_SECONDS = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "300"))

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
except Exception:
    redis_client = None


class Cache:
    def __init__(self):
        self.client = redis_client
        self.ttl = REDIS_CACHE_TTL_SECONDS
        self.prefix = REDIS_KEY_PREFIX

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> str | None:
        if not self.client:
            return None
        try:
            return self.client.get(self._key(key))
        except Exception:
            return None

    def get_json(self, key: str) -> any:
        if not self.client:
            return None
        try:
            val = self.client.get(self._key(key))
            if val is None:
                return None
            return json.loads(val)
        except Exception:
            return None

    def set(self, key: str, value: str, ttl: int = None):
        if not self.client:
            return
        try:
            self.client.setex(self._key(key), ttl or self.ttl, value)
        except Exception:
            pass

    def set_json(self, key: str, value: any, ttl: int = None):
        if not self.client:
            return
        try:
            self.client.setex(self._key(key), ttl or self.ttl, json.dumps(value, ensure_ascii=False))
        except Exception:
            pass

    def delete(self, key: str):
        if not self.client:
            return
        try:
            self.client.delete(self._key(key))
        except Exception:
            pass

    def exists(self, key: str) -> bool:
        if not self.client:
            return False
        try:
            return bool(self.client.exists(self._key(key)))
        except Exception:
            return False


cache = Cache()
