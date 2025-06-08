from django.contrib import admin
from django.urls import path
from . import views

app_name = "chatbot"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.chatbot_page, name='chatbot'),
    path('message/', views.chat_message, name='chat-message'),
]
