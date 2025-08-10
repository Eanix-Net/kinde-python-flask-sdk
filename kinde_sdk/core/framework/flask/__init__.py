from .framework.flask_framework import FlaskFramework
from kinde_sdk.core.framework.framework_factory import FrameworkFactory
from kinde_sdk.core.storage.storage_factory import StorageFactory
# from .storage.flask_storage_factory import FlaskStorageFactory  # Deprecated: Use RedisStorage directly

# Register the Flask framework (kept for backward compatibility if needed)
FrameworkFactory.register_framework("flask", FlaskFramework)
# StorageFactory.register_framework_factory("flask", FlaskStorageFactory)  # Deprecated: Use RedisStorage directly

__all__ = ['FlaskFramework'] 