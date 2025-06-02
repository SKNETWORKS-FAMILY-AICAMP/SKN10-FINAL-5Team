import openai
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Text, Date, Float, Boolean
from sqlalchemy.exc import ProgrammingError
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
load_dotenv()

# PostgreSQL 테이블 스키마 정의 (함수보다 먼저 정의)
def create_policies_table(engine):
    metadata = MetaData()
    Table(
        'policies', metadata,
        Column('정책명', String(255), primary_key=True),
        Column('정책설명내용', Text),
        Column('정책대분류명', String(50)),
        Column('정책중분류명', String(50)),
        Column('정책지원내용', Text),
        Column('심사방법내용', Text),
        Column('신청URL주소', String(255)),
        Column('제출서류내용', Text),
        Column('기타사항내용', Text),
        Column('참고URL주소1', String(255)),
        Column('참고URL주소2', String(255)),
        Column('소득기타내용', Text),
        Column('추가신청자격조건내용', Text),
        Column('참여제안대상내용', Text),
        Column('정책거주지역코드', String(50)),
        Column('정책취업요건코드', String(50)),
        Column('정책특화요건코드', String(50))
    )
    try:
        metadata.create_all(engine)
        print("테이블 생성 완료")
    except ProgrammingError as e:
        print(f"테이블 생성 오류: {e}")

# 1. NLU: 슬롯 추출
def parse_user_input(user_input):
    slots = {}
    if "서울" in user_input:
        slots["region"] = "서울"
    if "28" in user_input:
        slots["age"] = 28
    if "직장인" in user_input:
        slots["job"] = "직장인"
    return slots

# 2. RAG Retriever (PostgreSQL)
def query_rag(slots):
    # Docker Compose 서비스명으로 연결 (postgres_db)
    engine = create_engine(
        "postgresql+psycopg2://postgres_user:postgres_password@localhost:5432/postgres_db"
    )
    
    # 테이블 존재 확인 및 생성
    create_policies_table(engine)  # 테이블 생성 먼저 시도
    
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM policies WHERE 정책거주지역코드 LIKE :region"),
            {"region": f"%{slots.get('region', '')}%"}
        )
        return [dict(row) for row in result]

# 3. KAG Retriever (Neo4j)
def query_kag(slots):
    # Docker Compose 서비스명으로 연결 (neo4j)
    driver = GraphDatabase.driver(
        "bolt://neo4j_db:7687", # docker-compose.yml의 container_name
        auth=("neo4j", "neo4j_admin")
    )

    with driver.session() as session:
        cypher = """
        MATCH (p:Policy)-[:APPLIES_TO]->(r:Region)
        WHERE r.name CONTAINS $region
        RETURN p
        """
        result = session.run(cypher, region=slots.get("region", ""))
        return [dict(record["p"]) for record in result]

# 4. Fusion: 정책 통합
def fuse_results(rag_results, kag_results):
    all_policies = {p['정책명']: p for p in rag_results}
    for p in kag_results:
        all_policies[p['정책명']] = p
    return list(all_policies.values())

# 5. Matcher: 조건 필터링
def match_policies(policies, slots):
    matched = []
    for p in policies:
        if slots.get("job") and slots["job"] not in p.get("정책설명내용", ""):
            continue
        matched.append(p)
    return matched

# 6. LLM 응답 생성
def generate_response(matched_policies, user_input):
    context = "\n".join([
        f"정책명: {p['정책명']}, 지원내용: {p['정책지원내용']}, 필요서류: {p.get('제출서류내용', '공고문 참고')}"
        for p in matched_policies
    ])
    prompt = f"""아래는 청년 주거정책 데이터입니다.
            {context}
            사용자 질문: {user_input}
            위 정책 중 사용자에게 가장 적합한 정책을 추천하고, 자격조건·필요서류·지원금액을 자연스럽게 안내해줘."""
    
    # .env에서 OpenAI API 키 읽기
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(    
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 7. 전체 파이프라인
def chatbot(user_input):
    slots = parse_user_input(user_input)
    rag_results = query_rag(slots)
    kag_results = query_kag(slots)
    fused = fuse_results(rag_results, kag_results)
    matched = match_policies(fused, slots)
    return generate_response(matched, user_input)

# 8. Neo4j 연결 테스트
def test_neo4j():
    try:
        driver = GraphDatabase.driver(
            "bolt://neo4j:7687", 
            auth=("neo4j", "neo4j_admin")
        )
        with driver.session() as session:
            result = session.run("RETURN 1")
            print(result.single()[0])
        print("Neo4j 연결 성공!")
    except Exception as e:
        print(f"연결 실패: {e}")


# 실행
if __name__ == "__main__":
    test_neo4j()
    user_input = "저는 28살 서울 거주 직장인입니다. 받을 수 있는 청년 주거정책 알려줘."
    print(chatbot(user_input))