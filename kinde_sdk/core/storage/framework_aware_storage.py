from typing import Dict, Optional
from .storage_interface import StorageInterface
import logging
import os
import json
from urllib.parse import urlparse
import base64

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
        self._logger = logging.getLogger("redis")
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("redis").setLevel(logging.DEBUG)
        logging.config.fileConfig("logging.conf")

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
        self._logger.info(f"Redis client initialized for host '{host}', port '{port}', db '{db}'")

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
            self._logger.info(f"Redis get successful for key '{key}' value '{raw}'")
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
            self._logger.info(f"Redis set successful for key '{key}'")
        except Exception as ex:
            self._logger.warning(f"Redis set failed for key '{key}': {ex}")

    def cookie_set(self, key: str, value: Dict) -> None:
        try:
            # Encode dict as JSON then base64 for cookie-safe value
            json_str = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
            encoded = base64.b64encode(json_str.encode("utf-8")).decode("ascii")

            # Attach to current framework request for middleware to set on response
            try:
                from kinde_sdk.core.framework.framework_context import FrameworkContext
                request = FrameworkContext.get_request()
                if request is not None:
                    if not hasattr(request, "_kinde_cookies_to_set") or getattr(request, "_kinde_cookies_to_set") is None:
                        setattr(request, "_kinde_cookies_to_set", {})
                    request._kinde_cookies_to_set[key] = encoded
                else:
                    self._logger.debug("cookie_set called with no active request context; skipping attach to response")
            except Exception as inner_ex:
                self._logger.warning(f"cookie_set could not attach cookie to request: {inner_ex}")
        except Exception as ex:
            self._logger.warning(f"cookie_set failed for key '{key}': {ex}")
    
    def cookie_get(self, key: str) -> Dict:
        try:
            from kinde_sdk.core.framework.framework_context import FrameworkContext
            request = FrameworkContext.get_request()
            if request is None:
                return {}

            raw_val = None
            try:
                # Flask request has .cookies mapping
                raw_val = request.cookies.get(key)
            except Exception:
                raw_val = None

            if not raw_val:
                return {}

            # Decode base64 -> JSON -> dict
            # Add padding if stripped
            padding = "=" * (-len(raw_val) % 4)
            decoded_bytes = base64.b64decode(raw_val + padding)
            return json.loads(decoded_bytes.decode("utf-8"))
        except Exception as ex:
            self._logger.warning(f"cookie_get failed for key '{key}': {ex}")
            return {}

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