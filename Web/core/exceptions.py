# 커스텀 예외 클래스
# 예외가 발생했다는 사실"을 알리고, 어떤 상태와 메시지를 담을지 정의
# 어떤 조건에서 예외를 발생시킬지 정의
# 예외에 포함될 정보(status_code, message, code)를 담음

from rest_framework.exceptions import APIException  # DRF 기본 예외 클래스 import

# ✅ 회원가입 과정에서 특정 필드 누락 시 사용할 커스텀 예외 클래스
class CustomRegisterException(APIException):
    def __init__(self, status_code, detail):
        # 예외에 적용할 HTTP 상태 코드 (ex: 401, 402, 403 등)
        self.status_code = status_code

        # 클라이언트에게 전달할 에러 메시지를 담은 응답 본문
        self.detail = {'message': detail}

