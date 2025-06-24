import json
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Max, Q
from .service import graph
from User.services import verify_and_refresh_tokens
from functools import wraps
from User.models import User
from .models import ChatSession, Message, SearchHistory, RecommendInterest
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import difflib
from Home.models import Policies

logger = logging.getLogger(__name__)

# 챗봇 페이지 렌더링
def chatbot_view(request):
    return render(request, 'chatbot/chatbot.html')

# 현재 로그인한 사용자의 챗봇 세션 리스트 반환
def session_list(request):

    print("현재 사용자:", request.user)
    print("인증 여부:", request.user.is_authenticated)
    
    # 마지막 메시지의 생성일자를 기준으로 세션을 정렬
    sessions = ChatSession.objects.filter(user=request.user).annotate(
        last_message_time=Max('message__create_dt')
    ).order_by('-last_message_time', '-create_dt')
    
    print("조회된 세션 수:", sessions.count())
    
    session_list = []
    for session in sessions:
        # 마지막 메시지 시간이 있으면 그것을 사용, 없으면 세션 생성 시간 사용
        display_time = session.last_message_time if session.last_message_time else session.create_dt
        local_time = timezone.localtime(display_time)
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
                'id': message.msg_id,
                'sender': message.sender,
                'content': message.content,
                'sql_result': message.sql_result,
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

