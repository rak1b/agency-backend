from django.contrib import admin
from .models import BlockedIP, LoginAttempt, WhitelistedIP

# Register your models here.
admin.site.register(LoginAttempt)
admin.site.register(BlockedIP)
admin.site.register(WhitelistedIP)