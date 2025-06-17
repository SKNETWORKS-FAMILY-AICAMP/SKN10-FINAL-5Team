import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .service import get_rag_chain
from User.services import verify_and_refresh_tokens
from functools import wraps
from User.models import User
from .models import ChatSession, Message
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.utils import timezone

# 챗봇 페이지 렌더링
def chatbot_view(request):
    return render(request, 'chatbot/chatbot.html')

# 현재 로그인한 사용자의 챗봇 세션 리스트 반환
def session_list(request):
    # 디버깅
    print("현재 사용자:", request.user)
    print("인증 여부:", request.user.is_authenticated)
    
    sessions = ChatSession.objects.filter(user=request.user).order_by('-create_dt')
    print("조회된 세션 수:", sessions.count())
    
    session_list = []
    for session in sessions:
        # create_dt를 한국 시간으로 변환
        local_time = timezone.localtime(session.create_dt)
        session_list.append({
            'id': session.session_id,
            'name': session.session_nm,
            'created_at': local_time.strftime('%Y-%m-%d %H:%M')
        })
    print("반환할 데이터:", session_list)

    return JsonResponse({'sessions': session_list})

# 특정 세션의 메시지 리스트 반환
def session_detail(request, session_id):
    try:
        session = ChatSession.objects.get(session_id=session_id, user=request.user)
        messages = Message.objects.filter(session=session).order_by('create_dt', 'msg_id')
        
        message_list = []
        for message in messages:
            # create_dt를 한국 시간으로 변환
            local_time = timezone.localtime(message.create_dt)
            message_list.append({
                'sender': message.sender,
                'content': message.content,
                'created_at': local_time.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({
            'session': {
                'id': session.session_id,
                'name': session.session_nm,
                'created_at': timezone.localtime(session.create_dt).strftime('%Y-%m-%d %H:%M')
            },
            'messages': message_list
        })
    except ChatSession.DoesNotExist:
        return JsonResponse({'error': '세션을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        print(f"세션 상세 조회 오류: {e}")
        return JsonResponse({
            'status': 'error',
            'message': '세션 상세 정보를 불러오는데 실패했습니다.'
        }, status=500)

# 메시지 전송 및 응답 처리
@csrf_exempt
def send_message(request):
    if request.method == 'POST':
        try:
            # 클라이언트에서 전달된 JSON 문자열을 Python 딕셔너리로 변환
            data = json.loads(request.body)
            # 메시지 내용 추출
            message = data.get('message', '').strip()
            # 세션 ID 추출
            session_id = data.get('session_id')
            
            # 메시지가 비어있으면 세션 생성 및 메시지 저장을 하지 않음
            if not message:
                return JsonResponse({'error': '메시지가 비어있습니다. 세션이 생성되지 않았습니다.'}, status=400)
            
            # 세션 ID가 있으면 기존 세션 사용, 없으면 새 세션 생성
            if session_id:
                try:
                    session = ChatSession.objects.get(session_id=session_id, user=request.user)
                except ChatSession.DoesNotExist:
                    return JsonResponse({'error': '세션을 찾을 수 없습니다.'}, status=404)
            else:
                # 새 세션 생성 시 첫 번째 질문을 세션 제목으로 사용
                current_time = timezone.localtime(timezone.now())
                session_name = message if message else f"대화 {current_time.strftime('%Y-%m-%d %H:%M')}"
                session = ChatSession.objects.create(
                    user=request.user,
                    session_nm=session_name
                )
            
            # 사용자 메시지 저장
            user_message = Message.objects.create(
                session=session,
                sender='user',
                content=message,
                create_dt=timezone.localtime(timezone.now())
            )
            
            # 챗봇 응답 생성 (실제 구현 필요)
            bot_response = "안녕하세요! 청년 정책 가이드 챗봇입니다."
            
            # 챗봇 메시지 저장
            bot_message = Message.objects.create(
                session=session,
                sender='chatbot',
                content=bot_response,
                create_dt=timezone.localtime(timezone.now())
            )
            
            return JsonResponse({
                'status': 'success',
                'session_id': session.session_id,
                'messages': [
                    {
                        'sender': 'user',
                        'content': message,
                        'created_at': timezone.localtime(user_message.create_dt).strftime('%Y-%m-%d %H:%M')
                    },
                    {
                        'sender': 'chatbot',
                        'content': bot_response,
                        'created_at': timezone.localtime(bot_message.create_dt).strftime('%Y-%m-%d %H:%M')
                    }
                ]
            })
        except Exception as e:
            print(f"메시지 처리 중 오류 발생: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)