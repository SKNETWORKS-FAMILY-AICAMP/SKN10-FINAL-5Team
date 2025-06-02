import openai
from sqlalchemy import create_engine, text
from neo4j import GraphDatabase
from sqlalchemy import MetaData, Table, Column, String, Text

# 1. NLU: 간단한 슬롯 추출 (실제론 LLM이나 spaCy, transformers 등 활용)
def parse_user_input(user_input):
    # 예시: "저는 28살 서울 거주 직장인입니다."
    slots = {}
    if "서울" in user_input:
        slots["region"] = "서울"
    if "28" in user_input:
        slots["age"] = 28
    if "직장인" in user_input:
        slots["job"] = "직장인"
    # ... 추가 파싱
    return slots

'''
# 2. RAG Retriever (PostgreSQL)
def query_rag(slots):
    #engine = create_engine("postgresql+psycopg2://user:password@host:port/dbname")
    engine = create_engine(
    "postgresql+psycopg2://postgres_user:postgres_password@localhost:5432/postgres_db"
    )
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM policies WHERE region=:region"),
            {"region": slots.get("region", "")}
        )
        policies = [dict(row) for row in result]
    return policies
'''

# 2. RAG Retriever (PostgreSQL)
def query_rag(slots):
    #engine = create_engine("postgresql+psycopg2://user:password@host:port/dbname")
    engine = create_engine("postgresql+psycopg2://postgres_user:postgres_password@postgres_db:5432/postgres_db")
    
    # 테이블 존재 확인 및 생성
    with engine.connect() as conn:
        if not conn.dialect.has_table(conn, "policies"):
            create_policies_table(engine)
    
    # 기존 쿼리 수행
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM policies WHERE region=:region"),
            {"region": slots.get("region", "")}
        )
        return [dict(row) for row in result]



# 3. KAG Retriever (Neo4j)
def query_kag(slots):
    #driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
    driver = GraphDatabase.driver(
    "bolt://neo4j:7687",auth=("neo4j", "neo4j_admin")
    )
    with driver.session() as session:
        cypher = """
        MATCH (p:Policy)-[:APPLIES_TO]->(r:Region {name: $region})
        RETURN p
        """
        result = session.run(cypher, region=slots.get("region", ""))
        policies = [record["p"] for record in result]
    return policies

# 4. Fusion: 정책 통합 및 중복 제거
def fuse_results(rag_results, kag_results):
    # 정책명 기준 단순 병합 예시
    all_policies = {p['정책명']: p for p in rag_results}
    for p in kag_results:
        all_policies[p['정책명']] = p
    return list(all_policies.values())

# 5. Matcher: 조건 일치 정책 필터
def match_policies(policies, slots):
    # 예시: 나이, 직업 등 추가 필터링
    matched = []
    for p in policies:
        if slots.get("job") and slots["job"] not in p.get("정책설명내용", ""):
            continue
        matched.append(p)
    return matched

# 6. LLM 응답 생성 (OpenAI 예시)
def generate_response(matched_policies, user_input):
    context = "\n".join([
        f"정책명: {p['정책명']}, 지원내용: {p['정책지원내용']}, 필요서류: {p.get('제출서류내용', '공고문 참고')}"
        for p in matched_policies
    ])
    prompt = f"""아래는 청년 주거정책 데이터입니다.
{context}
사용자 질문: {user_input}
위 정책 중 사용자에게 가장 적합한 정책을 추천하고, 자격조건·필요서류·지원금액을 자연스럽게 안내해줘."""
    # 실제론 OpenAI API 호출
    openai.api_key = "YOUR_OPENAI_API_KEY"
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 7. 전체 챗봇 파이프라인
def chatbot(user_input):
    slots = parse_user_input(user_input)
    rag_results = query_rag(slots)
    kag_results = query_kag(slots)
    fused = fuse_results(rag_results, kag_results)
    matched = match_policies(fused, slots)
    answer = generate_response(matched, user_input)
    return answer


# 8. PostgreSQL 테이블 생성 함수 
def create_policies_table(engine):
    metadata = MetaData()
    Table('policies', metadata,
        Column('정책명', String(255)),
        Column('정책설명내용', Text),
        Column('정책대분류명', String(50)),
        # ... 나머지 컬럼 정의
    )
    metadata.create_all(engine)

# PostgreSQL 연결 후 테이블 생성
engine = create_engine("postgresql+psycopg2://...")
create_policies_table(engine)

# 9. RAG 쿼리 전 테이블 존재 여부 확인
def query_rag(slots):
    engine = create_engine(...)
    with engine.connect() as conn:
        # 테이블 존재 여부 확인
        table_exists = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename = 'policies'
            )
        """)).scalar()
        
        if not table_exists:
            raise Exception("'policies' 테이블이 존재하지 않습니다")

# --- 예시 실행 ---
if __name__ == "__main__":
    user_input = "저는 28살 서울 거주 직장인입니다. 받을 수 있는 청년 주거정책 알려줘."
    print(chatbot(user_input))