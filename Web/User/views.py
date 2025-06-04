import requests
from datetime import datetime, timedelta
import jwt

from django.conf import settings
from django.shortcuts import render, redirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

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

        # 4. JWT 생성
        access_token, refresh_token = generate_tokens(user.user_id)

        # ✅ 5. 기존 RefreshToken 삭제 → 새로 저장
        RefreshToken.objects.filter(user=user).delete()
   
        RefreshToken.objects.create(
            token=refresh_token,
            expired_dt=datetime.utcnow() + timedelta(days=7),
            user=user
        )

        # 6. 응답 쿠키 설정
        response = Response()
        response.set_cookie(key='refreshToken', value=refresh_token, httponly=True)
        response.data = {'token': access_token}
        
        return response
    

class RefreshView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refreshToken')

        user_id = verify_refresh_token(refresh_token)
        access_token, _ = generate_tokens(user_id)

        return Response({'token': access_token})
    

class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get("refreshToken")

        if not refresh_token:
            return Response({"error": "Refresh token not provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = jwt.decode(refresh_token, settings.REFRESH_SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
        except jwt.ExpiredSignatureError:
            return Response({"error": "Expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        deleted_count, _ = RefreshToken.objects.filter(token=refresh_token, user__user_id=user_id).delete()

        if deleted_count == 0:
            return Response({"error": "Token not found."}, status=status.HTTP_404_NOT_FOUND)

        response = Response({"message": "Logout successful. Refresh token deleted."}, status=status.HTTP_200_OK)
        response.delete_cookie("refreshToken")
        
        return response
