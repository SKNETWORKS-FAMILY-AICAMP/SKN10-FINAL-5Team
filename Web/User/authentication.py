# authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from User.token import decode_access_token
from User.models import User

# ✅ 쿠키 기반 JWT 인증 클래스 정의
class CookieJWTAuthentication(BaseAuthentication):
    """
    DRF의 커스텀 인증 클래스.
    요청(request)의 쿠키에 포함된 access_token을 읽어서 JWT를 검증하고,
    해당 사용자 정보를 가져와 인증된 user로 설정하는 역할.
    """
    def authenticate(self, request):
        # access_token을 쿠키에서 꺼낸다
        token = request.COOKIES.get('access_token')

        # 토큰이 없으면 인증 시도 자체를 하지 않음 → DRF가 다음 인증 방식으로 넘어감
        if not token:
            return None

        try:
            # access_token 디코딩 (유효성 검증 포함)
            user_id = decode_access_token(token)
        except Exception:
            # 디코딩 실패(만료, 위조 등) 시 인증 실패 처리 → 401 Unauthorized 응답 발생
            raise AuthenticationFailed('Invalid or expired access token')

        try:
            # 토큰에서 얻은 user_id로 실제 User 인스턴스를 가져옴
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            # 유저가 존재하지 않으면 인증 실패
            raise AuthenticationFailed('No such user')

        # 인증 성공 -> (user 인스턴스, 인증 방식 정보) 튜플 반환
        return (user, None)
    

        



