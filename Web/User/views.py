import requests
from datetime import datetime
import jwt
import pytz

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout  
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .token import JWT_KEY

from .models import RefreshToken
from .services import *


# ✅ 로그인 화면 렌더링
def login_view(request):
    return render(request, 'user/login.html')


# ✅ 네이버 로그인 리다이렉트
class NaverLoginRedirectView(APIView):
    def get(self, request):
        url = (
            f"https://nid.naver.com/oauth2.0/authorize?"
            f"response_type=code&client_id={settings.NAVER_CLIENT_ID}"
            f"&redirect_uri={settings.NAVER_REDIRECT_URI}&state=random_state"
        )
        return redirect(url)


# ✅ 네이버 로그인 콜백 처리
class NaverLoginCallbackView(APIView):
    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")

        # 1. 토큰 요청
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

        # 2. 유저 정보 요청
        user_info = get_naver_user_info(access_token)

        # 3. 사용자 조회 or 생성
        user = get_or_create_user_from_naver(user_info)

        # ✅ Django 세션 로그인 처리 (템플릿에서 인식되도록)
        login(request, user)

        # 4. JWT 생성
        access_token, refresh_token = generate_tokens(user.user_id)

        # 5. 기존 리프레시 토큰 삭제 후 새로 저장
        RefreshToken.objects.filter(user=user).delete()

        seoul_tz = pytz.timezone("Asia/Seoul")
        now = datetime.now(seoul_tz)
        expired_dt = now + JWT_KEY.RANDOM_OF_REFRESH_KEY.value[2]

        RefreshToken.objects.create(
            token=refresh_token,
            expired_dt=expired_dt,
            user=user
        )

        # 6. 쿠키 저장 후 챗봇 페이지로 리디렉션
        # 수정 필요할듯
        response = redirect('chatbot:chatbot')  
        response.set_cookie(key='refreshToken', value=refresh_token, httponly=True)
        response.set_cookie(key='accessToken', value=access_token, httponly=False)

        return response


class RefreshView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refreshToken')

        if not refresh_token:
            return Response({"error": "Refresh token not provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = verify_refresh_token(refresh_token)
        except jwt.ExpiredSignatureError:
            return Response({"error": "Expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        # ✅ 리프레시 토큰이 DB에 존재하는지 검증
        from .models import RefreshToken
        if not RefreshToken.objects.filter(token=refresh_token, user__user_id=user_id).exists():
            return Response({"error": "Refresh token not found in database."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ 새 accessToken 발급
        access_token, _ = generate_tokens(user_id)

        return Response({'token': access_token})


# ✅ 로그아웃
class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get("refreshToken")

        if not refresh_token:
            return Response({"error": "Refresh token not provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = decode_refresh_token(refresh_token)
        except jwt.ExpiredSignatureError:
            return Response({"error": "Expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        # ✅ 세션 로그아웃 처리 (Django에 로그아웃 알림)
        logout(request)

        # DB에서 리프레시 토큰 삭제
        deleted_count, _ = RefreshToken.objects.filter(token=refresh_token, user__user_id=user_id).delete()

        if deleted_count == 0:
            return Response({"error": "Token not found."}, status=status.HTTP_404_NOT_FOUND)

        # ✅ 쿠키 삭제 후 홈으로 리디렉션
        response = redirect('home:home')
        
        response.delete_cookie("refreshToken")
        response.delete_cookie("accessToken")

        return response
    

