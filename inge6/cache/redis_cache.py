"""
Module contains all the commands regarding redis caching. Prepending prefixes, and defining Time To Live.

Required settings:
    - settings.redis.default_cache_namespace, prefix all redis cache keys.
    - settings.redis.object_ttl, time to live for all objects stored in cache
"""

from typing import Any, Text, Optional
import pickle

from . import get_redis_client
from .redis_debugger import RedisGetDebugger

from ..config import get_settings

class RedisCache:

    def __init__(self, settings = None):
        self.settings = get_settings() if settings is None else settings
        self.key_prefix: str = self.settings.redis.default_cache_namespace
        self.expires_in_s: int = int(self.settings.redis.object_ttl)
        self.redis_debugger = RedisGetDebugger(get_redis_client(), settings=settings)

    def _serialize(self, value: Any) -> bytes:
        """
        Function that specifies how the data should be serialized into the redis-server.

        :param value: Any value that should be storen in a redis database
        :returns: Serialized value, a pickle dump.
        """
        return pickle.dumps(value)

    def _deserialize(self, serialized_value: Optional[Any]) -> Any:
        """
        Specifies the opposite of the serialize function, expects the output of a redis GET command. And
        returns the deserialized version of that output.

        :param serialized_value: value retrieved from our redis-server connection
        :returns: deserialized version of the object stored in redis.
        """
        return pickle.loads(serialized_value) if serialized_value else None

    def _get_namespace(self, namespace: str) -> str:
        """
        As the server connecting to might be used by other clients, we need to specify a namespace for our keys. Such that
        there is no conflict of keys possible.

        :param namespace: The key that needs to be prefixed
        :returns: the namespaces key.
        """
        return f"{self.key_prefix}:{namespace}"

    # pylint: disable=redefined-builtin
    def set(self, key: str, value: Any) -> None:
        """
        Store a value in the redis database using the specified key.

        :param key: key used to link with the value
        :param value: value we want to store
        """
        key = self._get_namespace(key)
        serialized_value = self._serialize(value)

        if get_settings().redis.enable_debugger:
            # If in debugging mode, prepend namespace with key for better debugging.
            # It allows the redis debugger to search for specific key_types, and
            # redis db inspection shows better keys
            key = f'{key}:{key}'

        get_redis_client().set(key, serialized_value, ex=self.expires_in_s)

    # pylint: disable=redefined-builtin
    def get(self, key: str) -> Any:
        """
        Retrieve a value from the redis database using the specified key

        :param key: used to retrieve the stored value

        :returns: the value belonging to the specified key
        """
        key = self._get_namespace(key)
        value = get_redis_client().get(key)

        if get_settings().redis.enable_debugger and value :
            self.redis_debugger.debug_get(key, value)

        deserialized_value = self._deserialize(value)
        return deserialized_value

    def hset(self, namespace: str, key: str, value: Any) -> None:
        """
        Set a value in the redis database within a namespace. Rather than manually
        prefixing the key, use the internal redis namespace system
        to store keys without clashing with other clients.

        :param namespace: the namespace redis should use internally
        :param key: the key to store with your value
        :param value: the value to store in the redis database
        """
        serialized_value = self._serialize(value)
        namespace = self._get_namespace(namespace)

        if self.settings.redis.enable_debugger:
            # If in debugging mode, prepend namespace with key for better debugging.
            # It allows the redis debugger to search for specific key_types, and
            # redis db inspection shows better keys
            namespace = f'{namespace}:{key}'

        get_redis_client().hset(namespace, key, serialized_value)
        get_redis_client().expire(name=namespace, time=self.expires_in_s)

    def hget(self, namespace, key) -> Any:
        """
        Get a value from the redis database within a namespace. Rather than
        manually prefixing the key, use the internal redis namespace system
        to retrieve keys without clashing with other clients.
        """
        namespace = self._get_namespace(namespace)

        if self.settings.redis.enable_debugger:
            # If in debugging mode, namespace is prepended with the key for better debugging.
            # It allows the redis debugger to search for specific key_types, and
            # redis db inspection shows better keys
            namespace = f'{namespace}:{key}'
            value = get_redis_client().hget(namespace, key)
            self.redis_debugger.debug_get(namespace, value)
        else:
            value = get_redis_client().hget(namespace, key)

        deserialized_value = self._deserialize(value)
        return deserialized_value

    def gen_token(self) -> Text:
        """
        Generate a random string, useful to generate unique keys that should be stored in the redis database.
        """
        return get_redis_client().acl_genpass()

redis_cache = RedisCache()
