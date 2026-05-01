from django.contrib import admin
from django.contrib.auth.hashers import make_password

from Config.master_admin_site import master_admin_site

from .models import User, Role, Permission, RolePermission, Merchant, Confirmation, Notification, OauthToken, Section

# Register your models here.
class RoleAdmin(admin.ModelAdmin):
    """Admin for Role model to enable autocomplete."""
    search_fields = ('name', 'description')
    list_display = ('id', 'name', 'description', 'created_at')
    list_filter = ('created_at',)


class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'email', 'phone', 'get_roles_display', 
        'user_type', 'is_active', 'is_superuser', 'is_staff', 'gender', 'created_at'
    )
    search_fields = (
        'name', 'email', 'phone', 'employee_id', 'designation', 'role__name',
        'slug', 'user_id'
    )
    list_filter = (
        'role', 'is_active', 'is_superuser', 'is_staff',
        'user_type', 'gender', 'is_verified', 'is_approved', 'created_at', 'updated_at'
    )
    # Use filter_horizontal for better UX with ManyToMany fields
    filter_horizontal = ('groups', 'role')
    exclude = ('user_permissions',)
    readonly_fields = ('slug', 'user_id', 'created_at', 'updated_at', 'last_login')
    date_hierarchy = 'created_at'
    list_per_page = 25
    list_max_show_all = 100
    
    fieldsets = (
        ('User Information', {
            'fields': (
                'name', 'email', 'phone', 'slug', 'user_id', 'role', 'user_type',
                'parent_business', 'parent_agency', 'parent_b2b_agent', 'linked_student_file', 'employee_id', 'designation',
                'trade_license_no', 'commission_rate', 'contract_start_date',
                'contract_end_date', 'joining_date', 'gender', 'address', 'dob', 'image_url'
            )
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')
        }),
        ('Verification', {
            'fields': ('is_verified', 'is_approved')
        }),
        ('System Information', {
            'fields': ('last_login', 'last_login_ip', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries with prefetch_related for ManyToMany."""
        qs = User.objects.all()
        return qs.prefetch_related('role', 'groups')
    
    def get_roles_display(self, obj):
        """Display roles as comma-separated string."""
        roles = obj.role.all()
        if roles:
            return ', '.join([role.name for role in roles])
        return '-'
    get_roles_display.short_description = 'Roles'
    
    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get('password') and not form.cleaned_data['password'].startswith("pbkdf2"):
            obj.password = make_password(form.cleaned_data['password'])
        super().save_model(request, obj, form, change)

master_admin_site.register(User, CustomUserAdmin)
master_admin_site.register(Role, RoleAdmin)
master_admin_site.register(Permission)
master_admin_site.register(RolePermission)
master_admin_site.register(OauthToken)
master_admin_site.register(Merchant)
master_admin_site.register(Confirmation)
master_admin_site.register(Notification)
master_admin_site.register(Section)
