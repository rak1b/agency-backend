from decouple import config
from django.urls import path, include
from django.contrib.auth.mixins import LoginRequiredMixin
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.contrib.auth.decorators import login_required

# Ensure DEBUG is correctly fetched
DEBUG = config('DEBUG', default=False, cast=bool)
ENABLE_API_DOCS = config('ENABLE_API_DOCS', default=False, cast=bool)

# Secure Spectacular API view
class ProtectedSpectacularAPIView(LoginRequiredMixin, SpectacularAPIView):
    login_url = "/auth/secure/super-admin/login/"
    redirect_field_name = "redirect_to"

# Secure Swagger view
class ProtectedSpectacularSwaggerView(LoginRequiredMixin, SpectacularSwaggerView):
    login_url = "/auth/secure/super-admin/login/"
    redirect_field_name = "redirect_to"

urlpatterns = [
    path('v1', include('Config.api.v1.urls'))  # Removed `namespace`, ensure it is defined in `api.v1.urls.py`
]

if DEBUG or ENABLE_API_DOCS:
    urlpatterns.append(path('schema/', ProtectedSpectacularAPIView.as_view(), name='schema'))
    # urlpatterns.append(path('docs/', ProtectedSpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'))
    urlpatterns.append(path('docs/', login_required(SpectacularSwaggerView.as_view(url_name='schema')), name='swagger-ui'))
