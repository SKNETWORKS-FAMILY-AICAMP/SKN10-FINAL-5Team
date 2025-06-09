from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Chatbot'
    verbose_name = '청년정책 챗봇'
    label = 'chatbot'