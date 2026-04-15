#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from decouple import config

def main():
    # Default False so a fresh clone without IS_LIVE uses development settings (matches wsgi/celery).
    IS_LIVE = config('IS_LIVE', default=False, cast=bool)
    if IS_LIVE:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings.production')
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
