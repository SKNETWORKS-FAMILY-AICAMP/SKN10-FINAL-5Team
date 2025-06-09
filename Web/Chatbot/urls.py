from django.contrib import admin
from django.urls import path
from .views import ChatbotPageView, chat_message, reset_session

app_name = "chatbot"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', ChatbotPageView.as_view(), name='chatbot'),
    path('api/chat/', chat_message, name='chat_message'),
    path('api/reset-session/', reset_session, name='reset_session'),
]
