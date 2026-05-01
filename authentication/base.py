from django.db import models
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import SAFE_METHODS, AllowAny
from rest_framework import viewsets
from simple_history.models import HistoricalRecords

from authentication.tenant_utils import (
    is_student_portal_user,
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

    def _has_model_field(self, model_class, field_name):
        return any(field.name == field_name for field in model_class._meta.get_fields())

    def _apply_tenant_scope(self, queryset):
        """
        Business-only tenant isolation.

        Master admins see every row. Business users only see rows whose
        ``business_id`` matches ``user.parent_business_id``.
        """
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return queryset.none()

        if user_is_master_admin(user):
            return queryset

        model_class = queryset.model

        business_id = tenant_business_id(user)
        if not business_id or not self._has_model_field(model_class, "business"):
            return queryset.none()

        return queryset.filter(business_id=business_id)

    def get_queryset(self):
        base_queryset = super().get_queryset()
        return self._apply_tenant_scope(base_queryset)

    def get_tenant_save_kwargs(self, serializer):
        """
        Force business-owned writes to the authenticated user's business.
        """
        model = getattr(serializer.Meta, "model", None)
        if not model:
            return {}
        user = getattr(self.request, "user", None)
        if user_is_master_admin(user) or not self._has_model_field(model, "business"):
            return {}

        business_id = tenant_business_id(user)
        if not business_id:
            raise ValidationError({"business": "Your user account is not assigned to a business."})
        return {"business_id": business_id}

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
        # Use the dynamic lookup_field and enforce business-level ownership.
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