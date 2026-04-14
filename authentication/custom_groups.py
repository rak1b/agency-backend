from django.contrib.auth.models import Permission, Group
from .permissions import USER_PERMISSIONS
from .roles import SUPER_ADMIN, USER_ROLES


def get_admin_permissions():
    return Permission.objects.exclude(codename__icontains='delete')


def get_permission_meta(role):
    try:
        return USER_PERMISSIONS[role]
    except KeyError:
        return None


def get_user_permission(role):
    permissions = []
    if role == SUPER_ADMIN:
        return get_admin_permissions()
    if get_permission_meta(role):
        for app, perms in get_permission_meta(role).items():
            for perm in perms:
                permission = Permission.objects.get(codename=f"{perm}_{app}")
                permissions.append(permission)
        return permissions


def create_groups():
    for group_name in USER_ROLES:
        permissions_list = get_user_permission(group_name)
        new_group, created = Group.objects.get_or_create(name=group_name)
        if permissions_list:
            new_group.permissions.set(permissions_list)
