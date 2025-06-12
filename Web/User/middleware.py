from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from .services import verify_and_refresh_tokens
from rest_framework.exceptions import AuthenticationFailed
from django.http import HttpResponse, JsonResponse

# User 모델 가져오기
# 이후 request.user에 User 객체 할당시 사용
User = get_user_model()

class JWTAuthenticationMiddleware:

    # Django middleware는 __init__ 에서 get_response 받아서 저장 → 요청 후 처리를 위해 사용.
    # get_response 저장 → 마지막에 호출
    def __init__(self, get_response):
        self.get_response = get_response

    # 미들웨어 본체 -> 모든 요청마다 실행
    def __call__(self, request):
        # 공개 페이지 URL 목록
        # 인증 검사 제외 대상
        public_urls = [
            '/user/login/',
            '/user/naver/login/',
            '/user/naver/callback/',
        ]
        print('hello world')
        
        # 뷰에서 항상 request.user를 안전하게 사용할 수 있도록 초기값 설정
        request.user = None

        # 공개 페이지는 인증 체크를 하지 않음
        if request.path in public_urls:
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
            is_valid, response, user_id = verify_and_refresh_tokens(request)

            # 토큰 갱신이 필요한 경우 (새로운 액세스 토큰 발급)
            if response and isinstance(response, (HttpResponse, JsonResponse)):
                return response

            # 인증이 성공했는지 확인
            if is_valid and user_id:
                try:
                    request.user = User.objects.get(user_id=user_id)
                except User.DoesNotExist:
                    if request.path != '/':  # 홈 페이지가 아닌 경우에만 로그인으로 리다이렉트
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'status': 'redirect',
                                'redirect_url': '/user/login/'
                            }, status=401)
                        return redirect('user:login')
                    
            # 만약 is_valid=False 이거나 user_id=None 인 경우 → 인증 실패
            elif request.path != '/':  # 홈 페이지가 아닌 경우에만 로그인으로 리다이렉트
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'redirect',
                        'redirect_url': '/user/login/'
                    }, status=401)
                return redirect('user:login')

        # verify_and_refresh_tokens() 호출 중에 AuthenticationFailed 예외가 발생한 경우 → 강제 로그인 페이지로 이동.
        except AuthenticationFailed:
            if request.path != '/':  # 홈 페이지가 아닌 경우에만 로그인으로 리다이렉트
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'redirect',
                        'redirect_url': '/user/login/'
                    }, status=401)
                return redirect('user:login')

        # 정상 통과 시 → view로 요청 전달
        return self.get_response(request)



