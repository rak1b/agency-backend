"""
WSGI config for entrepreneur project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os
from decouple import config
from django.core.wsgi import get_wsgi_application

IS_LIVE = config('IS_LIVE', default=False, cast=bool)
print(f"FROM WSGI.PY IS_LIVE: {IS_LIVE} Type: {type(IS_LIVE)}")
if IS_LIVE:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings.production')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings.development')

application = get_wsgi_application()
