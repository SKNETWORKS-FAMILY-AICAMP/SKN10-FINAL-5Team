from django.contrib import admin
from django.urls import path
from .views import home

app_name = "home"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
]
