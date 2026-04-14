from rest_framework import permissions
from authentication.models import Permission, RolePermission
from rest_framework.permissions import BasePermission
 
def get_permission_code(view, action):
    """
    Returns the permission code to check for a given DRF view and action.

    Order of resolution:
    1. Method-level CUSTOM_PERMISSION_CODE (for custom actions)
    2. Class-level CUSTOM_PERMISSION_CODE (e.g., for generic views)
    3. Derived from DYNAMIC_PERMISSION_CODE and action (for standard actions)
    """
    # 1. Method-level: Check if the current action (e.g., 'my_terminals') has CUSTOM_PERMISSION_CODE
    action_method = getattr(view, action, None)
    if action_method and hasattr(action_method, 'CUSTOM_PERMISSION_CODE'):
        return getattr(action_method, 'CUSTOM_PERMISSION_CODE')

    # 2. Class-level: Check if view itself declares CUSTOM_PERMISSION_CODE
    if hasattr(view, 'CUSTOM_PERMISSION_CODE'):
        return getattr(view, 'CUSTOM_PERMISSION_CODE')

    # 3. Dynamic based on DYNAMIC_PERMISSION_CODE and action
    section_slug = getattr(view, 'DYNAMIC_PERMISSION_CODE', None)
    if not section_slug:
        return None

    action_to_suffix = {
        'list': f'view_{section_slug}_list',
        'retrieve': f'view_{section_slug}_details',
        'create': f'add_{section_slug}',
        'update': f'edit_{section_slug}',
        'partial_update': f'edit_{section_slug}',
        'destroy': f'delete_{section_slug}',
    }

    return action_to_suffix.get(action)


class HasCustomPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        action = getattr(view, 'action', None)
        if not action:
            action = request.method.lower()

        CUSTOM_PERMISSION_CODE = get_permission_code(view, action)
        if not CUSTOM_PERMISSION_CODE:
            return False

        user_roles = request.user.role.all()
        user_permission_codes = RolePermission.objects.filter(role__in=user_roles)\
            .values_list('permissions__code', flat=True)

        if CUSTOM_PERMISSION_CODE in user_permission_codes:
            return True
        else:
            return False

