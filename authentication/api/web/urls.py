from rest_framework.routers import DefaultRouter
from django.urls import path,include
from django.conf import settings
from . import views

router = DefaultRouter()
router.register(r'role-list', views.RoleViewSet,basename='Inventory')
router.register(r'history', views.HistoryViewSet, basename='history')
router.register(r'all-permissions-section-wise', views.AllSectionWisePermissionAPI, basename='all-permissions-section-wise')
router.register(r'user-permissions-section-wise', views.SectionWiseUserPermissionAPI, basename='user-permissions-section-wise')
router.register(r'role', views.AssignPermissionToRoleAPI,basename='assign-permission-to-role')
router.register(r'user', views.UserAPI,basename='user')
urlpatterns = [
    # Web API's
    path('token/', views.WebUserLoginView.as_view(), name='web_user_login'),
    path('token/refresh/', views.WebRefreshTokenView.as_view(), name='web_token_refresh'),

    # path('moderaor/login/', views.WebLoginView.as_view(), name='web_moderator_login'),
    # path('admin/login/', views.WebLoginView.as_view(), name='web_admin_login'),
    path('reset-password/', views.WebResetPasswordAPIView.as_view(), name='web_reset_password'),
    path('forget-password/', views.PasswordChangeView.as_view(), name='web_forget_password'),
    path('forget-password-confirm/', views.PasswordChangeConfirmView.as_view(), name='web_forget_password_confirm'),

    # path('get-account-permissions/', views.UserPermissionsView.as_view(), name='get_account_permissions'),
    path('upload-image/', views.CloudflareUploadAPI.as_view(), name='upload_image'),
]


urlpatterns += router.urls