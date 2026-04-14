import random
from authentication.models import User, Confirmation

def generate_code():
    code = str(random.randint(10000, 99999))
    while Confirmation.objects.filter(code=code).exists():
        code = str(random.randint(10000, 99999))
    return code

def validated_merchant_user(data):
    try:
        return User.objects.get(email=data)
    except Exception as e:
        return None

def verify_confirmation(identifier,code):
    try:
        return Confirmation.objects.filter(identifier=identifier,code=code,is_used=False).latest('created_at')
    except Confirmation.DoesNotExist:
        return None

def process_code(user):
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
        'name': uniq_user.name,
        'email': confirmation.identifier,
        'code': confirmation.code
    }
    return data
