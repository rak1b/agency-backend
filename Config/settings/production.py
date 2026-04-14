from .base import *

DEBUG = config('DEBUG', cast=bool)
ALLOWED_HOSTS = [
    "inventory-backend.paymentsave.co.uk",
    "inventory.paymentsave.co.uk",
    "psinventory.devsstream.com",
    "ps-inventory-demo-backend.devsstream.com",
    "localhost",
    "127.0.0.1",
    ".traefik.me",
    "psinventorybycompose-exmrlr-ad88ed-88-99-13-130.traefik.me",
]

# settings.py
CSRF_TRUSTED_ORIGINS = [
    "https://inventory-backend.paymentsave.co.uk",   # backend (e.g., DRF docs, admin, etc.)
    "https://inventory.paymentsave.co.uk",
    "https://psinventory.devsstream.com",
    "https://inventory-demo-backend.devsstream.com",
    "https://ps-inventory-demo-backend.devsstream.com",

    # Add specific Traefik origin (wildcards not supported in older Django)
    "https://psinventorybycompose-exmrlr-ad88ed-88-99-13-130.traefik.me",
]

# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
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


CELERY_BROKER_URL = "redis://redis:6379/0"  # 'redis' matches docker service name
CELERY_RESULT_BACKEND = "redis://redis:6379/0"