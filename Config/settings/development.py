"""
Local development when ``IS_LIVE=false`` (see ``manage.py`` / ``Config.wsgi``).

**Always SQLite** + local Redis so a laptop works without PostgreSQL, even if ``.env``
still contains ``DB_*`` values copied from Dokploy.

**Live and demo** (Postgres, Redis, TLS, etc.): set ``IS_LIVE=true`` so Django loads
``Config.settings.production`` — same stack for production and Docker/Dokploy demo.
"""

from decouple import config

from .base import *

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
