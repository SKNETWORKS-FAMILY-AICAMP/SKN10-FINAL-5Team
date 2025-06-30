from django.contrib import admin
from django.urls import path
from .views import chatbot_view, send_message, session_list, session_detail, search_chat_history, save_interest

app_name = "chatbot"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', chatbot_view, name='chatbot'),
    path('api/chat/', send_message, name='send_message'),
    path('api/sessions/', session_list, name='session_list'),
    path('api/sessions/<int:session_id>/', session_detail, name='session_detail'),
    path('api/search/', search_chat_history, name='search_chat_history'),
    path('api/interest/', save_interest, name='save_interest'),
]
