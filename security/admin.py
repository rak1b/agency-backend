from Config.master_admin_site import master_admin_site

from .models import BlockedIP, LoginAttempt, WhitelistedIP

# Register your models here.
master_admin_site.register(LoginAttempt)
master_admin_site.register(BlockedIP)
master_admin_site.register(WhitelistedIP)