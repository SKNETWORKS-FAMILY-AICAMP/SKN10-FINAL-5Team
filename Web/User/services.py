import requests
from django.conf import settings
from .models import User
from .token import (
    create_access_token, create_refresh_token,
    decode_access_token, decode_refresh_token
)

# 네이버 사용자 정보 요청
def get_naver_user_info(access_token):
    """
    네이버 access_token을 이용하여 사용자 정보를 요청하는 함수.
    실패 시 예외를 발생시키고, 성공 시 사용자 정보를 반환함.
    """
    # 인증 헤더 설정
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get("https://openapi.naver.com/v1/nid/me", headers=headers)
    data = response.json()
    if data.get("resultcode") != "00":
        raise Exception("네이버 사용자 정보 조회 실패")
    
    return data["response"]

# 사용자 DB 조회 or 생성
def get_or_create_user_from_naver(user_info):
    """
    네이버 사용자 정보를 바탕으로 User 모델에서 해당 유저를 조회하거나 생성한다.
    """
    user, created = User.objects.get_or_create(
        auth_id=user_info["id"],
        auth_server="naver",
        defaults={
            "user_nm": user_info.get("name"),
            "email": user_info.get("email"),
            "profile_img": user_info.get("profile_image"),
            "birthyear": user_info.get("birthyear"),
            "birthday": user_info.get("birthday"),
            "gender": user_info.get("gender"),
        }
    )

    # 이미 존재하는 유저인데 프로필 이미지가 달라진 경우 → 업데이트
    if not created:
        new_profile_img = user_info.get("profile_image")
        if user.profile_img != new_profile_img:
            user.profile_img = new_profile_img
            user.save()

    return user

def generate_tokens(user_id):
    """
    ✅ [변경 이유]
    - access/refresh 토큰을 동시에 발급하는 로직을 하나의 의미 단위로 캡슐화
    - 뷰에서 각각의 함수를 호출하는 중복 제거
    - 추후 access만 발급하거나 구조 변경 시에도 이 함수만 수정하면 됨
    """
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    return access, refresh


def verify_access_token(token):
    """
    ✅ [변경 이유]
    - access token 검증을 서비스 함수로 분리
    - 예외처리, 로깅, 사용 중지된 토큰 체크 등의 로직 추가를 위한 구조 확보
    - 뷰는 단순히 인증 요청만 하고, 검증은 이 함수가 책임지도록 설계
    """
    return decode_access_token(token)


def verify_refresh_token(token):
    """
    ✅ [변경 이유]
    - refresh token 검증도 별도 함수로 분리
    - 향후 리프레시 토큰 재사용 방지, 만료 로그 기록, 사용자 강제 로그아웃 등 정책 적용 가능
    """
    return decode_refresh_token(token)

