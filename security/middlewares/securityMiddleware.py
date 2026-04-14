from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from ..models import BlockedIP,LoginAttempt

class BlockIPMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip_addr = request.META['REMOTE_ADDR']
        if BlockedIP.objects.filter(ip_address=ip_addr).exists():
            return HttpResponseForbidden("Your IP has been blocked.")
        return None
