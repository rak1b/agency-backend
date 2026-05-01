from django.db import models
from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, AllowAny
from rest_framework import viewsets
from simple_history.models import HistoricalRecords

from authentication import constants
from authentication.tenant_utils import (
    is_student_portal_user,
    tenant_agency_save_kwargs,
    tenant_business_id,
    user_is_master_admin,
)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        return super().get_queryset()
    
class SoftDeleteAdminManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()
    


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey('authentication.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    is_active = models.BooleanField(default=True)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Keep the default manager
    admin_objects = SoftDeleteAdminManager()  # Manager to include soft-deleted records in admin
    history = HistoricalRecords(inherit=True)
    class Meta:
        abstract = True
        ordering = ('-created_at', '-updated_at')

    def delete(self, user=None, *args, **kwargs):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()

    def hard_delete(self, *args, **kwargs):
        super(BaseModel, self).delete(*args, **kwargs)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()
    @property
    def default_image(self):
        return "https://dummyjson.com/image/300x300?type=webp&text=PaymentSave_Inventory&fontFamily=baton"

    # History related methods
    def get_history(self, start_date=None, end_date=None):
        """Get all historical records ordered by most recent first"""
        queryset = self.history.all().order_by('-history_date')
        
        # Apply date filters if provided
        if start_date:
            queryset = queryset.filter(history_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(history_date__lte=end_date)
            
        return queryset
    
    def get_last_change(self):
        """Get the most recent change"""
        return self.history.most_recent()
    
    def get_field_history(self, field_name):
        """Get history of specific field changes"""
        return [
            {
                'date': record.history_date,
                'user': record.history_user,
                'value': getattr(record, field_name),
                'type': record.history_type
            }
            for record in self.history.all().order_by('-history_date')
        ]
    
    def revert_to(self, history_id):
        """Revert to a specific point in history"""
        try:
            historical_record = self.history.get(history_id=history_id)
            for field in [f.name for f in self._meta.fields if f.name not in ['id', 'created_at', 'updated_at']]:
                setattr(self, field, getattr(historical_record, field))
            self.save()
            return True
        except self.history.model.DoesNotExist:
            return False
    
    def get_changed_fields(self, history_record=None):
        """Get fields that changed in the most recent update or specific history record"""
        if not history_record:
            history_record = self.get_last_change()
            if not history_record:
                return {}
        
        if history_record.prev_record:
            changed_fields = {}
            for field in [f.name for f in self._meta.fields]:
                old_value = getattr(history_record.prev_record, field, None)
                new_value = getattr(history_record, field, None)
                if old_value != new_value:
                    changed_fields[field] = {
                        'old': old_value,
                        'new': new_value
                    }
            return changed_fields
        return {}



class StudentPortalReadOnlyMixin:
    """
    Student accounts may only use safe HTTP methods on this viewset (read-only).
    """

    def dispatch(self, request, *args, **kwargs):
        user = getattr(request, "user", None)
        if (
            user
            and user.is_authenticated
            and is_student_portal_user(user)
            and request.method not in SAFE_METHODS
        ):
            raise PermissionDenied("Students may only read this resource.")
        return super().dispatch(request, *args, **kwargs)


class BaseModelViewSet(viewsets.ModelViewSet):

    permission_classes = [AllowAny]

    def _is_b2b_agent_type_user(self, user):
        if not user or not user.is_authenticated:
            return False
        return user.user_type in {
            constants.UserTypeChoice.B2B_AGENT,
            constants.UserTypeChoice.B2B_AGENT_EMPLOYEE,
        }

    def _has_model_field(self, model_class, field_name):
        return any(field.name == field_name for field in model_class._meta.get_fields())

    def _resolve_agent_owner_user(self, user):
        """
        Employee accounts are scoped under their parent B2B agent.
        """
        if (
            user.user_type == constants.UserTypeChoice.B2B_AGENT_EMPLOYEE
            and user.parent_b2b_agent_id
        ):
            return user.parent_b2b_agent
        return user

    def _apply_tenant_scope(self, queryset):
        """
        Row-level tenant isolation: master admins see everything; otherwise rows are scoped
        by ``business_id`` when available, falling back to a single-agency PK for legacy rows.

        B2B users with an ``agent`` FK continue to use that column when present (separate pathway).
        """
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return queryset.none()

        if user_is_master_admin(user):
            return queryset

        model_class = queryset.model

        # B2B inventory where ownership is expressed via ``agent`` on the row.
        if self._is_b2b_agent_type_user(user) and self._has_model_field(model_class, "agent"):
            return queryset.filter(agent=self._resolve_agent_owner_user(user))

        scoped_business_id = tenant_business_id(user)

        if scoped_business_id:
            if self._has_model_field(model_class, "business"):
                qs = queryset.filter(business_id=scoped_business_id)
            elif self._has_model_field(model_class, "agency"):
                qs = queryset.filter(agency__business_id=scoped_business_id)
            elif model_class._meta.app_label == "agency_inventory" and model_class.__name__ == "Agency":
                qs = queryset.filter(business_id=scoped_business_id)
            else:
                return queryset.none()
            return self._apply_student_portal_row_scope(qs, user, model_class)

        # Legacy path before every agency row has ``business_id`` populated.
        scoped_agency_id = getattr(user, "parent_agency_id", None)
        if not scoped_agency_id and getattr(user, "user_type", None) == constants.UserTypeChoice.STUDENT:
            linked_sid = getattr(user, "linked_student_file_id", None)
            if linked_sid:
                from agency_inventory.models import StudentFile

                scoped_agency_id = (
                    StudentFile.objects.filter(pk=linked_sid)
                    .values_list("agency_id", flat=True)
                    .first()
                )

        if not scoped_agency_id:
            return queryset.none()

        if self._has_model_field(model_class, "agency"):
            qs = queryset.filter(agency_id=scoped_agency_id)
        elif model_class._meta.app_label == "agency_inventory" and model_class.__name__ == "Agency":
            qs = queryset.filter(id=scoped_agency_id)
        else:
            return queryset.none()

        return self._apply_student_portal_row_scope(qs, user, model_class)

    def _apply_student_portal_row_scope(self, queryset, user, model_class):
        """
        After business/agency isolation, students only see rows tied to ``user.linked_student_file``.
        Reference data (countries, programs, universities, etc.) stays visible within that tenant slice.
        """
        if not is_student_portal_user(user):
            return queryset

        linked_id = getattr(user, "linked_student_file_id", None)
        if not linked_id:
            return queryset.none()

        label = model_class._meta.label

        # Read-only catalogue within the same agency (used by forms / lookups).
        if label in (
            "agency_inventory.Agency",
            "agency_inventory.Country",
            "agency_inventory.Program",
            "agency_inventory.University",
            "agency_inventory.UniversityIntake",
            "agency_inventory.UniversityProgram",
            "agency_inventory.UniversityProgramSubject",
        ):
            return queryset

        if label == "agency_inventory.StudentFile":
            return queryset.filter(pk=linked_id)

        if self._has_model_field(model_class, "student_file"):
            return queryset.filter(student_file_id=linked_id)

        if label == "agency_inventory.AppliedUniversity":
            return queryset.filter(student_files__id=linked_id).distinct()

        if label == "agency_inventory.StudentFileAttachment":
            return queryset.filter(student_files__id=linked_id).distinct()

        if label == "order.Invoice":
            return queryset.filter(student_id=linked_id)

        if label == "order.InvoiceLineItem":
            return queryset.filter(invoice__student_id=linked_id)

        if label == "order.InvoiceAttachment":
            return queryset.filter(invoices__student_id=linked_id).distinct()

        if label == "support.Ticket":
            return queryset.filter(student_file_id=linked_id)

        if label == "support.TicketReply":
            return queryset.filter(ticket__student_file_id=linked_id)

        if label == "support.TicketAttachment":
            return queryset.filter(
                Q(ticket__student_file_id=linked_id)
                | Q(reply__ticket__student_file_id=linked_id),
            ).distinct()

        return queryset.none()

    def get_queryset(self):
        base_queryset = super().get_queryset()
        return self._apply_tenant_scope(base_queryset)

    def get_tenant_save_kwargs(self, serializer):
        """
        Merge into ``serializer.save()`` so tenant users always persist their own
        ``business_id`` / ``agency_id`` when the model supports them (overrides client payload).
        """
        model = getattr(serializer.Meta, "model", None)
        if not model:
            return {}
        user = getattr(self.request, "user", None)
        return tenant_agency_save_kwargs(user, model, self._has_model_field)

    def perform_create(self, serializer):
        serializer.save(**self.get_tenant_save_kwargs(serializer))

    def perform_update(self, serializer):
        serializer.save(**self.get_tenant_save_kwargs(serializer))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete(user=self.request.user)

    @action(detail=True, methods=['delete'], url_path='hard-delete')
    def hard_delete(self, request, *args, **kwargs):
        # Use the dynamic lookup_field and enforce agent-level ownership.
        lookup_value = kwargs.get(self.lookup_field)
        soft_deleted_queryset = self.queryset.model.all_objects.all()
        soft_deleted_queryset = self._apply_tenant_scope(soft_deleted_queryset)
        instance = soft_deleted_queryset.get(**{self.lookup_field: lookup_value})
        instance.hard_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='soft-deleted')
    def get_soft_deleted(self, request, *args, **kwargs):
        queryset = self.queryset.model.all_objects.filter(is_deleted=True)
        queryset = self._apply_tenant_scope(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='retrieve-soft-deleted')
    def retrieve_soft_deleted(self, request, **kwargs):
        # Use the dynamic lookup_field instead of hardcoded 'slug'
        lookup_value = kwargs.get(self.lookup_field)
        
        try:
            queryset = self.queryset.model.all_objects.filter(is_deleted=True)
            queryset = self._apply_tenant_scope(queryset)
            instance = queryset.get(**{self.lookup_field: lookup_value})
        except self.queryset.model.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        instance.is_deleted = False
        instance.deleted_at = None
        instance.deleted_by = None
        instance.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)