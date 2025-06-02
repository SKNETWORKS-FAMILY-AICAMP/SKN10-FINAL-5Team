# 실제 프로젝트: 청년정책 추천 시스템 (RAG + KAG)
# 주요 모듈: LangChain, Neo4j, FAISS, OpenAI LLM

import os
from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA, GraphCypherQAChain
from langchain.chat_models import ChatOpenAI
from langchain.graphs import Neo4jGraph
from langchain.prompts import PromptTemplate

# 1. 환경 설정
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEO4J_URL = os.getenv("NEO4J_URL")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# 2. 벡터 검색기 준비 (RAG)
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large", max_tokens=300000)
vector_store = FAISS.load_local("faiss_policy_index", embeddings=embedding_model)
retriever = vector_store.as_retriever()

# 3. 지식그래프 연결 (KAG)
graph = Neo4jGraph(
    url=NEO4J_URL,
    username=NEO4J_USER,
    password=NEO4J_PASSWORD
)

# 4. LLM 초기화
llm = ChatOpenAI(model_name="gpt-4o")

# 5. RAG 체인 정의
rag_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True
)

# 6. KAG 체인 정의
cypher_prompt = PromptTemplate(
    input_variables=["question"],
    template="""
당신은 지식그래프를 탐색하여 한국 청년 정책에 대한 정보를 제공합니다.
사용자 질문: {question}
Cypher 쿼리를 생성하고, 관련 정책 정보를 요약하세요.
"""
)
graph_chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    cypher_prompt=cypher_prompt,
    verbose=True
)

# 7. 통합 라우팅 함수

def route_question(user_query: str):
    if any(x in user_query for x in ["어디", "무엇", "추천", "있는"]):
        print("[RAG 기반 검색 수행]")
        return rag_chain.run(user_query)
    else:
        print("[KAG 기반 그래프 탐색 수행]")
        return graph_chain.run(user_query)

# 8. 실행 예시
if __name__ == "__main__":
    query = "서울에 사는 30대 청년인데 생활비 지원 정책 있어?"
    result = route_question(query)
    print("\n[응답 결과]\n", result)
