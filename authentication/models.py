from authentication.base import BaseModel
from . import constants
from .helper import *
from django.core.exceptions import ObjectDoesNotExist
from authentication.base import BaseModel

def user_profile_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/users/<username>/<filename>
    return 'users/{0}/{1}'.format(instance.name, filename)

# Create your models here.
class Role(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=1200,help_text='Max 1200 words',null=True,blank=True)

    def __str__(self):
        return self.name
    class Meta:
        ordering = ['-created_at']
    
class Section(BaseModel):
    slug  = models.SlugField(blank=True,null=True)       # e.g. "inventory"
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
    def get_user_permissions(self,user):
        roles = user.role.all()
        role_permissions = RolePermission.objects.filter(role__in=roles).values_list('permissions',flat=True)
        permissions = Permission.objects.filter(id__in=role_permissions,section=self)
        return permissions
    
    def get_all_permissions(self):
        permissions = Permission.objects.filter(section=self)
        return permissions
    def save(self, *args, **kwargs):
        from utils.slug_utils import generate_unique_slug
        if not self.slug:
            self.slug = generate_unique_slug(self.name,self)
        super().save(*args, **kwargs)
    class Meta:
        ordering = ['-created_at']

class Permission(BaseModel):
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='permission_of_section',blank=True,null=True)
    code = models.CharField(max_length=255, help_text='Auto Generated EX:PERM0000001', unique=True,blank=True) # e.g., 'can_bulk_import_product'
    slug = models.SlugField(blank=True,null=True)
    name = models.CharField(max_length=255) # e.g., Can Bulk Import Product
    description = models.TextField(max_length=1200,help_text='Max 1200 words',null=True,blank=True)
    
    def __str__(self):
        return f"{self.id} -> {self.section.name if self.section else 'No Section'} -> {self.name}"
    
    def save(self, *args, **kwargs):
        from utils.slug_utils import generate_unique_code,generate_unique_slug
        if not self.slug:
            self.slug = generate_unique_slug(self.name,self)
            
        self.name = self.name.lower()
        super().save(*args, **kwargs)
        
    class Meta:
        ordering = ['-created_at']
        
    
    

class RolePermission(BaseModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    permissions = models.ManyToManyField(Permission)
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.role.name} -> {", ".join([permission.name for permission in self.permissions.all()])}'

class MyUserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        # Check if the "Super Admin" role exists, if not, create it
        role, created = Role.objects.get_or_create(name="Super Admin", defaults={'description': 'Has full access to all resources.'})
        
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    slug = models.SlugField(blank=True,null=True)
    user_id = models.CharField(max_length=30, blank=True,null=True)
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    image_url = models.URLField(max_length=1000, blank=True,null=True)
    # image = models.ImageField(default='users/default.png', upload_to=user_profile_path)
    dob = models.DateField(blank=True, null=True)
    role = models.ManyToManyField(Role, related_name='user_roles')
    user_type = models.CharField(
        max_length=30,
        choices=constants.USER_TYPE_OPTIONS,
        blank=True,
        null=True,
        help_text="Business user category used by the user-management UI.",
    )
    parent_agency = models.ForeignKey(
        "agency_inventory.Agency",
        on_delete=models.SET_NULL,
        related_name="linked_users",
        blank=True,
        null=True,
    )
    parent_b2b_agent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="managed_b2b_agent_employees",
        blank=True,
        null=True,
    )
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    designation = models.CharField(max_length=100, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    trade_license_no = models.CharField(max_length=100, blank=True, null=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    contract_start_date = models.DateField(blank=True, null=True)
    contract_end_date = models.DateField(blank=True, null=True)
    gender = models.SmallIntegerField(choices=constants.GENDER_OPTIONS, default=constants.MALE)
    address = models.TextField(blank=True, null=True)
    last_login_ip = models.CharField(max_length=100, blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = MyUserManager()
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        import uuid
        if not self.slug:
            self.slug = str(uuid.uuid4())
        if not self.user_id:
            self.user_id = str(uuid.uuid4())[:8]
        super().save(*args, **kwargs)
        
    

    def __str__(self):
        return self.email

    @property
    def get_full_name(self):
        return '%s %s' % (self.name, self.phone)

    @property
    def get_short_name(self):
        return self.name
        
    @property
    def get_merchant_uid(self):
        if hasattr(self, 'merchant'):
            return self.merchant.merchant_identifier
        return None
    
    @property
    def get_designation_title(self):
        if self.designation:
            return self.designation
        if hasattr(self, 'merchant'):
            return self.merchant.designation
        return None

    @property
    def generate_token(self):
        from .utils.auth_utils import regenerate_token
        token, created = regenerate_token(self)
        return token.key

    def get_token(self):
        return Token.objects.get(user_id=self.id).key

class Merchant(BaseModel):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    merchant_identifier = models.CharField(max_length=60, unique=True, default=auth_utils.unique_merchant_id)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    designation = models.CharField(max_length=60, blank=True, null=True)

    def __str__(self):
        return self.user.name
    
class OauthToken(BaseModel):
    access_token = models.TextField(null=False, blank=False)
    refresh_token = models.TextField(null=True, blank=True)
    expires_in = models.DateTimeField()

    @property
    def is_expired(self):
        from django.utils import timezone
        aware_datetime = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
        if self.expires_in < aware_datetime:
            return True
        return False

class CrmOauthToken(BaseModel):
    access_token = models.TextField(null=False, blank=False)
    refresh_token = models.TextField(null=True, blank=True)
    expires_in = models.DateTimeField()

    @property
    def is_expired(self):
        from django.utils import timezone
        aware_datetime = timezone.make_aware(datetime.datetime.now(), timezone.get_current_timezone())
        if self.expires_in < aware_datetime:
            return True
        return False
class Confirmation(BaseModel):
    identifier = models.CharField(max_length=60)
    code = models.CharField(max_length=10)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.identifier} - {self.code}"
        