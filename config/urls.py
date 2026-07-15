from django.contrib import admin
from django.urls import path
from .api import api  # Mengimpor objek api dari config/api.py

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api.urls),  # Menyediakan rute otomatis untuk /api/docs
]