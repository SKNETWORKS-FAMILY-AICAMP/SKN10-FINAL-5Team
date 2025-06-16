from django.contrib import admin
from django.urls import path
from .views import chatbot_view, send_message, session_list, session_detail

app_name = "chatbot"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', chatbot_view, name='chatbot'),
    path('api/chat/', send_message, name='send_message'),
    path('api/sessions/', session_list, name='session_list'),
    path('api/sessions/<int:session_id>/', session_detail, name='session_detail'),
]
