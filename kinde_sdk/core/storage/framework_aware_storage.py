from typing import Dict, Optional
from .storage_interface import StorageInterface
import logging
import os
import json
from urllib.parse import urlparse

# Optional import to avoid hard dependency at import-time in non-redis envs
try:  # pragma: no cover - exercised in runtime environments with redis installed
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore


class FrameworkAwareStorage(StorageInterface):
    """
    Redis-backed storage implementation that is framework-agnostic.

    Persists data in Redis. Applies TTL for short-lived OAuth artifacts
    like state, nonce, and code_verifier. Performs atomic pop for state
    to prevent replay.
    """

    def __init__(self, redis_url: Optional[str] = None, state_ttl_seconds: Optional[int] = None):
        self._logger = logging.getLogger(__name__)

        if redis is None:
            raise RuntimeError("redis package is required for FrameworkAwareStorage")

        self._redis_url = (
            redis_url
            or os.getenv("KINDE_REDIS_URL")
            or "redis://redis:6379/2"
        )
        self._state_ttl = state_ttl_seconds or int(os.getenv("KINDE_STATE_TTL", "600"))

        parsed_url = urlparse(self._redis_url)
        host = parsed_url.hostname or "redis"
        port = int(parsed_url.port or 6379)
        db_path = (parsed_url.path or "/2").lstrip("/")
        db = int(db_path) if db_path else 2

        self._client = redis.StrictRedis(host=host, port=port, db=db)

    def _is_state_like(self, key: str) -> bool:
        lowered = key.lower()
        return (
            lowered.endswith(":state")
            or lowered.endswith(":nonce")
            or lowered.endswith(":code_verifier")
            or lowered.endswith("state")
        )

    def get(self, key: str) -> Optional[Dict]:
        try:
            # Atomic pop for state to prevent replay
            if key.lower().endswith(":state") or key.lower().endswith("state"):
                pipe = self._client.pipeline()
                pipe.get(key)
                pipe.delete(key)
                value, _ = pipe.execute()
                if not value:
                    return None
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                return json.loads(value)

            raw = self._client.get(key)
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception as ex:
            self._logger.warning(f"Redis get failed for key '{key}': {ex}")
            return None

    def set(self, key: str, value: Dict) -> None:
        try:
            data = json.dumps(value)
            if self._is_state_like(key) and self._state_ttl > 0:
                self._client.setex(key, self._state_ttl, data)
            else:
                self._client.set(key, data)
        except Exception as ex:
            self._logger.warning(f"Redis set failed for key '{key}': {ex}")

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception as ex:
            self._logger.warning(f"Redis delete failed for key '{key}': {ex}")

    def set_flat(self, value: str) -> None:
        try:
            # Flat channel for opaque values if needed by callers
            self._client.set("kinde:core:flat_data", value)
        except Exception as ex:
            self._logger.warning(f"Redis set_flat failed: {ex}")