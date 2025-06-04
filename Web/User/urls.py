from django.contrib import admin
from django.urls import path
from .views import *

app_name = 'user'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('naver/login/', NaverLoginRedirectView.as_view(), name='naver-login'),
    path('naver/callback/', NaverLoginCallbackView.as_view(), name='naver-callback'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', RefreshView.as_view(), name='refresh'),
    path('userinfo/', UserInfoView.as_view(), name='userinfo'),
]
