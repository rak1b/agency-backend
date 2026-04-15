import socket
from urllib.parse import urlparse, urlunparse

from .base import *


def _resolved_tcp_host(hostname: str, *, fallback: str = '127.0.0.1') -> str:
    """
    Docker / Dokploy use service hostnames like 'db'. On a normal PC those names do not
    resolve unless Docker DNS is in play. Fall back to localhost so the same .env works
    when Postgres / Redis are published on the host loopback.
    """
    if not hostname:
        return fallback
    lowered = hostname.lower()
    if lowered in ('localhost', '127.0.0.1', '::1'):
        return hostname
    try:
        socket.gethostbyname(hostname)
    except OSError:
        return fallback
    return hostname


def _redis_url_local_fallback(url: str, *, fallback_host: str = '127.0.0.1') -> str:
    """Same idea as _resolved_tcp_host, but for redis:// URLs (including password in netloc)."""
    parsed = urlparse(url)
    if not parsed.hostname:
        return url
    try:
        socket.gethostbyname(parsed.hostname)
        return url
    except OSError:
        port = parsed.port or 6379
        netloc = parsed.netloc
        if '@' in netloc:
            userinfo, _, _hostport = netloc.rpartition('@')
            new_netloc = f'{userinfo}@{fallback_host}:{port}'
        else:
            new_netloc = f'{fallback_host}:{port}'
        return urlunparse((parsed.scheme, new_netloc, parsed.path, '', parsed.query, parsed.fragment))


DEBUG = config('DEBUG', cast=bool)
ALLOWED_HOSTS = [
    "agency-backend.devsstream.com",
    "agency.devsstream.com",
    ".traefik.me",
]

# settings.py
CSRF_TRUSTED_ORIGINS = [
    "https://inventory-backend.paymentsave.co.uk",   # backend (e.g., DRF docs, admin, etc.)
    "https://inventory.paymentsave.co.uk",
    "https://psinventory.devsstream.com",
    "https://inventory-demo-backend.devsstream.com",
    "https://ps-inventory-demo-backend.devsstream.com",
    "https://agency-backend.devsstream.com",
    "https://agency.devsstream.com",

    # Add specific Traefik origin (wildcards not supported in older Django)
    "https://psinventorybycompose-exmrlr-ad88ed-88-99-13-130.traefik.me",
]

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
#
# USE_SQLITE=True in .env: file-backed SQLite (handy on a laptop with IS_LIVE=True).
# Omit or False on Dokploy / production so PostgreSQL is used.
USE_SQLITE = config('USE_SQLITE', default=False, cast=bool)

if USE_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': _resolved_tcp_host(config('DB_HOST')),
            'PORT': config('DB_PORT', default=5432, cast=int),
        }
    }



# Cache (Cache settings)
# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": "redis://127.0.0.1:6379/1",
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#         }
#     }
# }

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
# https://docs.djangoproject.com/en/3.0/howto/static-files/
STATIC_URL = '/static/'
# STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  # this points to /app/static
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # this is where collectstatic copies files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Dokploy / Compose: set CELERY_BROKER_URL to redis://redis:6379/0 (or rely on default below).
_default_docker_redis = 'redis://redis:6379/0'
CELERY_BROKER_URL = _redis_url_local_fallback(
    config('CELERY_BROKER_URL', default=_default_docker_redis)
)
CELERY_RESULT_BACKEND = _redis_url_local_fallback(
    config('CELERY_RESULT_BACKEND', default=_default_docker_redis)
)

# Local: set CELERY_TASK_ALWAYS_EAGER=True when Redis is not running (works well with USE_SQLITE).
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True