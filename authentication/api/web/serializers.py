from rest_framework import serializers
from authentication.models import *
from rest_framework.validators import UniqueValidator
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import Group
from django.db import models
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
class DashboardRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    
class UserSerializer(serializers.ModelSerializer):
    role_details = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id','name','email','phone','password','role','role_details','user_id','image_url','gender','slug','is_active']
        lookup_field = 'slug'
        extra_kwargs = {
            'password': {'write_only': True},
            'slug': {'read_only': True},
            'role': {'write_only': True},
            'role_details': {'read_only': True},
        }
    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise ValidationError(e.messages)
        return value
    def get_role_details(self,obj):
        return AccountRoleSerializer(obj.role,many=True).data
        
    def create(self, validated_data):
        password = validated_data.pop('password',None)
        roles = validated_data.pop('role',None)
        if password:
            self.validate_password(password)
            validated_data['password'] = make_password(password)
        user = super().create(validated_data)
        if roles:
            for role in roles:
                user.role.add(role)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password',None)
        if password:
            self.validate_password(password)
            validated_data['password'] = make_password(password)
        roles = validated_data.pop('role',None)
        if roles:
            instance.role.clear()
            for role in roles:
                instance.role.add(role)
                
        for key,value in validated_data.items():
            setattr(instance,key,value)
            
        instance.save()
        return instance

class LoginRequestSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()

class RefreshTokenReqeustSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)


        
class ForgetPasswordRequestSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)

class ForgetPasswordConfirmSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(required=True)
    otp = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

class ResetPasswordRequestSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_new_password = serializers.CharField(required=True)

class AccountPropertiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email','username','phone','image','address']
        
class AccountRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id','name','description','is_active']
    
    # def validate_name(self, value):
    #     # Get the current instance if this is an update
    #     instance = getattr(self, 'instance', None)
        
    #     # If this is an update and we have an instance
    #     if instance:
    #         # Check if the name already exists (excluding current role)
    #         existing_role = Role.objects.filter(name=value).exclude(id=instance.id).first()
    #         if existing_role:
    #             raise serializers.ValidationError(f"Role with this name '{value}' already exists.")
    #     else:
    #         # For create, check if name already exists
    #         existing_role = Role.objects.filter(name=value).first()
    #         if existing_role:
    #             raise serializers.ValidationError(f"Role with this name '{value}' already exists.")
        
    #     return value
        
    
class SectionMinimizedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id','slug','name']
        


        
class PermissionMinimizedSerializer(serializers.ModelSerializer):
    # section = SectionMinimizedSerializer()
    class Meta:
        model = Permission
        exclude = ['section']        
class SectionWiseUserPermissionSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    class Meta:
        model = Section
        fields = ['id','slug','name','permissions']
        
    def get_permissions(self,obj):
        user = self.context['request'].user
        user_permissions = obj.get_user_permissions(user)
        return PermissionMinimizedSerializer(user_permissions,many=True).data
        
class AllSectionWisePermissionSerializer(serializers.ModelSerializer):
    permissions = PermissionMinimizedSerializer(many=True,source='get_all_permissions',read_only=True)
    class Meta:
        model = Section
        fields = '__all__'
        
class RolePermissionListSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source='role.name')
    description = serializers.ReadOnlyField(source='role.description')
    is_active = serializers.ReadOnlyField(source='role.is_active')
    
    class Meta:
        model = RolePermission
        fields = ['id','name','description','created_at','updated_at','is_active']
        
class AssignPermissionToRoleSerializer(serializers.ModelSerializer):
    role = AccountRoleSerializer(write_only=True)
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), write_only=True
    )
    permissions_details = PermissionMinimizedSerializer(
        many=True, source='permissions', read_only=True
    )
    name = serializers.ReadOnlyField(source='role.name')
    description = serializers.ReadOnlyField(source='role.description')
    is_active = serializers.ReadOnlyField(source='role.is_active')
    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'name', 'description', 'permissions', 'permissions_details','is_active']
    def validate_role_on_create(self, name):
        role = Role.objects.filter(name=name).first()
        if role:
            raise serializers.ValidationError(f"Role with this name '{name}' already exists.")
        return name
    
    def create(self, validated_data):
        permissions = validated_data.pop('permissions')
        role_data = validated_data.pop('role')

        # Check if the role already exists (optional)
        name = role_data.get('name',None)
        role = self.validate_role_on_create(name)
        role, _ = Role.objects.get_or_create(name=role_data['name'], defaults=role_data)

        # Create or get RolePermission
        role_permission, _ = RolePermission.objects.get_or_create(role=role)

        # Assign permissions
        role_permission.permissions.set(permissions)

        return role_permission

    def validate_role_on_update(self, name, current_role):
        if name:
            role = Role.objects.filter(name=name).exclude(id=current_role.id).first()
            if role:
                raise serializers.ValidationError(f"Role with this name '{name}' already exists.")
        return current_role
    
    def update(self, instance, validated_data):
        permissions = validated_data.pop('permissions',None)
        role_data = validated_data.pop('role',None)

        # Update role fields
        if role_data:
            name = role_data.get('name',None)
            role = self.validate_role_on_update(name,instance.role)
            for field, value in role_data.items():
                setattr(role, field, value)
            role.save()

        # Update permissions
        if permissions:
            instance.permissions.set(permissions)

        return instance

