# JWT 인코딩/디코딩을 위한 라이브러리
import jwt 

# 토큰 만료시간 설정을 위한 날짜/시간 모듈
import datetime 

# 열거형 클래스를 위한 enum 모듈
import enum 

# 인증 실패 시 사용할 DRF 예외 클래스
from rest_framework.exceptions import AuthenticationFailed

import pytz
from django.conf import settings


# 🔐 JWT에서 사용할 키, 만료시간, 알고리즘 등을 열거형(enum)으로 관리
# 토큰 생성 및 검증에 필요한 정보를 Enum 클래스로 정의
class JWT_KEY(enum.Enum):
    # access token 설정: (값ID, 시크릿키, 만료기간, 알고리즘, 설명)
    RANDOM_OF_ACCESS_KEY = (
        enum.auto(),          # 내부 식별 ID (자동 증가 정수, 사용 X)
        settings.ACCESS_SECRET_KEY,  # 환경 변수에서 가져옴
        datetime.timedelta(minutes=15), # 15분 동안 유효
        #datetime.timedelta(seconds=30),
        'HS256',              # HMAC SHA256 해시 알고리즘
        'Access Token'     # 설명 (기술적 기능 없음)
    )

    # refresh token 설정: 7일 동안 유효
    RANDOM_OF_REFRESH_KEY = (
        enum.auto(), 
        settings.REFRESH_SECRET_KEY,  # 환경 변수에서 가져옴
        datetime.timedelta(days=7),  
        #datetime.timedelta(minutes=1), 
        'HS256', 
        'Refresh Token'
    )

# 내부 함수: JWT 토큰을 생성해주는 핵심 함수
# id는 사용자 고유 ID, key는 JWT_KEY Enum 객체
# 반환값은 JWT 문자열 (Header.Payload.Signature 형태)
def __create_token(id: int, key: JWT_KEY) -> str:
    """
    사용자의 ID와 설정된 JWT_KEY 정보를 기반으로 JWT 토큰을 생성한다.
    """
    seoul_tz = pytz.timezone("Asia/Seoul")
    now = datetime.datetime.now(seoul_tz)

    payload = {
        'user_id': id,
        'exp': now + key.value[2],
        'iat': now
    }

    # 시크릿 키 및 알고리즘 추출 (Enum에서 꺼냄)
    random_key = key.value[1]
    alg = key.value[3]

    # PyJWT를 사용하여 JWT 문자열 생성
    return jwt.encode(payload, random_key, algorithm=alg)  # Header + Payload 서명 → JWT 문자열 반환


# 외부에서 사용할 함수: access token 생성기
# 사용자의 ID를 받아 access token을 반환함
# 내부적으로 __create_token() 호출

def create_access_token(id):
    return __create_token(id, JWT_KEY.RANDOM_OF_ACCESS_KEY)


# 외부에서 사용할 함수: refresh token 생성기
# 사용자의 ID를 받아 refresh token을 반환함

def create_refresh_token(id):
    return __create_token(id, JWT_KEY.RANDOM_OF_REFRESH_KEY)


# 내부 함수: 토큰을 디코딩하고 payload의 user_id를 추출
# 토큰이 유효하지 않으면 예외 발생

def __decode_token(token, key):
    try:
        alg = key.value[3]        # 해시 알고리즘
        random_key = key.value[1] # 서명 검증용 시크릿 키

        # jwt.decode(): 토큰의 유효성 검증 및 디코딩 수행
        payload = jwt.decode(token, random_key, algorithms=alg)

        # payload에서 사용자 ID를 반환 (주체 식별)
        return payload['user_id']

    # 토큰이 만료되었거나, 위조되어 유효하지 않은 경우
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        # JWT 관련 예외는 그대로 위쪽 서비스 레이어나 미들웨어에서 감지에서 처리하도록 유도
        raise e
    except Exception as e:
        # 기타 예외는 AuthenticationFailed로 변환
        raise AuthenticationFailed(e)


# access token 디코딩 함수 (API 인증 시 사용)
def decode_access_token(token):
    return __decode_token(token, JWT_KEY.RANDOM_OF_ACCESS_KEY)


# refresh token 디코딩 함수 (access token 재발급 시 사용)
def decode_refresh_token(token):
    return __decode_token(token, JWT_KEY.RANDOM_OF_REFRESH_KEY)