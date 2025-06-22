from django.db import models
from User.models import User  # User 모델 import (경로에 맞게 수정 필요)
from Home.models import Policies  # Policies 모델 import (경로에 맞게 수정 필요)

class ChatSession(models.Model):
    session_id = models.AutoField(primary_key=True, verbose_name='세션 아이디')
    session_nm = models.CharField(max_length=100, verbose_name='세션 이름')
    create_dt = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자 아이디')


class Message(models.Model):
    MSG_SENDER_CHOICES = [
        ('user', '사용자'),
        ('chatbot', '챗봇'),
    ]
    msg_id = models.AutoField(primary_key=True, verbose_name='메시지 아이디')
    sender = models.CharField(max_length=10, choices=MSG_SENDER_CHOICES, verbose_name='발신자')
    content = models.TextField(verbose_name='내용')
    sql_result = models.JSONField(null=True, blank=True, verbose_name='SQL 결과')
    create_dt = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, verbose_name='세션 아이디')


class SearchHistory(models.Model):
    search_id = models.AutoField(primary_key=True, verbose_name='검색 기록 아이디')
    query = models.TextField(verbose_name='검색 쿼리')
    search_dt = models.DateTimeField(auto_now_add=True, verbose_name='검색 일시')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자 아이디')


class RecommendInterest(models.Model):
    INTEREST_STATUS_CHOICES = [
        ('추천', '추천'),
        ('확인', '확인'),
        ('신청', '신청'),
    ]
    interest_id = models.AutoField(primary_key=True, verbose_name='추천 관심도 아이디')
    interest_status = models.CharField(max_length=10, choices=INTEREST_STATUS_CHOICES, verbose_name='관심도')
    plcy_no = models.ForeignKey(Policies, on_delete=models.CASCADE, verbose_name='정책번호')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자 아이디')