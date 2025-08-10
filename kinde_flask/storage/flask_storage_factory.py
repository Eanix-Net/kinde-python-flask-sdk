from typing import Optional, Dict, Any
from kinde_sdk.core.storage.storage_factory import StorageFactory
from kinde_sdk.core.storage.storage_interface import StorageInterface
import logging
import os
import json
from urllib.parse import urlparse

# TODO: This is a hack to get the redis client to work with the redis container.
# We should use the redis client from the kinde_sdk package instead.
try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # Allow import-time in environments without redis installed

logger = logging.getLogger(__name__)

class FlaskStorage(StorageInterface):
    """
    Redis-backed storage for Flask integration.

    Keys are received already namespaced by `StorageManager` (e.g.,
    device:{device_id}:state). We store JSON values under the provided key
    and apply TTLs for short-lived OAuth artifacts like state/nonce.
    """

    def __init__(self, redis_url: Optional[str] = None, state_ttl_seconds: Optional[int] = None):
        if redis is None:
            raise RuntimeError("redis package is required for FlaskStorage")

        self._redis_url = redis_url or os.getenv("KINDE_REDIS_URL", "redis://redis:6379/0")
        self._state_ttl = state_ttl_seconds or int(os.getenv("KINDE_STATE_TTL", "600"))
        # Parse redis_url into host, port, and db:
        parsed_url = urlparse(self._redis_url)
        host = parsed_url.hostname
        port = int(parsed_url.port)
        db = int(parsed_url.path.lstrip("/"))
        self._client = redis.StrictRedis(host=host, port=port, db=db)

    def _should_apply_state_ttl(self, key: str) -> bool:
        lowered = key.lower()
        return lowered.endswith(":state") or lowered.endswith(":nonce") or lowered.endswith(":code_verifier") or lowered.endswith("state")

    def get(self, key: str) -> Optional[Dict]:
        try:
            # For state-like keys, do an atomic pop (get + delete) to prevent replay
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
            logger.warning(f"Redis get failed for key '{key}': {ex}")
            return None

    def set(self, key: str, value: Dict) -> None:
        try:
            data = json.dumps(value)
            if self._should_apply_state_ttl(key) and self._state_ttl > 0:
                self._client.setex(key, self._state_ttl, data)
            else:
                self._client.set(key, data)
        except Exception as ex:
            logger.warning(f"Redis set failed for key '{key}': {ex}")

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception as ex:
            logger.warning(f"Redis delete failed for key '{key}': {ex}")

    def set_flat(self, value: str) -> None:
        try:
            # Flat storage channel for opaque values like access tokens (if used)
            self._client.set("kinde:flask:flat_data", value)
        except Exception as ex:
            logger.warning(f"Redis set_flat failed: {ex}")

class FlaskStorageFactory(StorageFactory):
    """
    Factory for creating Flask-specific storage instances.
    """
    
    @staticmethod
    def create_storage(config: Optional[Dict[str, Any]] = None) -> FlaskStorage:
        """
        Create a Flask storage instance.
        
        Args:
            config (Optional[Dict[str, Any]]): Configuration options.
                Supported options:
                  - options.redis_url: Redis connection URL (fallback REDIS_URL env)
                  - options.state_ttl_seconds: TTL for state/nonce/code_verifier (fallback KINDE_STATE_TTL env)
                
        Returns:
            FlaskStorage: A Flask storage instance.
        """
        config = config or {}
        options = config.get("options", {}) if isinstance(config, dict) else {}
        redis_url = options.get("redis_url")
        state_ttl_seconds = options.get("state_ttl_seconds")
        return FlaskStorage(redis_url=redis_url, state_ttl_seconds=state_ttl_seconds)
