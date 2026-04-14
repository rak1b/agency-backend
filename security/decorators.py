from functools import wraps
from django.http import HttpResponseForbidden
from django.utils import timezone
from .models import LoginAttempt,BlockedIP,WhitelistedIP

def get_client_ip(request):
    """Get the IP address of the client making the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def login_attempt_limit(max_attempts_per_day=10):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            ip_addr = get_client_ip(request)
            response = view_func(request, *args, **kwargs)
            try:
                if WhitelistedIP.objects.filter(ip_address=ip_addr).exists():
                    return response
            except WhitelistedIP.DoesNotExist:
                print('Not Exists')
            
            # Count the number of login attempts in the last 24 hours
            last_24_hours = timezone.now() - timezone.timedelta(hours=24)
            attempt_count = LoginAttempt.objects.filter(
                ip_address=ip_addr,
                timestamp__gte=last_24_hours
            ).count()

            if attempt_count > max_attempts_per_day:
                # Block the IP address
                BlockedIP.objects.create(ip_address=ip_addr)
                return HttpResponseForbidden("Too many login attempts. Your IP has been blocked.")
            
            # If login failed, increment the count
            if response.status_code == 400:
                LoginAttempt.objects.create(ip_address=ip_addr)
                # Count the number of login attempts in the last 24 hours
                last_24_hours = timezone.now() - timezone.timedelta(hours=24)
                attempt_count = LoginAttempt.objects.filter(
                    ip_address=ip_addr,
                    timestamp__gte=last_24_hours
                ).count()

                if attempt_count > max_attempts_per_day:
                    # Block the IP address
                    BlockedIP.objects.create(ip_address=ip_addr)
                    return HttpResponseForbidden("Too many login attempts. Your IP has been blocked.")
            return response
        return _wrapped_view
    return decorator

# def login_attempt_limit(max_attempts_per_day=10):
#     def decorator(view_func):
#         @wraps(view_func)
#         def _wrapped_view(request, *args, **kwargs):
#             ip_addr = request.META['REMOTE_ADDR']

#             # Count the number of login attempts in the last 24 hours
#             last_24_hours = timezone.now() - timezone.timedelta(hours=24)
#             attempt_count = LoginAttempt.objects.filter(
#                 ip_address=ip_addr,
#                 timestamp__gte=last_24_hours
#             ).count()

#             if attempt_count > max_attempts_per_day:
#                 # Block the IP address
#                 BlockedIP.objects.create(ip_address=ip_addr)
#                 return HttpResponseForbidden("Too many login attempts. Your IP has been blocked.")
            

#             response = view_func(request, *args, **kwargs)
            

#             # Log the login attempt
#             if request.method == 'POST':
#                 LoginAttempt.objects.create(ip_address=ip_addr)
#                 # Count the number of login attempts in the last 24 hours
#                 last_24_hours = timezone.now() - timezone.timedelta(hours=24)
#                 attempt_count = LoginAttempt.objects.filter(
#                     ip_address=ip_addr,
#                     timestamp__gte=last_24_hours
#                 ).count()

#                 if attempt_count > max_attempts_per_day:
#                     # Block the IP address
#                     BlockedIP.objects.create(ip_address=ip_addr)
#                     return HttpResponseForbidden("Too many login attempts. Your IP has been blocked.")
#             return view_func(request, *args, **kwargs)
#         return _wrapped_view
#     return decorator
