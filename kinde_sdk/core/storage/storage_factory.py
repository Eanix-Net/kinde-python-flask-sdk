from typing import Dict, Any, Type, Optional
from .storage_interface import StorageInterface
from .redis_storage_factory import RedisStorageFactory
import logging

logger = logging.getLogger(__name__)

class StorageFactory:
    _framework_factories = {}
    
    @classmethod
    def register_framework_factory(cls, framework: str, factory_class: Type) -> None:
        """
        Register a framework-specific storage factory.
        
        Args:
            framework (str): The framework name (e.g., 'flask')
            factory_class (Type): The storage factory class for the framework
        """
        logger.info(f"Registering storage factory: {framework}")
        cls._framework_factories[framework] = factory_class
    
    @classmethod
    def create_storage(cls, config: Optional[Dict[str, Any]] = None) -> StorageInterface:
        """
        Create a storage backend based on the provided configuration.
        RedisStorage is now the primary backend, with fallbacks to memory/local storage.

        Args:
            config (Optional[Dict[str, Any]]): Configuration dictionary containing storage settings.

        Returns:
            StorageInterface: An instance of the requested storage backend.
        """
        config = config or {}
        storage_type = config.get("type")
        
        # If a specific storage type is requested, use that
        if storage_type:
            logger.info(f"Storage type requested: {storage_type}")
            
            # Primary: RedisStorage (framework-agnostic)
            if storage_type == "redis":
                return RedisStorageFactory.create_storage(config)
                
            
            # Legacy framework-specific types (check first for backward compatibility)
            elif storage_type in cls._framework_factories:
                try:
                    factory_class = cls._framework_factories[storage_type]
                    logger.info(f"Using legacy framework factory for {storage_type}")
                    return factory_class.create_storage(config)
                except Exception as e:
                    logger.warning(f"Failed to create {storage_type} storage, falling back to Redis: {str(e)}")
                    return RedisStorageFactory.create_storage(config)
            else:
                logger.warning(f"Unsupported storage type: {storage_type}, trying Redis as fallback")
                return RedisStorageFactory.create_storage(config)
        
        # Default: Try RedisStorage first, fallback to memory
        logger.info("No storage type specified; trying Redis as primary, fallback to memory")
        try:
            return RedisStorageFactory.create_storage(config)
        except Exception as e:
            logger.info(f"Redis not available, using memory storage: {str(e)}")
            return MemoryStorage()