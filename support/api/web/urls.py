from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"tickets", views.TicketViewSet, basename="support-tickets")

urlpatterns = [
    path("", views.TicketViewSet.as_view({"get": "list"}), name="support-management-root"),
]

urlpatterns += router.urls
