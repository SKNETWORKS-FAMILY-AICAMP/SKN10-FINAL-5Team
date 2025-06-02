from django.contrib import admin
from django.urls import path
from .views import chatbot

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chatbot/', chatbot, name='chatbot'),
]
