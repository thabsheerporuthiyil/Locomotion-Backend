from django.contrib import admin
from .models import DriverApplication,DriverApplicationReview,DriverProfile

# Register your models here.
admin.site.register(DriverProfile)
admin.site.register(DriverApplicationReview)
admin.site.register(DriverApplication)
