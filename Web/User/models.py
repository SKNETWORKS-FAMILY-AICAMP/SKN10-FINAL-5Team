# Django의 기본 사용자 기능(인증/권한 등)을 제공하는 추상 클래스
from django.contrib.auth.models import AbstractUser

# Django 모델을 정의하기 위한 모듈
from django.db import models


class User(AbstractUser):

    # username 필드 제거 → 기본 username 로그인 사용 안 함 (우리는 user_id 사용)
    username = None  

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

    # username이 아닌 user_id를 인증 기준으로 사용하도록 명시
    USERNAME_FIELD = 'user_id'

    # createsuperuser 등에서 요구되는 필드 설정(우리는 없음)
    REQUIRED_FIELDS = []

    # 복합 고유 제약(unique_auth_id_server) 설정
    # auth_id(네이버에서 오는 고유 id) + auth_server로 고유 식별
    # auth_id + auth_server 조합이 유일해야 함 
    # (예: 네이버, 카카오 로그인에서 고유 id가 같아도 서버가 다르면 다른 사용자임)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['auth_id', 'auth_server'], name='unique_auth_id_server')
        ]


# 리프레시 토큰 모델 정의
# user : 한 User당 여러 개 refresh token 저장 가능 (지금은 싱글 디바이스 정책이므로 1개 유지)
class RefreshToken(models.Model):
    token_id = models.AutoField(primary_key=True, verbose_name='토큰 아이디')
    token = models.TextField(unique=True, verbose_name='토큰')
    create_dt = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    expired_dt = models.DateTimeField(verbose_name='만료일시')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자 아이디')

    def __str__(self):
        return f"{self.user.user_nm} - {self.token_id}"


# 알림 상태 모델 정의
class NotificationStatus(models.Model):
    status_id = models.AutoField(primary_key=True, verbose_name='알림 상태 아이디')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자 아이디')
    last_checked_count = models.IntegerField(default=0, verbose_name='마지막 확인한 정책 개수')
    last_checked_dt = models.DateTimeField(auto_now=True, verbose_name='마지막 확인 일시')

    class Meta:
        unique_together = ['user']

    def __str__(self):
        return f"{self.user.user_nm} - {self.last_checked_count}개"