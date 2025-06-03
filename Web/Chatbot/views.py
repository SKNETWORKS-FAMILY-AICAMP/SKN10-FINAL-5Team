import os
import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 환경변수 로드
load_dotenv()

# LLM 전역 변수 (앱 시작 시 한 번만 로드)
_rag_chain = None

def get_rag_chain():
    """RAG 체인을 초기화하고 반환하는 함수"""
    global _rag_chain
    if _rag_chain is None:
        try:
            # 벡터 DB 경로 설정 (프로젝트 루트의 data 폴더)
            base_dir = os.path.dirname('../..')
            db_path = os.path.join(base_dir, "data", "vector_db_openai_large_combined")
            
            print(f"벡터 DB 경로: {db_path}")  # 디버깅용
            
            # 임베딩 모델과 벡터 DB 로드
            embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
            vector_db = FAISS.load_local(
                folder_path=db_path,
                embeddings=embedding_model,
                allow_dangerous_deserialization=True
            )
            
            # LLM 초기화
            llm = ChatOpenAI(model="gpt-4o", temperature=0)
            
            # 시스템 프롬프트 정의
            system_prompt = (
                "당신은 한국의 청년 정책에 대한 질문-답변 도우미입니다. "
                "검색된 다음 정보들을 사용하여 질문에 답변하세요. "
                "답을 모르면 모른다고 말하세요. "
                "\n\n"
                "{context}"
            )
            
            # 프롬프트 템플릿 생성
            qa_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    ("human", "{input}"),
                ]
            )
            
            # 리트리버 생성
            retriever = vector_db.as_retriever(search_kwargs={"k": 5})
            
            # 문서 결합 체인 생성
            question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
            
            # 최종 RAG 체인 생성
            _rag_chain = create_retrieval_chain(retriever, question_answer_chain)
            
        except Exception as e:
            print(f"RAG 체인 초기화 오류: {e}")
            _rag_chain = None
    
    return _rag_chain

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

