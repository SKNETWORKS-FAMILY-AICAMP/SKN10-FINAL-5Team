import requests
from datetime import datetime
import jwt
import pytz

from django.conf import settings
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .token import JWT_KEY
from .models import RefreshToken
from .services import (
    get_naver_user_info,
    get_or_create_user_from_naver,
    generate_tokens,
    verify_refresh_token,
    decode_refresh_token,
)

from django.shortcuts import render, redirect

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response


class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "user_nm": user.user_nm,
            "email": user.email,
            "profile_img": user.profile_img or "/static/images/default_profile.png"
        })
    

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
        from django.shortcuts import redirect
        return redirect(url)


# ✅ 네이버 로그인 콜백 처리 (세션 없이 JWT 발급)
class NaverLoginCallbackView(APIView):
    def get(self, request):
        code = request.GET.get("code")
        state = request.GET.get("state")

        # 1. 네이버 토큰 요청
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

        # 2. 사용자 정보 요청
        user_info = get_naver_user_info(access_token)

        # 3. 사용자 조회 또는 생성
        user = get_or_create_user_from_naver(user_info)

        # 4. JWT 발급
        access_token, refresh_token = generate_tokens(user.user_id)

        # 5. 기존 refreshToken 삭제 후 새로 저장
        RefreshToken.objects.filter(user=user).delete()
        now = datetime.now(pytz.timezone("Asia/Seoul"))
        expired_dt = now + JWT_KEY.RANDOM_OF_REFRESH_KEY.value[2]

        RefreshToken.objects.create(
            token=refresh_token,
            expired_dt=expired_dt,
            user=user
        )

        # 6. 응답 처리: accessToken은 JSON, refreshToken은 HttpOnly 쿠키
        response = redirect('chatbot:chatbot')
        response.set_cookie(
            key='refreshToken',
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite='Lax'
        )
        
        # access token을 쿼리 파라미터로 전달
        response['Location'] = f"{response['Location']}?access_token={access_token}"

        return response


# ✅ 토큰 갱신 (refreshToken → accessToken)
class RefreshView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refreshToken')

        if not refresh_token:
            return Response({"error": "Refresh token not provided."}, status=400)

        try:
            user_id = verify_refresh_token(refresh_token)
        except jwt.ExpiredSignatureError:
            return Response({"error": "Expired refresh token."}, status=401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid refresh token."}, status=401)
        except Exception as e:
            return Response({"error": str(e)}, status=401)

        if not RefreshToken.objects.filter(token=refresh_token, user__user_id=user_id).exists():
            return Response({"error": "Refresh token not found in database."}, status=404)

        access_token, _ = generate_tokens(user_id)

        return Response({'accessToken': access_token}, status=200)


# ✅ 로그아웃
class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get("refreshToken")

        if not refresh_token:
            return Response({"error": "Refresh token not provided."}, status=400)

        try:
            user_id = decode_refresh_token(refresh_token)
        except jwt.ExpiredSignatureError:
            return Response({"error": "Expired refresh token."}, status=401)
        except jwt.InvalidTokenError:
            return Response({"error": "Invalid refresh token."}, status=401)

        # DB에서 refreshToken 삭제
        deleted_count, _ = RefreshToken.objects.filter(token=refresh_token, user__user_id=user_id).delete()

        if deleted_count == 0:
            return Response({"error": "Token not found."}, status=404)

        # 쿠키 삭제 후 응답
        response = JsonResponse({"message": "Logged out successfully."})
        response.delete_cookie("refreshToken")

        return response
