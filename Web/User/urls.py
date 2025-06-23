from django.contrib import admin
from django.urls import path
from .views import *

app_name = 'user'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('naver/login/', naver_login_redirect, name='naver-login'),
    path('naver/callback/', naver_login_callback, name='naver-callback'),
    path('logout/', logout_view, name='logout'),
    path('notifications/count/', get_notification_count, name='notification-count'),
    path('notifications/read/', mark_notifications_read, name='notification-read'),
]
