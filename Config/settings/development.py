"""
Local development defaults.

**Dokploy demo (``dev`` branch, ``IS_LIVE=false``):** set ``DB_HOST`` (and DB_NAME / DB_USER /
DB_PASSWORD) like production. When ``DB_HOST`` is non-empty, this module uses PostgreSQL and
defaults Celery to ``redis://redis:6379/0`` so the same Compose/Dokploy stack as live works
without forcing ``IS_LIVE=true``.
"""

from decouple import config

from .base import *
from .db_utils import redis_url_local_fallback, resolved_tcp_host

DEBUG = True
ALLOWED_HOSTS = ["*", "inventory.payinpos.com"]

# Demo backend hostname (Dokploy); base.py CSRF list does not include every subdomain.
CSRF_TRUSTED_ORIGINS = list(
    dict.fromkeys(
        [
            *CSRF_TRUSTED_ORIGINS,
            "https://agency-demo-backend.devsstream.com",
            "http://agency-demo-backend.devsstream.com",
        ]
    )
)

_db_host = config("DB_HOST", default="").strip()

if _db_host:
    # Container / Dokploy: Postgres service (same contract as production when not on SQLite).
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": resolved_tcp_host(_db_host),
            "PORT": config("DB_PORT", default=5432, cast=int),
        }
    }
    _default_docker_redis = "redis://redis:6379/0"
    CELERY_BROKER_URL = redis_url_local_fallback(
        config("CELERY_BROKER_URL", default=_default_docker_redis)
    )
    CELERY_RESULT_BACKEND = redis_url_local_fallback(
        config("CELERY_RESULT_BACKEND", default=_default_docker_redis)
    )
else:
    # Laptop: file-backed SQLite, local Redis (or set CELERY_TASK_ALWAYS_EAGER=True).
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        }
    }
    CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
    CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/0"

CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
