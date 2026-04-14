import os
import glob
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Deletes all migration files except __init__.py, excluding the venv folder"

    def handle(self, *args, **options):
        base_dir = os.getcwd()
        deleted_files = 0

        for root, dirs, files in os.walk(base_dir):
            # Skip the virtual environment folder
            if "venv" in root.split(os.sep) or "env" in root.split(os.sep):
                continue

            if "migrations" in root.split(os.sep):
                migration_files = glob.glob(os.path.join(root, "*.py"))
                for file in migration_files:
                    if not file.endswith("__init__.py"):
                        os.remove(file)
                        deleted_files += 1

                # Remove .pyc files
                pyc_files = glob.glob(os.path.join(root, "*.pyc"))
                for pyc in pyc_files:
                    os.remove(pyc)
                    deleted_files += 1

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_files} migration files."))
