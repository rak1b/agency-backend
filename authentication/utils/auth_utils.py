import random


def generate_code():
    from authentication.models import User, Confirmation
    code = str(random.randint(100000, 999999))
    while Confirmation.objects.filter(code=code).exists():
        code = str(random.randint(100000, 999999))
    return code

def unique_merchant_id():
    from ..models import Merchant
    code = "PS"+str(random.randint(1000000, 9999999))
    while Merchant.objects.filter(merchant_identifier=code).exists():
        code = "PS"+str(random.randint(1000000, 9999999))
    return code

def validated_user(identifier):
    from authentication.models import User, Confirmation
    user = None
    try:
        user = User.objects.get(email=identifier)
    except Exception as e:
        print(e)
    try:
        user = User.objects.get(phone=identifier)
    except Exception as e:
        print(e)
    return user

def process_code(user):
    from authentication.models import User, Confirmation
    uniq_user = None
    try:
        uniq_user = User.objects.get(email=user)
    except Exception as e:
        print(e)
    try:
        uniq_user = User.objects.get(phone=user)
    except Exception as e:
        print(e)
    code = generate_code()
    confirmation = Confirmation.objects.create(identifier=user, code=code)
    confirmation.save()
    data = {
        'name': uniq_user.username,
        'email': confirmation.identifier,
        'code': confirmation.code
    }
    return data

def create_user_confirmation(user):
    from authentication.models import User, Confirmation
    confirmation_code = Confirmation.objects.create(
        identifier=user,
        code=generate_code()
    )
    confirmation_code.save()
    return confirmation_code

def verify_confirmation(identifier,code):
    from authentication.models import User, Confirmation
    try:
        return Confirmation.objects.filter(identifier=identifier,code=code,is_used=False).latest('created_at')
    except Confirmation.DoesNotExist:
        return None
