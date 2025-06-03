# 커스텀 예외 핸들러
# 예외가 발생했을 때, 최종적으로 어떤 HTTP 응답으로 바꿔서 클라이언트에게 줄 것인가
# 발생된 예외를 HTTP 응답(Response)으로 바꾸는 책임
# status_code, json 형식, 응답 형태의 통일성 등을 조절
# 필요 시 DRF의 기본 처리 로직(exception_handler) 호출 가능

from rest_framework.views import exception_handler  # DRF 기본 예외 처리기 import
from rest_framework.response import Response        # JSON 응답 반환용
from .exceptions import CustomRegisterException     # 커스텀 회원가입 예외 클래스 import

# ✅ DRF의 예외 처리 로직을 커스터마이징하는 함수
def status_code_handler(exc, context):

    # ✅ 회원가입에서 발생한 커스텀 예외 처리
    if isinstance(exc, CustomRegisterException):
        # 예외에 담긴 message와 status_code로 응답 생성
        return Response(exc.detail, status=exc.status_code)

    # 기본 DRF 예외 처리기 호출 (ValidationError, AuthenticationFailed 등 처리됨)
    response = exception_handler(exc, context)
    
    # ✅ 기본 예외 응답이 존재할 경우: 상태 코드를 사용자 정의로 변환
    if response is not None:
        if 400 <= response.status_code < 500:
            response.status_code = 444  # 클라이언트 오류 → 444
        elif response.status_code >= 500:
            response.status_code = 555  # 서버 오류 → 555
        else:
            response.status_code = 777  # 기타 예외 → 777

    # 최종 응답 반환
    return response
