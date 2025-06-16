from django.contrib import admin
from django.urls import path
from .views import home, get_policy_detail

app_name = "home"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('api/policy/<int:policy_id>/', get_policy_detail, name='policy_detail'),
]

