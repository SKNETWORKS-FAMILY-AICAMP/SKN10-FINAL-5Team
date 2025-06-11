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
def handle_auth_failure(refresh_token):
    clear_refresh_token(refresh_token)
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
    #===========================================================================================
    # 홈 화면에서 토큰이 없는 경우 -> 예외처리
    # 홈 페이지 요청인 경우 예외적으로 토큰 없이도 접근 허용(비로그인 접근 허용)
    '''
    그러면 왜 "False, None, None"을 리턴할까?
    미들웨어 / 데코레이터에서 verify_and_refresh_tokens()는 반환값이 True / False에 따라 다음 동작을 결정

    여기서 "False, None, None" 을 리턴하지만 response 리다이렉트는 없음

    → 즉, 미들웨어/데코레이터 쪽에서 response가 None이면 그냥 통과 시킴
    (홈 화면에서 비회원이 접근해도 그냥 정상 화면 보여주게 됨)
    '''
    if request.path == '/' and not access_token:
        logger.info("홈 페이지 접근 - 토큰 없음")
        return False, None, None
    #===========================================================================================
    # 1. 액세스 토큰 존재 확인
    # access_token 없는 경우
    # ex) 정상적인 인증 정보가 없는 상태(로그아웃 후 재접속, 처음 접속 등)
    # 리프레시 토큰 DB에서 삭제, 쿠키 삭제, 로그인 페이지로 이동
    if not access_token:
        logger.warning("액세스 토큰 없음")
        return handle_auth_failure(refresh_token)

    # 2. 액세스 토큰 만료 체크
    try:
        # 액세스 토큰이 유효한 경우(위변조 X, user DB에 존재, 만료되지 않음)
        user_id = verify_access_token(access_token)
        logger.info(f"액세스 토큰 유효 - User ID: {user_id}")

        # 엑세스 토큰은 있는데 해당 user가 DB에 존재하지 않는 경우
        # ex) 사용자 탈퇴 후 브라우저 새로고침 -> 엑세스 토큰은 아직 유효
        # 리프레시 토큰 DB에서 삭제, 쿠키 삭제, 로그인 페이지로 이동
        if not User.objects.filter(user_id=user_id).exists():
            logger.warning(f"유저 존재하지 않음 - User ID: {user_id}")
            return handle_auth_failure(refresh_token)

        '''
        True → 정상 인증됨
        None → 별도 response 필요 없음 → 그대로 view 흐름 진행 가능
        user_id → 이후 미들웨어나 view에서 request.user 등에 할당 가능
        '''
        return True, None, user_id
    #-----------
    # 2-2. 엑세스 토큰 만료 예외가 발생한 경우
    except jwt.ExpiredSignatureError as e:
        logger.info(f"액세스 토큰 만료됨: {str(e)}")

        # 2-3. 리프레시 토큰 존재 확인
        # 리프레시 토큰 없음 -> 재발급 불가 -> 강제 로그아웃
        if not refresh_token:
            logger.warning("리프레시 토큰 없음")
            return handle_auth_failure(refresh_token)

        try:
            # refresh_token이 유효한 경우(만료 안됨, 위변조 안됨)
            user_id = verify_refresh_token(refresh_token)
            logger.info(f"리프레시 토큰 유효 - User ID: {user_id}")

            # 해당 유저가 유저 테이블에 존재하지 않는 경우 강제 로그아웃
            if not User.objects.filter(user_id=user_id).exists():
                logger.warning(f"유저 존재하지 않음 - User ID: {user_id} (refresh_token 검증 시)")
                return handle_auth_failure(refresh_token)
            
            # refresh_token DB 테이블에 존재 여부 확인
            refresh_token_obj = RefreshToken.objects.filter(
                token=refresh_token,
                user__user_id=user_id
            ).first()

            # DB에 리프레시 토큰 없는 경우 강제 로그아웃
            if not refresh_token_obj:
                logger.warning(f"DB에 리프레시 토큰 없음 - User ID: {user_id}")
                return handle_auth_failure(refresh_token)

            # 새 액세스 토큰 발급
            new_access_token = create_access_token(user_id)
            logger.info(f"새 액세스 토큰 발급 완료 - User ID: {user_id}")
            logger.info(f"새 액세스 토큰: {new_access_token[:20]}...")  # 토큰의 일부만 로깅

            '''
            # AJAX 요청 상황
            - 사용자가 채팅 입력 후 JS 코드가 /api/chat/ 로 POST 요청
            - 서버: access_token 만료 → 새 access_token 발급 후 JSON 응답 { status: token_refreshed }
            - 프론트 JS 코드: "아, 토큰 갱신됐구나" → 이후 새 access_token으로 채팅 요청 재전송 → UX 끊김 없이 자연스러움
            '''
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                response = JsonResponse({
                    'status': 'token_refreshed',
                    'message': '토큰이 갱신되었습니다.'
                })
                response.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax')
                return True, response, user_id
            '''
            # 일반 요청 상황 ex
            - 사용자가 /chatbot/ 링크 클릭
            - 서버: access_token 만료 → 새 access_token 발급 후 redirect('/chatbot/')
            - 브라우저: 페이지 새로고침 → 새 access_token 적용 → 정상 페이지 표시됨
            '''
            response = redirect(request.path)
            response.set_cookie('access_token', new_access_token, httponly=True, samesite='Lax')
            return True, response, user_id
    
        # 리프레시 토큰이 유효하지 않은 경우(위변조, 만료)
        # 리프레시 토큰 사용 불가 -> 액세스 토큰 재발급 불가 -> 강제 로그아웃
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
            logger.error(f"리프레시 토큰 오류: {str(e)}")
            return handle_auth_failure(refresh_token)
    #-----------
    # 액세스 토큰 자체가 잘못된 토큰인 경우(위변조)
    # 위변조 시도 등으로 액세스 토큰 디코드 자체가 실패하는 경우
    # 강제 로그아웃 처리
    except jwt.InvalidTokenError as e:
        logger.error(f"액세스 토큰 유효하지 않음: {str(e)}")
        return handle_auth_failure(refresh_token)
