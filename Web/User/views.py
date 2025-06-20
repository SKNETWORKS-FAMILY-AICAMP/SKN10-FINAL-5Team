import requests
from datetime import datetime
import jwt
import pytz

from django.conf import settings
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .token import create_access_token
from django.shortcuts import render, redirect
from .models import User 
from .token import JWT_KEY
from .models import RefreshToken
from .services import (
    get_naver_user_info,
    get_or_create_user_from_naver,
    generate_tokens,
    verify_refresh_token,
    decode_refresh_token,
)
from django.utils import timezone
from datetime import timedelta
from Home.models import Policies
from Chatbot.models import RecommendInterest
from django.views.decorators.http import require_http_methods
from django.db import models

# 로그인 화면 렌더링
# 아무 인증 처리 없음 → public_urls 에 포함 → middleware 통과
def login_view(request):
    return render(request, 'user/login.html')


# 사용자를 네이버 인증 페이지로 리다이렉트.
# 네이버 인증 URL 생성 후 사용자 브라우저를 그 주소로 리디렉션
# 로그인 성공시 설정한 redirect_uri로 code + state 보내줌 -> naver_login_callback으로 돌아옴
def naver_login_redirect(request):
    url = (
        f"https://nid.naver.com/oauth2.0/authorize?"
        f"response_type=code&client_id={settings.NAVER_CLIENT_ID}"
        f"&redirect_uri={settings.NAVER_REDIRECT_URI}&state=random_state"
    )
    return redirect(url)


# 네이버 로그인 콜백 처리 
def naver_login_callback(request):
    try:
        # 1. 네이버에서 전달받은 인증 code, state를 추출
        code = request.GET.get("code")
        state = request.GET.get("state")

        if not code:
            return redirect('user:login')

        # 2. 네이버에 access_token 요청
        # 네이버 API를 호출하여 인증 코드를 access_token으로 바꿈
        token_url = "https://nid.naver.com/oauth2.0/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.NAVER_CLIENT_ID,
            "client_secret": settings.NAVER_CLIENT_SECRET,
            "code": code,
            "state": state,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        token_response = requests.post(token_url, data=data, headers=headers).json()
        access_token = token_response.get("access_token")

        if not access_token:
            return redirect('user:login')

        # 3. access_token으로 사용자 정보 조회
        user_info = get_naver_user_info(access_token)

        # 4. 사용자 조회 또는 생성
        user = get_or_create_user_from_naver(user_info)

        # 5. JWT 발급
        access_token, refresh_token = generate_tokens(user.user_id)

        # 6. 기존 refreshToken 삭제 후 새로 저장(싱글 디바이스 정책 적용)
        RefreshToken.objects.filter(user=user).delete()

        now = datetime.now(pytz.timezone("Asia/Seoul"))
        expired_dt = now + JWT_KEY.RANDOM_OF_REFRESH_KEY.value[2]

        RefreshToken.objects.create(
            token=refresh_token,
            expired_dt=expired_dt,
            user=user
        )

        # 7. 응답 처리 - 쿠키 저장
        response = redirect('home:home')
        response.set_cookie(key='refresh_token', value=refresh_token, httponly=True)
        response.set_cookie(key='access_token', value=access_token, httponly=True)  
        
        # 세션에서 알림 관련 데이터 초기화 (새로운 로그인 시 알림 다시 표시)
        if 'last_checked_notification_count' in request.session:
            del request.session['last_checked_notification_count']
        
        return response

    except Exception as e:
        print(f"Naver login error: {str(e)}")
        return redirect('user:login')


# ✅ 로그아웃
def logout_view(request):
    # POST 요청만 허용
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed."}, status=405)
    
    refresh_token = request.COOKIES.get("refresh_token")  

    if not refresh_token:
        return JsonResponse({"error": "Refresh token not provided."}, status=400)

    try:
        user_id = decode_refresh_token(refresh_token)
    except jwt.ExpiredSignatureError:
        return JsonResponse({"error": "Expired refresh token."}, status=401)
    except jwt.InvalidTokenError:
        return JsonResponse({"error": "Invalid refresh token."}, status=401)

    # DB에서 refreshToken 삭제
    deleted_count, _ = RefreshToken.objects.filter(token=refresh_token, user__user_id=user_id).delete()

    if deleted_count == 0:
        return JsonResponse({"error": "Token not found."}, status=404)

    # 쿠키에서 access_token, refresh_token 모두 삭제
    response = redirect('home:home') 
    
    response.delete_cookie("refresh_token")
    response.delete_cookie("access_token")

    return response

