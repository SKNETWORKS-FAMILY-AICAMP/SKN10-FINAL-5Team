import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 환경변수 로드
load_dotenv()

# 벡터 DB 로드
db_path = "../Data/vector_db_openai_large_combined"

embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
vector_db = FAISS.load_local(
    folder_path=db_path,
    embeddings=embedding_model,
    allow_dangerous_deserialization=True
)

# LLM 초기화 (GPT-4 또는 GPT-3.5 가능)
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

# 리트리버 생성 (더 많은 문서 검색을 위해 k 값 증가)
retriever = vector_db.as_retriever(search_kwargs={"k": 5})

# 문서 결합 체인 생성
question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

# 최종 RAG 체인 생성 (최신 API 사용)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

# 사용자 질문
user_question = "서울에 사는 26살 청년인데 주거비를 지원해주는 정책이 뭐가 있을까?"

# 질의 응답 수행
result = rag_chain.invoke({"input": user_question})

# 출력
print("🧑 사용자 질문:")
print(user_question)
print("\n🤖 챗봇 답변:")
print(result['answer'])

print("\n📚 관련 정책 문서 제목:")
for doc in result['context']:
    print("-", doc.metadata.get("정책명", "제목 없음"))
