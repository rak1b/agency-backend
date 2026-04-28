from django.db import models
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework import viewsets
from simple_history.models import HistoricalRecords

from authentication import constants


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



class BaseModelViewSet(viewsets.ModelViewSet):

    permission_classes = [AllowAny]

    def _is_agent_type_user(self, user):
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

    def _apply_agent_scope(self, queryset):
        """
        Restrict agent-type users to only their owned records.
        Priority: explicit `agent` field, then `agency`, then `Agency` id fallback.
        """
        user = getattr(self.request, "user", None)
        if not self._is_agent_type_user(user):
            return queryset
        if not user:
            return queryset.none()

        scoped_agency_id = user.parent_agency_id
        model_class = queryset.model
        if self._has_model_field(model_class, "agent"):
            return queryset.filter(agent=self._resolve_agent_owner_user(user))

        if self._has_model_field(model_class, "agency"):
            if scoped_agency_id:
                return queryset.filter(agency_id=scoped_agency_id)
            return queryset.none()

        # Agency model itself has no `agency` FK, so scope by its own id.
        if model_class._meta.app_label == "agency_inventory" and model_class.__name__ == "Agency":
            if scoped_agency_id:
                return queryset.filter(id=scoped_agency_id)
            return queryset.none()

        return queryset

    def get_queryset(self):
        base_queryset = super().get_queryset()
        return self._apply_agent_scope(base_queryset)

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
        soft_deleted_queryset = self._apply_agent_scope(soft_deleted_queryset)
        instance = soft_deleted_queryset.get(**{self.lookup_field: lookup_value})
        instance.hard_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='soft-deleted')
    def get_soft_deleted(self, request, *args, **kwargs):
        queryset = self.queryset.model.all_objects.filter(is_deleted=True)
        queryset = self._apply_agent_scope(queryset)
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
            queryset = self._apply_agent_scope(queryset)
            instance = queryset.get(**{self.lookup_field: lookup_value})
        except self.queryset.model.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        instance.is_deleted = False
        instance.deleted_at = None
        instance.deleted_by = None
        instance.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)