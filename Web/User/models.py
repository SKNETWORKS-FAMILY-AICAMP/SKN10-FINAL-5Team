# Django의 기본 사용자 기능(인증/권한 등)을 제공하는 추상 클래스
from django.contrib.auth.models import AbstractUser

# Django 모델을 정의하기 위한 모듈
from django.db import models


class User(AbstractUser):
    username = None  # username 필드 제거

    user_id = models.AutoField(primary_key=True, verbose_name='사용자 아이디')
    auth_id = models.CharField(max_length=100, unique=True, verbose_name='인증 아이디')
    auth_server = models.CharField(max_length=50, verbose_name='인증 서버')
    user_nm = models.CharField(max_length=100, verbose_name='이름')
    email = models.EmailField(unique=True, verbose_name='이메일')
    profile_img = models.URLField(null=True, blank=True, verbose_name='프로필 이미지')
    birthyear = models.CharField(max_length=4, null=True, blank=True, verbose_name='출생년도')
    birthday = models.CharField(max_length=5, null=True, blank=True, verbose_name='생일')
    gender = models.CharField(max_length=10, null=True, blank=True, verbose_name='성별')
    addr = models.CharField(max_length=200, null=True, blank=True, verbose_name='주소')
    create_dt = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')

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
    token_id = models.AutoField(primary_key=True, verbose_name='토큰 아이디')
    token = models.TextField(unique=True, verbose_name='토큰')
    create_dt = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    expired_dt = models.DateTimeField(verbose_name='만료일시')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자 아이디')

    def __str__(self):
        return f"{self.user.user_nm} - {self.token_id}"

