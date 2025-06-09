import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .service import get_rag_chain
from User.services import verify_and_refresh_tokens
from functools import wraps

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_valid, response, user_id = verify_and_refresh_tokens(request)
        if not is_valid:
            return redirect('user:login')
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
def chatbot_page(request):
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
        
        # RAG 체인 가져오기
        rag_chain = get_rag_chain()
        
        if rag_chain is None:
            return JsonResponse({
                'status': 'error',
                'message': '챗봇 서비스를 사용할 수 없습니다. 관리자에게 문의하세요.'
            }, status=500)
        
        # LLM 질의 응답 수행
        result = rag_chain.invoke({"input": user_message})
        
        return JsonResponse({
            'status': 'success',
            'answer': result['answer'],
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

