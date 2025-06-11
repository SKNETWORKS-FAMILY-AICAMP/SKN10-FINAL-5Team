import os
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