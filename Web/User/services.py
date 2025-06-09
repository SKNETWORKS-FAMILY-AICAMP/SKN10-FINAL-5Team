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

# 네이버 사용자 정보 요청
def get_naver_user_info(access_token):
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

    if not created:
        new_profile_img = user_info.get("profile_image")
        if user.profile_img != new_profile_img:
            user.profile_img = new_profile_img
            user.save()

    return user

def generate_tokens(user_id):
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    return access, refresh

def verify_access_token(token):
    return decode_access_token(token)

def verify_refresh_token(token):
    return decode_refresh_token(token)

def verify_and_refresh_tokens(request):
    access_token = request.COOKIES.get('access_token')
    refresh_token = request.COOKIES.get('refresh_token')
    
    logger.info(f"토큰 검증 시작 - Path: {request.path}")
    logger.info(f"액세스 토큰 존재: {bool(access_token)}")
    logger.info(f"리프레시 토큰 존재: {bool(refresh_token)}")
    
    if request.path == '/' and not access_token:
        logger.info("홈 페이지 접근 - 토큰 없음")
        return False, None, None
    
    if not access_token:
        logger.warning("액세스 토큰 없음")
        response = redirect('user:login')
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return False, response, None
        
    try:
        user_id = verify_access_token(access_token)
        logger.info(f"액세스 토큰 유효 - User ID: {user_id}")
        
        if not User.objects.filter(user_id=user_id).exists():
            logger.warning(f"유저 존재하지 않음 - User ID: {user_id}")
            response = redirect('user:login')
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return False, response, None
            
        return True, None, user_id
        
    except jwt.ExpiredSignatureError as e:
        logger.info(f"액세스 토큰 만료됨: {str(e)}")
        if not refresh_token:
            logger.warning("리프레시 토큰 없음")
            response = redirect('user:login')
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return False, response, None
            
        try:
            user_id = verify_refresh_token(refresh_token)
            logger.info(f"리프레시 토큰 유효 - User ID: {user_id}")
            
            refresh_token_obj = RefreshToken.objects.filter(
                token=refresh_token,
                user__user_id=user_id
            ).first()
            
            if not refresh_token_obj:
                logger.warning(f"DB에 리프레시 토큰 없음 - User ID: {user_id}")
                response = redirect('user:login')
                response.delete_cookie('access_token')
                response.delete_cookie('refresh_token')
                return False, response, None
                
            new_access_token = create_access_token(user_id)
            logger.info(f"새 액세스 토큰 발급 완료 - User ID: {user_id}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response = JsonResponse({
                    'status': 'token_refreshed',
                    'message': '토큰이 갱신되었습니다.'
                })
                response.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax')
                return True, response, user_id
            
            response = redirect(request.path)
            response.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax')
            return True, response, user_id
            
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            logger.error(f"리프레시 토큰 오류: {str(e)}")
            RefreshToken.objects.filter(token=refresh_token).delete()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response = JsonResponse({
                    'status': 'redirect',
                    'redirect_url': '/user/login/'
                }, status=401)  # 401 상태 코드로 변경
                response.delete_cookie('access_token')
                response.delete_cookie('refresh_token')
                return False, response, None
            
            response = redirect('user:login')
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return False, response, None
            
    except jwt.InvalidTokenError as e:
        logger.error(f"액세스 토큰 유효하지 않음: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            response = JsonResponse({
                'status': 'redirect',
                'redirect_url': '/user/login/'
            }, status=401)  # 401 상태 코드로 변경
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return False, response, None
        
        response = redirect('user:login')
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return False, response, None
