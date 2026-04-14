from django.utils.crypto import get_random_string
from django.utils.text import slugify
import uuid
from datetime import datetime
from django.db import models
import time
from django.db import transaction

def generate_product_slug(title, instance=None):
    from utils.common_import_utils import print_log
    from inventory.models import Product
    base_slug = slugify(title)
    timestamp = str(int(time.time()))
    slug = f"{base_slug}-{timestamp}"
    
    # If instance is provided, exclude it from the uniqueness check
    if instance and instance.pk:
        while Product.all_objects.filter(slug=slug).exclude(pk=instance.pk).exists():
            slug = f"{base_slug}-{timestamp}-{get_random_string(length=5)}"
    else:
        while Product.all_objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{timestamp}-{get_random_string(length=5)}"
    print_log(f"Generated slug: {slug}")
    return slug

def generate_unique_slug(slug_content, instance):
    base_slug = slugify(slug_content)
    timestamp = str(int(time.time()))
    slug = f"{base_slug}"
    KClass = instance.__class__
    if instance and instance.pk:
        while KClass.all_objects.filter(slug=slug).exclude(pk=instance.pk).exists():
            slug = f"{base_slug}-{timestamp}-{get_random_string(length=5,allowed_chars='abcdefghijklmnopqrstuvwxyz')}"
    else:
        while KClass.all_objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{timestamp}-{get_random_string(length=5,allowed_chars='abcdefghijklmnopqrstuvwxyz')}"
    
    return slug



def generate_unique_invoice_code(model, prefix="INV"):
    while True:  # Keep generating until a unique code is found
        # current_datetime = datetime.now().strftime("%M%S%f")[:10] 
        current_datetime = datetime.now().strftime("%y%m%d%S")  # Format: YYMMDDSS 
        unique_id = str(uuid.uuid4().int)[:5]  
        code = f"{prefix}{current_datetime}{unique_id}"

        # Check if the generated code already exists
        if not model.objects.filter(number=code).exists():
            return code  # Return only if unique
        
# utils/codes.py


def generate_unique_code(model, field_name='code', prefix='PERM', number_length=10):

    with transaction.atomic():
        # lock matching rows so two threads don’t pick the same "last"
        qs = (
            model.objects
            .select_for_update()
            .filter(**{f"{field_name}__startswith": prefix})
            .order_by(f"-{field_name}")
        )
        last = qs.first()
        if last:
            # strip off the prefix and parse the integer suffix
            last_num = int(getattr(last, field_name)[len(prefix):])
        else:
            last_num = 0

        new_num = last_num + 1
        new_code = f"{prefix}{new_num:0{number_length}d}"
        return new_code
