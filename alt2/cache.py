from flask_caching import Cache
from . import config

cache = Cache(config={
    'CACHE_TYPE': config.CACHE_TYPE,
    'CACHE_DEFAULT_TIMEOUT': config.CACHE_DEFAULT_TIMEOUT,
    'CACHE_REDIS_HOST': config.CACHE_REDIS_HOST
    })