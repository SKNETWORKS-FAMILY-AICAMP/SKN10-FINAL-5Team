from django.contrib import admin
from django.urls import path
from .views import chatbot, chat_message

app_name = "chatbot"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chatbot/', chatbot, name='chatbot'),
    path('api/chat/', chat_message, name='chat_message'),
]
