from django.contrib import admin
from django.urls import path
from .views import login_view

app_name = 'user'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
]
