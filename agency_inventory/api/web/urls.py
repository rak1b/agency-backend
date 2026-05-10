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
    path('university-form-download/', views.UniversityFormDownloadAPIView.as_view(), name='university-form-download'),
    path('university-form-html/', views.UniversityFormViewAPIView.as_view(), name='university-form-html'),
    path("public/countries/", views.PublicCountryCatalogAPIView.as_view(), name="public-country-catalog"),
    path("public/universities/", views.PublicUniversityCatalogAPIView.as_view(), name="public-university-catalog"),
    path(
        "public/universities/<slug:slug>/",
        views.PublicUniversitySelectionAPIView.as_view(),
        name="public-university-selection",
    ),
    path("public/student-files/submit/", views.PublicStudentFileCreateAPIView.as_view(), name="public-student-file-submit"),
]

urlpatterns += router.urls