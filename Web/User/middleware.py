from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from .services import verify_and_refresh_tokens
from rest_framework.exceptions import AuthenticationFailed
from django.http import HttpResponse, JsonResponse
import logging

# User 모델 가져오기
# 이후 request.user에 User 객체 할당시 사용
User = get_user_model()

logger = logging.getLogger('User.middleware')

class JWTAuthenticationMiddleware:

    # Django middleware는 __init__ 에서 get_response 받아서 저장 → 요청 후 처리를 위해 사용.
    # get_response 저장 → 마지막에 호출
    def __init__(self, get_response):
        # view로 요청 전달할 때 사용되는 함수
        self.get_response = get_response

    def _is_home_page(self, request):
        return request.path == '/'

    def _redirect_to_login(self, request):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            response = JsonResponse({
                'status': 'redirect',
                'redirect_url': '/user/login/'
            }, status=401)
        else:
            response = redirect('user:login')
        
        # 쿠키 삭제
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

    # 미들웨어 본체 -> 모든 요청마다 실행
    def __call__(self, request):
        logger.info('미들웨어 사용됨')
        
        # 공개 페이지 URL 목록
        # 인증 검사 제외 대상
        public_urls = [
            '/user/login/',
            '/user/naver/login/',
            '/user/naver/callback/',
        ]

        # 뷰에서 항상 request.user를 안전하게 사용할 수 있도록 초기값 설정
        request.user = None

        # 공개 페이지는 인증 체크를 하지 않음
        # '/api/policy/'로 시작하는 URL도 인증 검사 제외
        if request.path in public_urls or request.path.startswith('/api/policy/'):
            return self.get_response(request)

        try:
            '''
                # is_valid(토큰 검증 성공 여부)
                - True : Access Token 유효, 만료됐는데 Refresh Token으로 복구 성공
                - False : 인증 실패

                # response(응답 객체)
                - HttpResponse : 새 access_token 발급 시 → redirect or JsonResponse 반환
                - None : 인증 성공(→ 정상적으로 view 진행 가능)

                # user_id(토큰에서 추출한 사용자 user_id)
                - user_id : Access Token or Refresh Token decode 시 복원된 user_id → request.user 설정할 때 사용
                - None : 추출 실패  

            '''
            # access_token + refresh_token 검증
            is_valid, response, user_id = verify_and_refresh_tokens(request)

            # 토큰 갱신이 필요한 경우 (새로운 액세스 토큰 발급)
            if is_valid and response and isinstance(response, str):
                # 새 액세스 토큰을 받은 경우
                new_access_token = response
                
                # AJAX 요청이면 token_refreshed JSON 응답 반환
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    response_obj = JsonResponse({
                        'status': 'token_refreshed',
                        'message': '토큰이 갱신되었습니다.',
                        'retry_request': True
                    })
                else:
                    # 일반 요청이면 redirect로 새 토큰 적용
                    response_obj = redirect(request.path)
                
                response_obj.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax')
                return response_obj

            # 기존 응답 객체가 있는 경우 (이전 로직과의 호환성)
            if response and isinstance(response, (HttpResponse, JsonResponse)):
                return response

            # 인증이 성공했는지 확인
            # 정상 인증 성공 → request.user 설정
            if is_valid and user_id:
                try:
                    request.user = User.objects.get(user_id=user_id)
                except User.DoesNotExist:
                    if not self._is_home_page(request):
                        return self._redirect_to_login(request)
                    
            # 만약 is_valid=False 이거나 user_id=None 인 경우 → 인증 실패
            elif not self._is_home_page(request):
                return self._redirect_to_login(request)

        # verify_and_refresh_tokens() 호출 중에 AuthenticationFailed 예외가 발생한 경우 → 강제 로그인 페이지로 이동.
        except AuthenticationFailed:
            if not self._is_home_page(request):
                return self._redirect_to_login(request)

        # 정상 통과 시 → view로 요청 전달
        return self.get_response(request)



