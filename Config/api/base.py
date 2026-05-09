from django.urls import path, include
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.contrib.auth.decorators import login_required

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

# Always mount schema + Swagger. Both require login, so this does not expose anonymous API docs on prod.
# (Previously gated on DEBUG / ENABLE_API_DOCS, which broke demo when env did not match runtime settings.)
urlpatterns.append(path('schema/', ProtectedSpectacularAPIView.as_view(), name='schema'))
urlpatterns.append(path('docs/', login_required(SpectacularSwaggerView.as_view(url_name='schema')), name='swagger-ui'))
urlpatterns.append(
    path(
        'docs',
        RedirectView.as_view(url='/api/docs/', permanent=True),
        name='swagger-ui-no-slash',
    ),
)
