from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Role, RolePermission


# @receiver(post_save, sender=Role)
# def create_rolepermission(sender, instance, created, **kwargs):
#     if created:
#         RolePermission.objects.get_or_create(role=instance)
