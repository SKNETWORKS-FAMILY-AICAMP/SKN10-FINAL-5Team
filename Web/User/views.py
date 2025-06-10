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

        # 6. 기존 refreshToken 삭제 후 새로 저장(싱글 디바이스 정책 적용ㅍ)
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



