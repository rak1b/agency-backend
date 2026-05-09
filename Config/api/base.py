from django.urls import path, include
from django.contrib.auth.mixins import LoginRequiredMixin
from drf_spectacular.views import SpectacularAPIView

# OpenAPI schema (login required). Mounted under ``/api/`` in ``Config.urls`` so it matches before
# ``include('Config.api.base')`` — some reverse proxies / Dokploy setups were not hitting nested routes.
class ProtectedSpectacularAPIView(LoginRequiredMixin, SpectacularAPIView):
    login_url = "/auth/secure/super-admin/login/"
    redirect_field_name = "redirect_to"


urlpatterns = [
    path('v1', include('Config.api.v1.urls'))  # Removed `namespace`, ensure it is defined in `api.v1.urls.py`
]
