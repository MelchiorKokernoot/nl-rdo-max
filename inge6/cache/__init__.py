from typing import Optional

from redis import StrictRedis
from ..config import settings

# pylint: disable=global-statement
_REDIS_CLIENT: Optional[StrictRedis] = None

def get_redis_client() -> StrictRedis:
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        use_ssl = settings.redis.ssl.lower() == 'true'

        if use_ssl:
            _REDIS_CLIENT = StrictRedis(
                                host=settings.redis.host, port=settings.redis.port, db=0,
                                ssl=True,
                                ssl_keyfile=settings.redis.key, ssl_certfile=settings.redis.cert,
                                ssl_ca_certs=settings.redis.cafile
                            )
        else:
            _REDIS_CLIENT = StrictRedis(host=settings.redis.host, port=settings.redis.port, db=0)

    return _REDIS_CLIENT