# 채팅 기록 검색 API
@csrf_exempt
def search_chat_history(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '').strip()
            
            if not query:
                return JsonResponse({
                    'status': 'success',
                    'results': []
                })
            
            # 검색 기록 저장 (1분 이내 동일 쿼리 중복 저장 방지)
            if request.user.is_authenticated:
                now = timezone.now()
                recent_history = SearchHistory.objects.filter(
                    user=request.user,
                    query=query,
                    search_dt__gte=now - timedelta(minutes=1)
                ).exists()
                if not recent_history:
                    SearchHistory.objects.create(
                        user=request.user,
                        query=query
                    )
            
            # 현재 사용자의 세션들에서 검색
            # 세션 제목과 메시지 내용에서 검색
            sessions = ChatSession.objects.filter(
                user=request.user
            ).filter(
                Q(session_nm__icontains=query) |  # 세션 제목에서 검색
                Q(message__content__icontains=query)  # 메시지 내용에서 검색
            ).distinct()
            
            results = []
            for session in sessions:
                # 해당 세션에서 검색어가 포함된 메시지들 찾기
                matching_messages = Message.objects.filter(
                    session=session,
                    content__icontains=query
                ).order_by('create_dt')
                
                for message in matching_messages:
                    # 메시지 내용에서 검색어 주변 텍스트 추출 (최대 100자)
                    content = message.content
                    query_index = content.lower().find(query.lower())
                    
                    if query_index != -1:
                        # 검색어 주변 50자씩 추출
                        start = max(0, query_index - 50)
                        end = min(len(content), query_index + len(query) + 50)
                        
                        # 문장 단위로 자르기
                        if start > 0:
                            start = content.find(' ', start) + 1
                        if end < len(content):
                            end = content.rfind(' ', start, end)
                            if end == -1:
                                end = len(content)
                        
                        excerpt = content[start:end].strip()
                        if len(excerpt) > 100:
                            excerpt = excerpt[:97] + '...'
                        
                        # 세션의 마지막 메시지 시간 가져오기
                        last_message_time = Message.objects.filter(session=session).aggregate(
                            Max('create_dt')
                        )['create_dt__max']
                        
                        local_time = timezone.localtime(last_message_time) if last_message_time else timezone.localtime(session.create_dt)
                        
                        results.append({
                            'session_id': session.session_id,
                            'session_name': session.session_nm,
                            'session_date': local_time.strftime('%Y-%m-%d %H:%M'),
                            'message_id': message.msg_id,
                            'message_content': excerpt,
                            'search_term': query
                        })
            
            # 결과를 세션별로 그룹화하고 최신 순으로 정렬
            unique_results = []
            seen_combinations = set()
            
            for result in results:
                key = (result['session_id'], result['message_id'])
                if key not in seen_combinations:
                    seen_combinations.add(key)
                    unique_results.append(result)
            
            # 세션 날짜 기준으로 내림차순 정렬
            unique_results.sort(key=lambda x: x['session_date'], reverse=True)
            
            return JsonResponse({
                'status': 'success',
                'results': unique_results[:20]  # 최대 20개 결과만 반환
            })
            
        except Exception as e:
            print(f"검색 중 오류 발생: {e}")
            return JsonResponse({
                'status': 'error',
                'message': '검색 중 오류가 발생했습니다.'
            }, status=500)
    
    return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

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
            
            # 챗봇 응답 생성
            try:
                logger.info(f"사용자 메시지 처리 시작: {user_message.content}")
                
                # LangGraph의 invoke 메서드 호출 - GraphState 형태로 반환됨
                # HumanMessage 객체로 감싸서 전달
                from langchain_core.messages import HumanMessage
                
                graph_result = graph.invoke({
                    "messages": [HumanMessage(content=user_message.content)],
                    "query": user_message.content
                })
                
                logger.info(f"그래프 결과 타입: {type(graph_result)}")
                logger.info(f"그래프 결과 키들: {graph_result.keys() if isinstance(graph_result, dict) else 'Not a dict'}")
                
                # GraphState에서 final_response 추출
                if isinstance(graph_result, dict):
                    if 'final_response' in graph_result and graph_result['final_response']:
                        bot_response = graph_result['final_response']
                        logger.info("final_response에서 응답 추출 성공")
                    elif 'error' in graph_result:
                        bot_response = graph_result['error']
                        logger.info("error 필드에서 응답 추출")
                    elif 'messages' in graph_result and graph_result['messages']:
                        # 마지막 AI 메시지에서 내용 추출
                        last_message = graph_result['messages'][-1]
                        bot_response = last_message.content if hasattr(last_message, 'content') else str(last_message)
                        logger.info("messages에서 응답 추출")
                    else:
                        bot_response = "죄송합니다. 응답을 생성할 수 없습니다."
                        logger.warning("그래프 결과에서 응답을 찾을 수 없음")
                else:
                    # 그래프 결과가 문자열인 경우 (이전 버전 호환성)
                    bot_response = str(graph_result)
                    logger.info("그래프 결과를 문자열로 변환")
                    
            except Exception as graph_error:
                logger.error(f"그래프 처리 중 오류: {graph_error}", exc_info=True)
                bot_response = f"죄송합니다. 요청을 처리하는 중 오류가 발생했습니다: {str(graph_error)}"
            
            # 챗봇 메시지 저장
            # sql_result에서 필요한 필드만 필터링
            filtered_sql_result = None
            if isinstance(graph_result, dict) and 'sql_result' in graph_result and graph_result['sql_result']:
                filtered_sql_result = []
                for policy in graph_result['sql_result']:
                    filtered_policy = {
                        'plcy_no': policy.get('plcy_no'),
                        'plcy_nm': policy.get('plcy_nm'),
                        'plcy_expln_cn': policy.get('plcy_expln_cn'),
                        'lclsf_nm': policy.get('lclsf_nm'),
                        'mclsf_nm': policy.get('mclsf_nm'),
                        'zip_cd': policy.get('zip_cd'),
                        'inq_cnt': policy.get('inq_cnt', 0)
                    }
                    filtered_sql_result.append(filtered_policy)
            
            bot_message = Message.objects.create(
                session=session,
                sender='chatbot',
                content=bot_response,
                sql_result=graph_result['selected_policies'],
                create_dt=timezone.localtime(timezone.now())
            )
            
            # LLM 추천 정책을 관심(추천)으로 저장
            if request.user.is_authenticated and filtered_sql_result:
                for policy_data in filtered_sql_result:
                    plcy_no = policy_data.get('plcy_no')
                    if plcy_no:
                        try:
                            policy_obj = Policies.objects.get(plcy_no=plcy_no)
                            RecommendInterest.objects.get_or_create(
                                user=request.user,
                                plcy_no=policy_obj,
                                interest_status='추천'
                            )
                        except Policies.DoesNotExist:
                            pass  # 정책이 DB에 없으면 무시
            
            return JsonResponse({
                'status': 'success',
                'session_id': session.session_id,
                'messages': [
                    {
                        'id': user_message.msg_id,
                        'sender': 'user',
                        'content': message,
                        'created_at': timezone.localtime(user_message.create_dt).strftime('%Y-%m-%d %H:%M')
                    },
                    {
                        'id': bot_message.msg_id,
                        'sender': 'chatbot',
                        'content': bot_response,
                        'sql_result': graph_result['selected_policies'],
                        'created_at': timezone.localtime(bot_message.create_dt).strftime('%Y-%m-%d %H:%M')
                    }
                ]
            })
        except Exception as e:
            print(f"메시지 처리 중 오류 발생: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': '잘못된 요청입니다.'}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def save_interest(request):
    """
    정책 카드 클릭(모달 오픈) 시 '확인', 신청/이동 버튼 클릭 시 '신청'으로 관심도 저장
    body: { plcy_no: string, interest_status: '확인' | '신청' }
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '로그인 필요'}, status=401)
    try:
        data = json.loads(request.body)
        plcy_no = data.get('plcy_no')
        interest_status = data.get('interest_status')
        if not plcy_no or interest_status not in ['확인', '신청']:
            return JsonResponse({'success': False, 'error': '잘못된 요청'}, status=400)
        policy = Policies.objects.get(plcy_no=plcy_no)
        # 이미 동일 정책+유저+상태로 저장된 경우 중복 저장 방지
        obj, created = RecommendInterest.objects.get_or_create(
            user=request.user,
            plcy_no=policy,
            interest_status=interest_status
        )
        return JsonResponse({'success': True, 'created': created})
    except Policies.DoesNotExist:
        return JsonResponse({'success': False, 'error': '정책 없음'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)