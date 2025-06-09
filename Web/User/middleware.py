from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from .services import verify_and_refresh_tokens
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()

class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 공개 페이지 URL 목록
        public_urls = [
            '/user/login/',
            '/user/naver/login/',
            '/user/naver/callback/',
        ]

        # 모든 요청에 대해 request.user를 None으로 초기화
        request.user = None

        # 공개 페이지는 인증 체크를 하지 않음
        if request.path in public_urls:
            return self.get_response(request)

        # 챗봇 페이지와 API에 대한 토큰 검증
        if request.path.startswith('/chatbot/'):
            try:
                is_valid, response, user_id = verify_and_refresh_tokens(request)
                
                # 토큰이 갱신된 경우에만 응답 반환
                if response:
                    return response

                if is_valid and user_id:
                    try:
                        request.user = User.objects.get(user_id=user_id)
                    except User.DoesNotExist:
                        return redirect('user:login')
                else:
                    return redirect('user:login')

            except AuthenticationFailed:
                return redirect('user:login')

        # 다른 페이지에 대한 토큰 검증
        try:
            is_valid, response, user_id = verify_and_refresh_tokens(request)
            
            # 토큰이 갱신된 경우에만 응답 반환
            if response:
                return response

            if is_valid and user_id:
                try:
                    request.user = User.objects.get(user_id=user_id)
                except User.DoesNotExist:
                    if request.path != '/':  # 홈 페이지가 아닌 경우에만 로그인으로 리다이렉트
                        return redirect('user:login')
            elif request.path != '/':  # 홈 페이지가 아닌 경우에만 로그인으로 리다이렉트
                return redirect('user:login')

        except AuthenticationFailed:
            if request.path != '/':  # 홈 페이지가 아닌 경우에만 로그인으로 리다이렉트
                return redirect('user:login')

        return self.get_response(request) 