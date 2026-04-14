from django.urls import path,include
from django.conf import settings
from . import views

urlpatterns = [
    path('list/', views.UserList.as_view(), name='list'),
    path('admin-login/', views.AdminLoginView.as_view(), name='admin_login'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.registration_view, name='registration'),
    # path('account_details/<uuid:uuid>', views.PersonalDetailView.as_view(), name='account_details'),
    path('update-account/', views.UpdateAccountView.as_view(), name='update_account'),
    # path('update-account/', views.update_account_view, name='update_account'),
    path('change-password-request/', views.PasswordChangeRequestView.as_view(), name='change_password_request'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset_password'),

    # Merchant Pocket API's
    # path('merchant/', include('pocket.api.urls')),
    # path('merchant/login', views.MerchantLoginView.as_view(), name='merchant_login'),
    # path('merchant/profile', views.ProfileDetailView.as_view(), name='merchant_profile'),
]