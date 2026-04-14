from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.management.commands.data.permission_list import PERMISSION_LIST
from authentication.models import Section,Permission
from authentication.models import User
from authentication.models import Role
from authentication.models import RolePermission

def create_user():
    User.objects.create_superuser('inventory@admin.com', 'PS@2025#inventory')
    User.objects.create_superuser('rakib@admin.com', 'admin')
    print("Successfully created super users")

def create_permissions():
    for section in PERMISSION_LIST:
        section_obj, created = Section.objects.get_or_create(name=section['section_name'])
        if created:
            print(f"Section {section['section_name']} created")
        section_permissions = section['permissions']
        for permission in section_permissions:
            permission_obj, created = Permission.objects.get_or_create(name=permission['name'],code=permission['code'],description=permission['description'], section=section_obj)
            if created:
                print(f"Permission {permission['name']} created")
            else:
                print(f"Permission {permission['name']} already exists")

def create_super_admin_role():
    role, created = Role.objects.get_or_create(name='Super Admin')
    role_permission, created = RolePermission.objects.get_or_create(role=role)
    permissions = Permission.objects.all()
    role_permission.permissions.set(permissions)
    role_permission.save()
    role.save()
    print("Successfully created super admin role")

def add_admin_permissions():
    user = User.objects.get(email='inventory@admin.com')
    role = Role.objects.get(name='Super Admin')
    user.role.add(role)
    user.save()
    print("Successfully added admin permissions")
                    


class Command(BaseCommand):
    help = 'Initial application configuration'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                create_user()
                create_permissions()
                create_super_admin_role()
                add_admin_permissions()
                print("Initial setup completed")
        except Exception as e:
            print(f"Error: {e}")
            transaction.set_rollback(True)
            raise e

