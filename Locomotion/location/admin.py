from django.contrib import admin
from .models import District,Taluk,Panchayath

# Register your models here.
admin.site.register(District)
admin.site.register(Taluk)
admin.site.register(Panchayath)