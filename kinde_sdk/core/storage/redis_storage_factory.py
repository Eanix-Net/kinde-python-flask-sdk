from typing import Optional, Dict, Any
from .storage_interface import StorageInterface
from .redis_storage import RedisStorage
import logging
import os
logger = logging.getLogger(__name__)


class RedisStorageFactory:
    """
    Factory for creating RedisStorage instances without framework dependencies.
    This replaces framework-specific storage factories.
    """
    
    @staticmethod
    def create_storage(config: Optional[Dict[str, Any]] = None) -> RedisStorage:
        """
        Create a RedisStorage instance.
        
        Args:
            config (Optional[Dict[str, Any]]): Configuration options.
                Supported options:
                  - redis_url: Redis connection URL (fallback KINDE_REDIS_URL env)
                  - state_ttl_seconds: TTL for state/nonce/code_verifier (fallback KINDE_STATE_TTL env)
                  - options.redis_url: Alternative way to specify redis_url
                  - options.state_ttl_seconds: Alternative way to specify state_ttl_seconds
                
        Returns:
            RedisStorage: A RedisStorage instance.
        """
        config = config or {}
        
        # Support both direct config and nested options for compatibility
        if isinstance(config, dict):
            options = config.get("options", {})
            redis_url = config.get("redis_url") or options.get("redis_url") or os.getenv("KINDE_REDIS_URL") or "redis://redis:6379/0"
            state_ttl_seconds = config.get("state_ttl_seconds") or options.get("state_ttl_seconds")
        else:
            redis_url = None
            state_ttl_seconds = None
            
        logger.info(f"Creating RedisStorage with redis_url={redis_url}, state_ttl_seconds={state_ttl_seconds}")
        return RedisStorage(redis_url=redis_url, state_ttl_seconds=state_ttl_seconds)


# Convenience alias for backward compatibility
RedisFactory = RedisStorageFactory
