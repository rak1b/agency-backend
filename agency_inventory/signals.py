"""
Keep ``StudentApplicationProgress`` in sync when related domain rows change.
"""

from django.apps import apps
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from agency_inventory.models import AppliedUniversity, StudentFile, StudentFileAttachment
from agency_inventory.services.application_progress import sync_application_progress


@receiver(post_save, sender=StudentFile, dispatch_uid="agency_inventory_sf_progress_sync")
def student_file_post_save_sync_progress(sender, instance, **kwargs):
    sync_application_progress(instance)


@receiver(post_save, sender=StudentFileAttachment, dispatch_uid="agency_inventory_sfa_progress_sync")
def student_file_attachment_post_save_sync_progress(sender, instance, **kwargs):
    for student_file in instance.student_files.all():
        sync_application_progress(student_file)


@receiver(post_delete, sender=StudentFileAttachment, dispatch_uid="agency_inventory_sfa_progress_delete")
def student_file_attachment_post_delete_sync_progress(sender, instance, **kwargs):
    for student_file in instance.student_files.all():
        sync_application_progress(student_file)


@receiver(
    m2m_changed,
    sender=StudentFile.attachments.through,
    dispatch_uid="agency_inventory_sf_attachments_m2m",
)
def student_file_attachments_m2m_changed(sender, instance, action, **kwargs):
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if isinstance(instance, StudentFile):
        sync_application_progress(instance)


@receiver(post_save, sender=AppliedUniversity, dispatch_uid="agency_inventory_au_progress_sync")
def applied_university_post_save_sync_progress(sender, instance, **kwargs):
    for student_file in instance.student_files.all():
        sync_application_progress(student_file)


def _sync_invoice_student_progress(invoice_instance):
    student = getattr(invoice_instance, "student", None)
    if student is not None:
        sync_application_progress(student)


def invoice_post_save_for_progress(sender, instance, **kwargs):
    _sync_invoice_student_progress(instance)


def _connect_invoice_signal():
    try:
        Invoice = apps.get_model("order", "Invoice")
    except LookupError:
        return

    post_save.connect(
        invoice_post_save_for_progress,
        sender=Invoice,
        dispatch_uid="agency_inventory_invoice_progress_sync",
        weak=False,
    )


_connect_invoice_signal()
