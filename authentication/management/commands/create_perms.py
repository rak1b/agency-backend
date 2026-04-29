from django.core.management.base import BaseCommand
from django.db import transaction
from authentication.management.commands.data.permission_list import PERMISSION_LIST
from authentication.models import Section,Permission
from authentication.models import User
from authentication.models import Role
from authentication.models import RolePermission


def create_permissions():
    for section_data in PERMISSION_LIST:
        section_name = section_data["section_name"]
        section_obj, section_created = Section.objects.get_or_create(name=section_name)
        if section_created:
            print(f"Section {section_name} created")

        section_permissions = section_data["permissions"]
        for permission_data in section_permissions:
            # Use stable identity fields for lookup, and only apply others on create.
            _, permission_created = Permission.objects.get_or_create(
                section=section_obj,
                code=permission_data["code"],
                defaults={
                    "name": permission_data["name"],
                    "description": permission_data["description"],
                },
            )
            if permission_created:
                print(f"Permission {permission_data['name']} created")
            else:
                print(f"Permission {permission_data['name']} already exists")
def delete_permissions():
    # Hard-delete permissions first, then sections, to avoid orphaned references.
    total_deleted_permissions = 0
    total_deleted_sections = 0

    permission_records = Permission.all_objects.select_related("section").all()
    for permission_record in permission_records:
        permission_name = permission_record.name
        permission_record.hard_delete()
        total_deleted_permissions += 1
        print(f"Permission {permission_name} permanently deleted")

    section_records = Section.all_objects.all()
    for section_record in section_records:
        section_name = section_record.name
        section_record.hard_delete()
        total_deleted_sections += 1
        print(f"Section {section_name} permanently deleted")

    print(
        f"Permanent deletion completed: "
        f"{total_deleted_permissions} permissions, {total_deleted_sections} sections."
    )

def create_super_admin_role():
    role, created = Role.objects.get_or_create(name='Super Admin')
    role_permission, created = RolePermission.objects.get_or_create(role=role)
    permissions = Permission.objects.all()
    role_permission.permissions.set(permissions)
    role_permission.save()
    role.save()
    print("Super admin role created successfully")
class Command(BaseCommand):
    help = 'Create permissions'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                # delete_permissions()
                create_permissions()
                # create_super_admin_role()
                print("Permissions permanently deleted successfully")
        except Exception as e:
            print(f"Error: {e}")
            transaction.set_rollback(True)
            raise e

