from django.contrib import admin
from .models import VehicleCategory,VehicleBrand,VehicleModel

# Register your models here.
admin.site.register(VehicleCategory),
admin.site.register(VehicleBrand),
admin.site.register(VehicleModel),
