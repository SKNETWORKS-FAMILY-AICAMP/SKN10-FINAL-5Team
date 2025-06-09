from django.urls import path
from .views import chatbot_query, chatbot_page

urlpatterns = [
    path('chatbot/', chatbot_query, name='chatbot_query'),
    path('', chatbot_page, name='chatbot_page'),  # 루트에 챗봇 페이지 연결
]