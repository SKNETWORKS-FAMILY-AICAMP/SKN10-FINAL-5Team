# Django의 기본 사용자 기능(인증/권한 등)을 제공하는 추상 클래스
from django.contrib.auth.models import AbstractUser

# Django 모델을 정의하기 위한 모듈
from django.db import models


class User(AbstractUser):
    username = None  # username 필드 제거

    user_id = models.AutoField(primary_key=True)
    auth_id = models.CharField(max_length=100, unique=True)  # ← unique=True는 제거해도 무방
    auth_server = models.CharField(max_length=50)
    user_nm = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    profile_img = models.URLField(null=True, blank=True)
    birthyear = models.CharField(max_length=4, null=True, blank=True)
    birthday = models.CharField(max_length=5, null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    addr = models.CharField(max_length=200, null=True, blank=True)
    create_dt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user_nm

    USERNAME_FIELD = 'user_id' # id 필드 정의
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['auth_id', 'auth_server'], name='unique_auth_id_server')
        ]


# 리프레시 토큰 모델 정의
class RefreshToken(models.Model):
    token_id = models.AutoField(primary_key=True)
    token = models.TextField(unique=True)
    create_dt = models.DateTimeField(auto_now_add=True)
    expired_dt = models.DateTimeField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.user_nm} - {self.token_id}"

