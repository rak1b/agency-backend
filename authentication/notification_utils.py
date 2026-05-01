from django.db.models import Q

from authentication import constants
from authentication.models import Notification, User
from authentication.tenant_utils import tenant_business_id


ADMIN_ROLE_NAMES = {"Super Admin"}


def user_is_admin(user):
    """
    Resolve admin visibility using explicit auth flags first, then fall back to the role relation.
    """

    if not user or not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.role.filter(name__in=ADMIN_ROLE_NAMES).exists()


def create_notifications_for_event(*, entity_type, action, instance, actor=None):
    """
    Create one notification row per recipient so reads stay user-specific.

    Visibility rules:
    - Admin users receive notifications for StudentFile, Agency, and User events.
    - Non-admin users receive only StudentFile notifications for their own actions.
    """

    business_id = _resolve_notification_business_id(instance=instance, actor=actor)
    admin_queryset = User.objects.filter(is_active=True).filter(
        Q(is_superuser=True)
        | Q(is_staff=True)
        | Q(role__name__in=ADMIN_ROLE_NAMES)
    )
    if business_id:
        admin_queryset = admin_queryset.filter(
            Q(is_superuser=True)
            | Q(parent_business_id=business_id)
        )

    admin_user_ids = set(admin_queryset.distinct().values_list("id", flat=True))

    recipient_ids = set(admin_user_ids)
    if (
        entity_type == constants.NotificationEntityTypeChoice.STUDENT_FILE
        and actor
        and getattr(actor, "is_authenticated", False)
        and actor.is_active
        and not user_is_admin(actor)
    ):
        recipient_ids.add(actor.id)

    if not recipient_ids:
        return 0

    title, message, reference_label = _build_notification_content(
        entity_type=entity_type,
        action=action,
        instance=instance,
        actor=actor,
    )

    actor_id = actor.id if actor and getattr(actor, "is_authenticated", False) else None
    notification_rows = [
        Notification(
            business_id=business_id,
            recipient_id=recipient_id,
            actor_id=actor_id,
            entity_type=entity_type,
            action=action,
            title=title,
            message=message,
            reference_id=getattr(instance, "id", None),
            reference_slug=getattr(instance, "slug", None),
            reference_label=reference_label,
        )
        for recipient_id in recipient_ids
    ]
    Notification.objects.bulk_create(notification_rows)
    return len(notification_rows)


def _resolve_notification_business_id(*, instance, actor=None):
    """Prefer the event object's business, then the user's tenant business."""
    instance_business_id = getattr(instance, "business_id", None) or getattr(instance, "parent_business_id", None)
    if instance_business_id:
        return instance_business_id
    if actor and getattr(actor, "is_authenticated", False):
        return tenant_business_id(actor)
    return None


def _build_notification_content(*, entity_type, action, instance, actor=None):
    entity_label_map = {
        constants.NotificationEntityTypeChoice.STUDENT_FILE: "Student File",
        constants.NotificationEntityTypeChoice.AGENCY: "Agency",
        constants.NotificationEntityTypeChoice.USER: "User",
    }
    action_verb_map = {
        constants.NotificationActionChoice.CREATED: "created",
        constants.NotificationActionChoice.UPDATED: "updated",
    }

    entity_label = entity_label_map[entity_type]
    action_verb = action_verb_map[action]
    actor_name = _resolve_actor_name(actor)
    reference_label = _resolve_reference_label(entity_type=entity_type, instance=instance)

    title = f"{entity_label} {action.title()}"
    if actor_name:
        message = f"{actor_name} {action_verb} {entity_label.lower()} \"{reference_label}\"."
    else:
        message = f"{entity_label} \"{reference_label}\" was {action_verb}."
    return title, message, reference_label


def _resolve_actor_name(actor):
    if not actor or not getattr(actor, "is_authenticated", False):
        return None
    return getattr(actor, "name", None) or getattr(actor, "email", None) or f"User {actor.id}"


def _resolve_reference_label(*, entity_type, instance):
    if entity_type == constants.NotificationEntityTypeChoice.STUDENT_FILE:
        student_file_id = getattr(instance, "student_file_id", None) or f"ID {instance.id}"
        full_name = f"{getattr(instance, 'given_name', '')} {getattr(instance, 'surname', '')}".strip()
        return f"{student_file_id} - {full_name}".strip(" -")

    if entity_type == constants.NotificationEntityTypeChoice.AGENCY:
        return getattr(instance, "name", None) or f"Agency {instance.id}"

    if entity_type == constants.NotificationEntityTypeChoice.USER:
        return (
            getattr(instance, "name", None)
            or getattr(instance, "email", None)
            or getattr(instance, "user_id", None)
            or f"User {instance.id}"
        )

    return str(instance)
