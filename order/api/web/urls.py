from rest_framework.routers import DefaultRouter
from django.urls import path

from . import views

router = DefaultRouter()
router.register(r"invoices", views.InvoiceViewSet, basename="invoices")

urlpatterns = [
    path("", views.InvoiceViewSet.as_view({"get": "list"}), name="order-management-root"),
]

urlpatterns += router.urls
