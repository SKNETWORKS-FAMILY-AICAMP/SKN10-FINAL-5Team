import requests
from django.conf import settings
from .models import User, RefreshToken
from .token import (
    create_access_token, create_refresh_token,
    decode_access_token, decode_refresh_token
)
from django.http import HttpResponse
import jwt
from django.shortcuts import redirect
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# 싱글 디바이스 정책 시 RefreshToken DB 삭제 처리
def clear_refresh_token(refresh_token):
    if refresh_token:
        logger.info("싱글 디바이스 정책 - RefreshToken DB 삭제 시도")
        RefreshToken.objects.filter(token=refresh_token).delete()

# 공통 인증 실패 처리 → 쿠키 삭제 + DB 삭제 + 리다이렉트
def handle_auth_failure(refresh_token, request=None):
    clear_refresh_token(refresh_token)
    
    # AJAX 요청인 경우 JSON 응답 반환
    if request and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response = JsonResponse({
            'status': 'redirect',
            'redirect_url': '/user/login/'
        }, status=401)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return False, response, None
    
    # 일반 요청인 경우 리다이렉트
    response = redirect('user:login')
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return False, response, None


# 네이버 REST API 호출해서 사용자 정보(Dict) 조회
def get_naver_user_info(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get("https://openapi.naver.com/v1/nid/me", headers=headers)
    data = response.json()
    if data.get("resultcode") != "00":
        raise Exception("네이버 사용자 정보 조회 실패")
    
    return data["response"]


#  User 테이블에 존재하면 조회, 없으면 생성
def get_or_create_user_from_naver(user_info):
    
    # auth_id + auth_server로 유저 찾기
    # 없다면 새로 생성 (defaults 사용)
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

    # 기존 유저의 프로필 이미지 변경된 경우 업데이트
    if not created:
        new_profile_img = user_info.get("profile_image")
        if user.profile_img != new_profile_img:
            user.profile_img = new_profile_img
            user.save()

    return user

# 액세스 토큰, 리프레시 토큰 발급
def generate_tokens(user_id):
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    return access, refresh


# 액세스 토큰 디코드 -> user_id 반환
def verify_access_token(token):
    return decode_access_token(token)


# 리프레시 토큰 디코드 -> user_id 반환
def verify_refresh_token(token):
    return decode_refresh_token(token)


# 핵심 인증 처리 함수
# 모든 요청에서 이걸 통해 토큰 검증 + 갱신 처리
def verify_and_refresh_tokens(request):
    # 쿠키에서 토큰 가져오기
    access_token = request.COOKIES.get('access_token')
    refresh_token = request.COOKIES.get('refresh_token')

    logger.info(f"토큰 검증 시작 - Path: {request.path}")
    logger.info(f"액세스 토큰 존재: {bool(access_token)}")
    logger.info(f"리프레시 토큰 존재: {bool(refresh_token)}")

    # 홈 화면에서 토큰이 없는 경우 -> 예외처리
    if request.path == '/' and not access_token:
        logger.info("홈 페이지 접근 - 토큰 없음")
        return False, None, None

    # 1. 액세스 토큰 존재 확인
    if not access_token:
        logger.warning("액세스 토큰 없음")
        return handle_auth_failure(refresh_token, request)

    # 2. 액세스 토큰 만료 체크
    try:
        # 액세스 토큰이 유효한 경우
        user_id = verify_access_token(access_token)
        logger.info(f"액세스 토큰 유효 - User ID: {user_id}")

        if not User.objects.filter(user_id=user_id).exists():
            logger.warning(f"유저 존재하지 않음 - User ID: {user_id}")
            return handle_auth_failure(refresh_token, request)

        return True, None, user_id

    except jwt.ExpiredSignatureError as e:
        logger.info(f"액세스 토큰 만료됨: {str(e)}")

        if not refresh_token:
            logger.warning("리프레시 토큰 없음")
            return handle_auth_failure(refresh_token, request)

        try:
            user_id = verify_refresh_token(refresh_token)
            logger.info(f"리프레시 토큰 유효 - User ID: {user_id}")

            if not User.objects.filter(user_id=user_id).exists():
                logger.warning(f"유저 존재하지 않음 - User ID: {user_id} (refresh_token 검증 시)")
                return handle_auth_failure(refresh_token, request)
            
            refresh_token_obj = RefreshToken.objects.filter(
                token=refresh_token,
                user__user_id=user_id
            ).first()

            if not refresh_token_obj:
                logger.warning(f"DB에 리프레시 토큰 없음 - User ID: {user_id}")
                return handle_auth_failure(refresh_token, request)

            new_access_token = create_access_token(user_id)
            logger.info(f"새 액세스 토큰 발급 완료 - User ID: {user_id}")
            logger.info(f"새 액세스 토큰: {new_access_token[:20]}...")

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # 원래 요청의 메서드와 데이터를 유지
                original_method = request.method
                original_data = request.body
                original_content_type = request.content_type
                
                # 새로운 액세스 토큰으로 요청 헤더 설정
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {new_access_token}'
                
                # 원래 요청을 다시 처리
                response = JsonResponse({
                    'status': 'token_refreshed',
                    'message': '토큰이 갱신되었습니다.',
                    'retry_request': True
                })
                response.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax')
                return True, response, user_id
            
            response = redirect(request.path)
            response.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax')
            return True, response, user_id
    
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            logger.error(f"리프레시 토큰 오류: {str(e)}")
            # 리프레시 토큰이 만료되거나 유효하지 않은 경우
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                logger.info("AJAX 요청에서 리프레시 토큰 만료 감지")
                response = JsonResponse({
                    'status': 'redirect',
                    'redirect_url': '/user/login/'
                }, status=401)
                response.delete_cookie('access_token')
                response.delete_cookie('refresh_token')
                clear_refresh_token(refresh_token)
                logger.info("로그인 페이지로 리다이렉트 응답 전송")
                return False, response, None
            logger.info("일반 요청에서 리프레시 토큰 만료 감지")
            return handle_auth_failure(refresh_token, request)

    except jwt.InvalidTokenError as e:
        logger.error(f"액세스 토큰 유효하지 않음: {str(e)}")
        return handle_auth_failure(refresh_token, request)

