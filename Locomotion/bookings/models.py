from django.db import models
from django.conf import settings
from drivers.models import DriverProfile

User = settings.AUTH_USER_MODEL

class RideRequest(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ride_requests")
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name="ride_requests")
    
    source_location = models.CharField(max_length=255)
    source_lat = models.FloatField()
    source_lng = models.FloatField()
    
    destination_location = models.CharField(max_length=255)
    destination_lat = models.FloatField()
    destination_lng = models.FloatField()
    
    vehicle_details = models.CharField(max_length=255, null=True, blank=True)
    
    distance_km = models.FloatField(null=True, blank=True)
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.rider.name} -> {self.driver.user.name} ({self.status})"
