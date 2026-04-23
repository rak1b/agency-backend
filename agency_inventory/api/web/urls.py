from rest_framework.routers import DefaultRouter
from django.urls import path
from . import views

router = DefaultRouter()
router.register(r'agencies', views.AgencyViewSet, basename='agencies')
router.register(r'countries', views.CountryViewSet, basename='countries')
router.register(r'programs', views.ProgramViewSet, basename='programs')
router.register(r'customers', views.CustomerViewSet, basename='customers')
router.register(r'student-files', views.StudentFileViewSet, basename='student-files')
router.register(r'universities', views.UniversityViewSet, basename='universities')
router.register(r'university-intakes', views.UniversityIntakeViewSet, basename='university-intakes')
router.register(r'university-programs', views.UniversityProgramViewSet, basename='university-programs')
router.register(r'office-costs', views.OfficeCostViewSet, basename='office-costs')
router.register(r'student-costs', views.StudentCostViewSet, basename='student-costs')

urlpatterns = [
    path('', views.AgencyViewSet.as_view({'get': 'list'}), name='agency-management-root'),
    path('dashboard/', views.InventoryDashboardAPIView.as_view(), name='inventory-dashboard'),
]

urlpatterns += router.urls