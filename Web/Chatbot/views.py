import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .service import get_rag_chain

from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy

@login_required(login_url=reverse_lazy('user:login'))
def chatbot(request):
    """챗봇 페이지 렌더링"""
    return render(request, 'chatbot/chatbot.html')

@csrf_exempt
@require_http_methods(["POST"])
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
        
        # 관련 정책 문서 제목 추출
        related_policies = []
        for doc in result.get('context', []):
            policy_name = doc.metadata.get("정책명", "제목 없음")
            if policy_name not in related_policies:
                related_policies.append(policy_name)
        
        return JsonResponse({
            'status': 'success',
            'answer': result['answer'],
            'related_policies': related_policies
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

