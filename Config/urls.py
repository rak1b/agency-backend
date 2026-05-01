"""entrepreneur URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from Config.master_admin_site import master_admin_site
from django.urls import path,include,re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.http import HttpResponse
# Error Response Handlers
from authentication import handlers
from django.utils.translation import gettext_lazy as _
handler403 = handlers.handler403
handler404 = handlers.handler404
handler500 = handlers.handler500
from decouple import config
IS_LIVE = config('IS_LIVE', default=False, cast=bool)

def custom_login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Pfizer2021QU
            if user.email in ['salmansadi165324@gmail.com', 'rakib@admin.com',]:
                login(request, user)
                next_url = request.GET.get('next', '/api/docs/')  # Default redirect
                return redirect(next_url)  # Redirect to `next` after login 
            else:
                form.add_error(None, _("Corona virus detected, You need to be quarantined"))
                return render(request, "registration/login.html", {"form": form})
    else:
        form = AuthenticationForm()
    return render(request, "registration/login.html", {"form": form})

def health_check(request):
    return HttpResponse("OK")
urlpatterns = [
    path('swagger/login/', custom_login_view, name='login'),
    path('auth/secure/super-admin/', master_admin_site.urls),
    path('api/', include('Config.api.base')),
    path('accounts/', include('allauth.urls')),
    path('health/', health_check),
    
    # path('authentication/', include('coreapp.urls')),
    # re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
] 

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve media files in both development and production
if not IS_LIVE:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Production media serving
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]