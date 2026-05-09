from .base import *
from .db_utils import redis_url_local_fallback, resolved_tcp_host

DEBUG = config('DEBUG', cast=bool)
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "agency-backend.devsstream.com",
    "agency-demo-backend.devsstream.com",
    "agency.devsstream.com",
    ".traefik.me",
]
_extra_hosts = [h.strip() for h in config("EXTRA_ALLOWED_HOSTS", default="").split(",") if h.strip()]
if _extra_hosts:
    ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, *_extra_hosts]))

# settings.py
CSRF_TRUSTED_ORIGINS = [
    "https://inventory-backend.paymentsave.co.uk",   # backend (e.g., DRF docs, admin, etc.)
    "https://inventory.paymentsave.co.uk",
    "https://psinventory.devsstream.com",
    "https://inventory-demo-backend.devsstream.com",
    "https://ps-inventory-demo-backend.devsstream.com",
    "https://agency-backend.devsstream.com",
    "https://agency-demo-backend.devsstream.com",
    "http://agency-demo-backend.devsstream.com",
    "https://agency.devsstream.com",

    # Add specific Traefik origin (wildcards not supported in older Django)
    "https://psinventorybycompose-exmrlr-ad88ed-88-99-13-130.traefik.me",
]
_extra_csrf = [h.strip() for h in config("EXTRA_CSRF_TRUSTED_ORIGINS", default="").split(",") if h.strip()]
if _extra_csrf:
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([*CSRF_TRUSTED_ORIGINS, *_extra_csrf]))

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
            'HOST': resolved_tcp_host(config('DB_HOST')),
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
CELERY_BROKER_URL = redis_url_local_fallback(
    config('CELERY_BROKER_URL', default=_default_docker_redis)
)
CELERY_RESULT_BACKEND = redis_url_local_fallback(
    config('CELERY_RESULT_BACKEND', default=_default_docker_redis)
)

# Local: set CELERY_TASK_ALWAYS_EAGER=True when Redis is not running (works well with USE_SQLITE).
CELERY_TASK_ALWAYS_EAGER = config('CELERY_TASK_ALWAYS_EAGER', default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True
