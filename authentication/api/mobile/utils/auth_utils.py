from datetime import datetime
from authentication.models import User, Merchant

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def updateLastLoginInfo(request=None, user=None):
    user.last_login = datetime.now()
    user.last_login_ip = get_client_ip(request)
    user.save()

def validated_user_account(email=None):
    try:
        account = User.objects.get(email=email,is_active=True)
        return account
    except User.DoesNotExist:
        return None