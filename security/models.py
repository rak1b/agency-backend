from django.db import models
from authentication.base import BaseModel

# Create your models here.
class LoginAttempt(models.Model):
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ip_address} at {self.timestamp}"

class BlockedIP(BaseModel):
    ip_address = models.GenericIPAddressField(unique=True)
    blocked_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.ip_address
    
class WhitelistedIP(BaseModel):
    ip_address = models.GenericIPAddressField(unique=True)
    blocked_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.ip_address