def get_notification_count(request):
    """사용자에게 맞는 새로운 정책 개수를 반환하는 API"""
    if not request.user.is_authenticated:
        print("DEBUG: 사용자가 인증되지 않음")
        return JsonResponse({'count': 0})
    
    try:
        # 사용자의 나이 계산
        user = request.user
        print(f"DEBUG: 사용자 정보 - user_id: {user.user_id}, user_nm: {user.user_nm}")
        print(f"DEBUG: 출생년도: {user.birthyear}, 생일: {user.birthday}")
        
        if not user.birthyear or not user.birthday:
            print("DEBUG: 출생년도 또는 생일 정보가 없음")
            return JsonResponse({'count': 0})
        
        # 생일에서 월/일 추출
        birthday_month, birthday_day = user.birthday.split('-')
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_day = datetime.now().day
        
        # 나이 계산
        age = current_year - int(user.birthyear)
        if current_month < int(birthday_month) or (current_month == int(birthday_month) and current_day < int(birthday_day)):
            age -= 1
        
        print(f"DEBUG: 계산된 나이: {age}세")
        
        # 최근 일주일 이내 업데이트된 정책 필터링
        one_week_ago = timezone.now() - timedelta(days=7)
        today = timezone.now()
        print(f"DEBUG: 일주일 전 날짜: {one_week_ago}")
        print(f"DEBUG: 오늘 날짜: {today}")
        
        # 조건에 맞는 정책 조회
        matching_policies = Policies.objects.filter(
            updated_at__gte=one_week_ago,
            updated_at__lte=today
        ).filter(
            # 나이 조건: min_age <= 사용자나이 <= max_age 또는 min_age/max_age가 0/null인 경우
            models.Q(
                sprt_trgt_min_age__lte=age,
                sprt_trgt_max_age__gte=age
            ) |
            models.Q(sprt_trgt_min_age=0) |
            models.Q(sprt_trgt_min_age__isnull=True) |
            models.Q(sprt_trgt_max_age=0) |
            models.Q(sprt_trgt_max_age__isnull=True)
        )
        
        print(f"DEBUG: 나이 조건 + 업데이트 조건 만족하는 정책 개수: {matching_policies.count()}")
        
        # 사용자가 이미 확인하거나 신청한 정책 제외
        excluded_policies = RecommendInterest.objects.filter(
            user=user,
            interest_status__in=['확인', '신청']
        ).values_list('plcy_no', flat=True)
        
        print(f"DEBUG: 사용자가 이미 확인/신청한 정책 개수: {excluded_policies.count()}")
        if excluded_policies.exists():
            print(f"DEBUG: 제외할 정책 ID들: {list(excluded_policies)}")
        
        matching_policies = matching_policies.exclude(plcy_no__in=excluded_policies)
        
        count = matching_policies.count()
        print(f"DEBUG: 최종 매칭 정책 개수: {count}")
        
        # 세션에서 이전에 확인한 정책 개수 확인
        last_checked_count = request.session.get('last_checked_notification_count', 0)
        print(f"DEBUG: 이전에 확인한 정책 개수: {last_checked_count}")
        
        # 항상 현재 정책 개수를 반환 (새로운 정책 여부는 프론트엔드에서 처리)
        return JsonResponse({'count': count, 'is_new': count > last_checked_count})
        
    except Exception as e:
        print(f"DEBUG: 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'count': 0, 'error': str(e)})

@require_http_methods(["POST"])
def mark_notifications_read(request):
    """알림을 읽음으로 표시하는 API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False})
    
    try:
        # 현재 정책 개수를 세션에 저장
        user = request.user
        
        if not user.birthyear or not user.birthday:
            return JsonResponse({'success': True})
        
        # 생일에서 월/일 추출
        birthday_month, birthday_day = user.birthday.split('-')
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_day = datetime.now().day
        
        # 나이 계산
        age = current_year - int(user.birthyear)
        if current_month < int(birthday_month) or (current_month == int(birthday_month) and current_day < int(birthday_day)):
            age -= 1
        
        # 최근 일주일 이내 업데이트된 정책 필터링
        one_week_ago = timezone.now() - timedelta(days=7)
        today = timezone.now()
        
        # 조건에 맞는 정책 조회
        matching_policies = Policies.objects.filter(
            updated_at__gte=one_week_ago,
            updated_at__lte=today
        ).filter(
            # 나이 조건: min_age <= 사용자나이 <= max_age 또는 min_age/max_age가 0/null인 경우
            models.Q(
                sprt_trgt_min_age__lte=age,
                sprt_trgt_max_age__gte=age
            ) |
            models.Q(sprt_trgt_min_age=0) |
            models.Q(sprt_trgt_min_age__isnull=True) |
            models.Q(sprt_trgt_max_age=0) |
            models.Q(sprt_trgt_max_age__isnull=True)
        )
        
        # 사용자가 이미 확인하거나 신청한 정책 제외
        excluded_policies = RecommendInterest.objects.filter(
            user=user,
            interest_status__in=['확인', '신청']
        ).values_list('plcy_no', flat=True)
        
        matching_policies = matching_policies.exclude(plcy_no__in=excluded_policies)
        current_count = matching_policies.count()
        
        # 세션에 현재 정책 개수 저장
        request.session['last_checked_notification_count'] = current_count
        print(f"DEBUG: 사용자 {request.user.user_id}의 알림을 읽음으로 표시함 (현재 정책 개수: {current_count})")
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        print(f"DEBUG: 알림 읽음 처리 중 오류: {str(e)}")
        return JsonResponse({'success': False})



