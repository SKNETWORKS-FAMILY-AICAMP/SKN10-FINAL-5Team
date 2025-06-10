import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .service import get_rag_chain
from User.services import verify_and_refresh_tokens
from functools import wraps
from User.models import User

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 미들웨어에서 이미 검증된 request.user를 사용
        if not request.user:
            return redirect('user:login')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
def chatbot_page(request):
    """챗봇 페이지 렌더링"""
    return render(request, 'chatbot/chatbot.html')

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def chat_message(request):
    """챗봇 메시지 처리 API"""
    try:
        # 요청 데이터 파싱
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                'status': 'error',
                'message': '메시지를 입력해주세요.'
            }, status=400)
        
        # RAG 체인 대신 하드코딩된 정책 정보 반환
        hardcoded_response_html = """
        <div style="text-align: left; margin-bottom: 20px;">
            <p style="font-size: 1.1em; color: #333;">다음과 같은 청년 정책을 추천드려요!</p>
            <p style="font-size: 0.9em; color: #666;">다음 정책들을 클릭하시면 자세한 정보를 확인할 수 있어요!</p>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 20px; justify-content: center;">
            <button class="policy-card" data-policy-id="youth-tomorrow-success-project" style="all: unset; cursor: pointer; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; width: 300px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: left; background-color: white;">
                <h3 style="color: #333; font-size: 18px; margin-bottom: 10px;">청년내일채움공제</h3>
                <p style="color: #666; font-size: 14px; line-height: 1.5;">중소기업 취업 청년에게 2년간</p>
                <div style="margin-top: 15px;">
                    <span style="background-color: #e6f7ed; color: #52c41a; padding: 5px 10px; border-radius: 4px; font-size: 12px;">취업지원</span>
                </div>
            </button>
            <button class="policy-card" data-policy-id="youth-jeonse-loan" style="all: unset; cursor: pointer; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; width: 300px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: left; background-color: white;">
                <h3 style="color: #333; font-size: 18px; margin-bottom: 10px;">청년 전세임대주택</h3>
                <p style="color: #666; font-size: 14px; line-height: 1.5;">만 19~39세 청년에게 시중 시세</p>
                <div style="margin-top: 15px;">
                    <span style="background-color: #e6f7ed; color: #52c41a; padding: 5px 10px; border-radius: 4px; font-size: 12px;">주거지원</span>
                </div>
            </button>
            <button class="policy-card" data-policy-id="youth-startup-academy" style="all: unset; cursor: pointer; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; width: 300px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: left; background-color: white;">
                <h3 style="color: #333; font-size: 18px; margin-bottom: 10px;">청년창업사관학교</h3>
                <p style="color: #666; font-size: 14px; line-height: 1.5;">예비창업자에게 9개월간 집중</p>
                <div style="margin-top: 15px;">
                    <span style="background-color: #e6f7ed; color: #52c41a; padding: 5px 10px; border-radius: 4px; font-size: 12px;">창업지원</span>
                </div>
            </button>
        </div>
        """
        
        return JsonResponse({
            'status': 'success',
            'answer': hardcoded_response_html,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '잘못된 요청 형식입니다.'
        }, status=400)
        
    except Exception as e:
        print(f"챗봇 응답 오류: {e}")
        return JsonResponse({
            'status': 'error',
            'message': '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def reset_session(request):
    """챗봇 세션 초기화 API"""
    try:
        # 세션 데이터 초기화 (필요한 경우)
        if hasattr(request, 'session'):
            # 챗봇 관련 세션 데이터만 초기화
            keys_to_remove = [key for key in request.session.keys() if key.startswith('chatbot_')]
            for key in keys_to_remove:
                del request.session[key]
            request.session.modified = True
        
        return JsonResponse({
            'status': 'success',
            'message': '세션이 초기화되었습니다.'
        })
        
    except Exception as e:
        print(f"세션 초기화 오류: {e}")
        return JsonResponse({
            'status': 'error',
            'message': '세션 초기화 중 오류가 발생했습니다.'
        }, status=500)