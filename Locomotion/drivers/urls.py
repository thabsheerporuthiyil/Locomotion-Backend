from django.urls import path
from .views import ApplyDriverView,DriverListView,DriverDetailView, DriverVehicleDataView,DriverAvailabilityView
from .admin_views import AdminDriverApplicationListView,AdminDriverApplicationActionView, AdminVehicleListView, AdminVehicleActionView


urlpatterns = [
    path("apply/", ApplyDriverView.as_view()),
    path("admin/applications/", AdminDriverApplicationListView.as_view()),
    path(
    "admin/applications/<int:pk>/action/",
    AdminDriverApplicationActionView.as_view(),
    ),
    path("admin/vehicles/", AdminVehicleListView.as_view()),
    path("admin/vehicles/<int:pk>/action/", AdminVehicleActionView.as_view()),
    path("", DriverListView.as_view(), name="driver-list"),
    path("<int:id>/", DriverDetailView.as_view(), name="driver-detail"),

    path("vehicles/", DriverVehicleDataView.as_view()),
    path('availability/', DriverAvailabilityView.as_view(), name='driver-availability'),
]