class RolePermissionSerializer(serializers.Serializer):
    # account = AccountDetailsSerializer()
    permissions = serializers.ListField(child=serializers.CharField())

class HistorySerializer(serializers.Serializer):
    history_id = serializers.SerializerMethodField()
    history_date = serializers.DateTimeField()
    history_type = serializers.SerializerMethodField()
    history_user = serializers.SerializerMethodField()
    changed_fields = serializers.SerializerMethodField()
    
    def get_history_id(self, obj):
        """Get the history_id (primary key) from the historical record."""
        # In simple-history, historical records have:
        # - 'id' field: the original object's ID (what we DON'T want)
        # - 'history_id' field: the primary key of the history record (what we DO want)
        # - 'pk' property: also returns history_id since it's the primary key
        # We should use pk or history_id, NOT id
        if hasattr(obj, 'history_id'):
            return obj.history_id
        elif hasattr(obj, 'pk'):
            return obj.pk
        # Don't use obj.id as it's the original object's ID, not the history record ID
        return None

    def get_history_type(self, obj):
        """Get human-readable history type."""
        type_map = {
            '+': 'Created',
            '~': 'Updated',
            '-': 'Deleted'
        }
        return type_map.get(obj.history_type, obj.history_type)
    
    def get_history_user(self, obj):
        if not obj.history_user:
            return None
        
        # Handle case where history_user might be an ID (integer) instead of User object
        user = obj.history_user
        if isinstance(user, int):
            try:
                user = User.objects.get(id=user)
            except User.DoesNotExist:
                return {
                    'id': user,
                    'name': None,
                    'email': None
                }
        
        # Handle case where user object exists
        if hasattr(user, 'id') and hasattr(user, 'name') and hasattr(user, 'email'):
            return {
                'id': user.id,
                'name': user.name if user.name else None,
                'email': user.email if user.email else None
            }
        
        # Fallback: if it's just an ID
        return {
            'id': user if isinstance(user, int) else getattr(user, 'id', None),
            'name': None,
            'email': None
        }

    def get_changed_fields(self, obj):
        if obj.prev_record:
            changed_fields = {}
            for field in [f.name for f in obj.instance._meta.fields]:
                old_value = getattr(obj.prev_record, field, None)
                new_value = getattr(obj, field, None)
                
                # Skip certain fields that are not meaningful to show
                if field in ['updated_at', 'created_at']:
                    continue
                
                # Handle ForeignKey fields
                if isinstance(obj.instance._meta.get_field(field), models.ForeignKey):
                    field_obj = obj.instance._meta.get_field(field)
                    related_model = field_obj.related_model
                    
                    # Handle User fields - show user name
                    if related_model and related_model.__name__ == 'User':
                        old_user_data = self._get_user_details(old_value) if old_value else None
                        new_user_data = self._get_user_details(new_value) if new_value else None
                        
                        if old_user_data != new_user_data:
                            changed_fields[field] = {
                                'field': self._get_field_label(obj.instance, field),
                                'old': self._format_user_display(old_user_data),
                                'new': self._format_user_display(new_user_data)
                            }
                    # Handle Product fields - show product small details
                    elif related_model and related_model.__name__ == 'Product':
                        old_product_data = self._get_product_details(old_value) if old_value else None
                        new_product_data = self._get_product_details(new_value) if new_value else None
                        
                        if old_product_data != new_product_data:
                            changed_fields[field] = {
                                'field': self._get_field_label(obj.instance, field),
                                'old': self._format_product_display(old_product_data),
                                'new': self._format_product_display(new_product_data)
                            }
                    # Handle Supplier objects which use uuid instead of id
                    elif hasattr(old_value, 'uuid') or hasattr(new_value, 'uuid'):
                        old_value = old_value.uuid if old_value and hasattr(old_value, 'uuid') else (old_value.id if old_value else None)
                        new_value = new_value.uuid if new_value and hasattr(new_value, 'uuid') else (new_value.id if new_value else None)
                        
                        if old_value != new_value:
                            changed_fields[field] = {
                                'field': self._get_field_label(obj.instance, field),
                                'old': str(old_value) if old_value else 'Not set',
                                'new': str(new_value) if new_value else 'Not set'
                            }
                    else:
                        old_value = old_value.id if old_value else None
                        new_value = new_value.id if new_value else None
                        
                        if old_value != new_value:
                            changed_fields[field] = {
                                'field': self._get_field_label(obj.instance, field),
                                'old': f'ID: {old_value}' if old_value else 'Not set',
                                'new': f'ID: {new_value}' if new_value else 'Not set'
                            }
                # Handle regular fields
                elif old_value != new_value:
                    changed_fields[field] = {
                        'field': self._get_field_label(obj.instance, field),
                        'old': self._format_value(old_value, field, obj.instance),
                        'new': self._format_value(new_value, field, obj.instance)
                    }
            
            # Handle ManyToMany fields
            for field in obj.instance._meta.many_to_many:
                try:
                    # Get current M2M values as a list of IDs
                    current_m2m = list(getattr(obj.instance, field.name).values_list('id', flat=True))
                    
                    # Get previous M2M values as a list of IDs
                    if hasattr(obj.prev_record, field.name):
                        old_m2m = list(getattr(obj.prev_record, field.name).values_list('id', flat=True))
                    else:
                        old_m2m = []
                    
                    if old_m2m != current_m2m:
                        changed_fields[field.name] = {
                            'field': self._get_field_label(obj.instance, field.name),
                            'old': f'{len(old_m2m)} item(s)' if old_m2m else 'None',
                            'new': f'{len(current_m2m)} item(s)' if current_m2m else 'None'
                        }
                except AttributeError:
                    continue
            
            return changed_fields
        return {}
    
    def _get_field_label(self, instance, field_name):
        """Get human-readable field label."""
        try:
            field = instance._meta.get_field(field_name)
            return field.verbose_name.title() if hasattr(field, 'verbose_name') and field.verbose_name else field_name.replace('_', ' ').title()
        except:
            return field_name.replace('_', ' ').title()
    
    def _format_value(self, value, field_name, instance):
        """Format value for display."""
        if value is None:
            return 'Not set'
        
        # Handle boolean values
        if isinstance(value, bool):
            return 'Yes' if value else 'No'
        
        # Handle date/time fields
        if field_name.endswith('_date') or field_name.endswith('_at'):
            if hasattr(value, 'strftime'):
                return value.strftime('%Y-%m-%d %H:%M:%S')
        
        # Handle email fields
        if 'email' in field_name.lower():
            return value
        
        # Handle choice fields
        try:
            field = instance._meta.get_field(field_name)
            if hasattr(field, 'choices') and field.choices:
                choices_dict = dict(field.choices)
                return choices_dict.get(value, value)
        except:
            pass
        
        return str(value) if value else 'Not set'
    
    def _format_user_display(self, user_data):
        """Format user data for display."""
        if not user_data:
            return 'Not assigned'
        if user_data.get('name'):
            return f"{user_data.get('name')} (ID: {user_data.get('id')})"
        return f"User ID: {user_data.get('id')}"
    
    def _format_product_display(self, product_data):
        """Format product data for display."""
        if not product_data:
            return 'Not set'
        
        parts = []
        if product_data.get('serial_number'):
            parts.append(f"SN: {product_data.get('serial_number')}")
        if product_data.get('title'):
            parts.append(product_data.get('title'))
        if product_data.get('product_model'):
            parts.append(f"Model: {product_data.get('product_model')}")
        
        if parts:
            return " | ".join(parts)
        return f"Product ID: {product_data.get('id')}"
    
    def _get_user_details(self, user):
        """Get user details (id and name) from user object or ID."""
        if not user:
            return None
        
        # If it's already a User object
        if hasattr(user, 'id') and hasattr(user, 'name'):
            return {
                'id': user.id,
                'name': user.name if user.name else None
            }
        
        # If it's an ID, try to fetch the user
        if isinstance(user, int):
            try:
                user_obj = User.objects.get(id=user)
                return {
                    'id': user_obj.id,
                    'name': user_obj.name if user_obj.name else None
                }
            except User.DoesNotExist:
                return {
                    'id': user,
                    'name': None
                }
        
        return None
    
    def _get_product_details(self, product):
        """Get product small details from product object or ID."""
        if not product:
            return None
        
        # If it's already a Product object
        if hasattr(product, 'id'):
            return {
                'id': product.id,
                'serial_number': getattr(product, 'serial_number', None),
                'title': getattr(product, 'title', None),
                'product_model': getattr(product.product_model, 'title', None) if hasattr(product, 'product_model') and product.product_model else None
            }
        
        # Product app was removed; keep graceful fallback for historical IDs.
        if isinstance(product, int):
            return {
                'id': product,
                'serial_number': None,
                'title': None,
                'product_model': None
            }
        
        return None

class CloudflareDeleteSerializer(serializers.Serializer):
    file_url = serializers.CharField(required=True)