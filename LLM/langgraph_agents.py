from typing import Dict, List, Any, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# logs 디렉토리 생성 (없으면)
os.makedirs('logs', exist_ok=True)

# 안전한 로깅을 위한 문자열 처리 함수
def safe_log_string(text):
    """로깅 시 안전한 문자열 처리"""
    if not isinstance(text, str):
        text = str(text)
    
    # 문제가 되는 유니코드 문자들을 안전한 문자로 대체
    replacements = {
        '\u2024': '•',  # ONE DOT LEADER → BULLET
        '\u2025': '••', # TWO DOT LEADER → DOUBLE BULLET  
        '\u2026': '...', # HORIZONTAL ELLIPSIS → THREE DOTS
        '\u2027': '•',  # HYPHENATION POINT → BULLET
        '\u2030': '‰',  # PER MILLE SIGN → safe alternative
    }
    
    for old_char, new_char in replacements.items():
        text = text.replace(old_char, new_char)
    
    # cp949로 인코딩할 수 없는 문자들을 안전하게 처리
    try:
        text.encode('cp949')
        return text
    except UnicodeEncodeError:
        # cp949로 인코딩할 수 없는 문자를 '?'로 대체
        return text.encode('cp949', errors='replace').decode('cp949')

# 로깅 설정 (UTF-8 인코딩 추가)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(
            f'logs/langgraph_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log', 
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)

# State 정의
class AgentState(TypedDict):
    messages: List[Any]
    all_policies: List[Dict]
    filtered_policies: List[Dict]
    user_profile: Dict
    current_intent: str
    search_results: List[Dict]
    final_response: str
    use_structured_search: bool
    error: str
    context: str

# 데이터베이스 연결 관리
class DatabaseManager:
    def __init__(self):
        self.pg_conn = None
        self.vector_model = None
        self.index = None
        self.policy_vectors = None
        
    def get_pg_connection(self):
        """PostgreSQL 연결 반환"""
        if not self.pg_conn:
            try:
                self.pg_conn = psycopg2.connect(
                    dbname="postgres",
                    user="postgres",
                    password="postgres",
                    host="localhost",
                    port="5432"
                )
            except Exception as e:
                logging.error(f"PostgreSQL 연결 실패: {str(e)}")
                raise
        return self.pg_conn
    
    def load_vector_db(self):
        """Vector DB 로드 (example.py 방식 참고)"""
        try:
            from langchain_openai import OpenAIEmbeddings
            from langchain_community.vectorstores import FAISS
            
            # OpenAI 임베딩 모델 사용 (example.py와 동일)
            embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
            
            # FAISS 벡터 DB 로드 (example.py 방식)
            db_path = "data/vector_db_openai_large_combined"
            
            if os.path.exists(db_path):
                self.vector_db = FAISS.load_local(
                    folder_path=db_path,
                    embeddings=embedding_model,
                    allow_dangerous_deserialization=True
                )
                # 리트리버 생성
                self.retriever = self.vector_db.as_retriever(search_kwargs={"k": 10})
                logging.info("Vector DB (FAISS) 로드 성공!")
            else:
                logging.error("Vector DB 파일을 찾을 수 없습니다.")
                raise FileNotFoundError("Vector DB 파일을 찾을 수 없습니다.")
                
        except Exception as e:
            logging.error(f"Vector DB 로드 실패: {str(e)}")
            raise

# 데이터베이스 매니저 인스턴스 생성
db_manager = DatabaseManager()

# 공통 필터 노드
def common_filter_node(state: AgentState) -> AgentState:
    user_profile = state["user_profile"]
    # todo: user_profile 자체적으로 가져오는 방법 찾아보기.
    all_policies = state["all_policies"]
    
    filtered_policies = []
    current_date = datetime.now().date()
    
    for policy in all_policies:
        # 연령 조건
        age_condition = (
            (policy.get("지원대상최소연령") is None or policy["지원대상최소연령"] <= user_profile["age"]) and
            (policy.get("지원대상최대연령") is None or policy["지원대상최대연령"] >= user_profile["age"])
        )
        
        # 소득 조건
        income_condition = (
            policy.get("소득조건구분코드") is None or 
            policy["소득조건구분코드"] == user_profile["income_code"]
        )
        
        # 지역 조건
        region_condition = (
            policy.get("정책거주지역코드") is None or 
            policy["정책거주지역코드"] == user_profile["region"]
        )
        
        # 사업기간 조건
        date_condition = (
            policy.get("사업기간시작일자") <= current_date and
            (policy.get("사업기간종료일자") is None or policy["사업기간종료일자"] >= current_date)
        )
        
        if age_condition and income_condition and region_condition and date_condition:
            filtered_policies.append(policy)
    
    return {**state, "filtered_policies": filtered_policies}

# 주거 필터 노드
def housing_filter_node(state: AgentState) -> AgentState:
    filtered_policies = state["filtered_policies"]
    user_profile = state["user_profile"]
    
    housing_policies = []
    
    for policy in filtered_policies:
        # 주거 관련 키워드 검색
        housing_keywords = [
            policy.get("정책키워드명", "").lower(),
            policy.get("정책지원내용", "").lower(),
            policy.get("추가신청자격조건내용", "").lower()
        ]
        
        housing_condition = any([
            "주거" in keyword or
            "임대" in keyword or
            "무주택" in keyword
            for keyword in housing_keywords
        ])
        
        # 결혼 상태 조건
        marital_condition = (
            policy.get("결혼상태코드") is None or
            policy["결혼상태코드"] == user_profile.get("marital_status")
        )
        
        if housing_condition or marital_condition:
            housing_policies.append(policy)
    
    return {**state, "filtered_policies": housing_policies}

# 일자리 필터 노드
def job_filter_node(state: AgentState) -> AgentState:
    filtered_policies = state["filtered_policies"]
    user_profile = state["user_profile"]
    
    job_policies = []
    
    for policy in filtered_policies:
        # 일자리 관련 키워드 검색
        job_keywords = [
            policy.get("정책키워드명", "").lower(),
            policy.get("정책지원내용", "").lower(),
            policy.get("참여제안대상내용", "").lower()
        ]
        
        job_condition = any([
            "취업" in keyword or
            "훈련" in keyword or
            "구직자" in keyword
            for keyword in job_keywords
        ])
        
        # 취업/학력/특화 조건
        qualification_condition = (
            (policy.get("정책취업요건코드") is None or policy["정책취업요건코드"] == user_profile.get("job_code")) and
            (policy.get("정책학력요건코드") is None or policy["정책학력요건코드"] == user_profile.get("edu_code")) and
            (policy.get("정책특화요건코드") is None or policy["정책특화요건코드"] == user_profile.get("special_code"))
        )
        
        if job_condition or qualification_condition:
            job_policies.append(policy)
    
    return {**state, "filtered_policies": job_policies}

# 쿼리 라우터 로직을 intent_classifier에 통합
def enhanced_intent_classifier_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    last_message = messages[-1].content
    
    # 인텐트 분류
    housing_keywords = ["주거", "집", "임대", "전세", "월세", "무주택"]
    job_keywords = ["취업", "일자리", "직장", "훈련", "교육", "구직"]
    
    # tood: llm이 판단하게 하기.
    housing_score = sum(1 for keyword in housing_keywords if keyword in last_message)
    job_score = sum(1 for keyword in job_keywords if keyword in last_message)
    
    intent = "housing" if housing_score > job_score else "job"
    
    # 구조화된 검색 여부 판단
    is_structured = any([
        "연령" in last_message,
        "소득" in last_message,
        "지역" in last_message,
        "학력" in last_message
    ])
    
    return {**state, "current_intent": intent, "use_structured_search": is_structured}

# 인텐트 분류 노드 (enhanced 버전으로 통합)
intent_classifier_node = enhanced_intent_classifier_node

# 주거 에이전트 노드
def housing_agent_node(state: AgentState) -> AgentState:
    # 1. 공통 필터링
    state = common_filter_node(state)
    
    # 2. 주거 특화 필터링
    state = housing_filter_node(state)
    
    # 3. 검색 방식 결정 및 실행
    if state.get("use_structured_search", False):
        state = postgres_search_tool(state)
    else:
        state = vector_search_tool(state)
    
    # 4. 결과 재순위화
    state = rerank_tool(state)
    
    return state

# 일자리 에이전트 노드
def job_agent_node(state: AgentState) -> AgentState:
    # 1. 공통 필터링
    state = common_filter_node(state)
    
    # 2. 일자리 특화 필터링
    state = job_filter_node(state)
    
    # 3. 검색 방식 결정 및 실행
    if state.get("use_structured_search", False):
        state = postgres_search_tool(state)
    else:
        state = vector_search_tool(state)
    
    # 4. 결과 재순위화
    state = rerank_tool(state)
    
    return state

# PostgreSQL 검색 도구
def postgres_search_tool(state: AgentState) -> AgentState:
    try:
        filtered_policies = state["filtered_policies"]
        user_profile = state["user_profile"]
        messages = state["messages"]
        last_message = messages[-1].content
        
        logging.info(f"PostgreSQL 검색 시작 - 쿼리: {safe_log_string(last_message)}")
        logging.info(f"사용자 프로필: {user_profile}")
        
        conn = db_manager.get_pg_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 검색 키워드 추출
        housing_keywords = ["주거", "집", "임대", "전세", "월세", "무주택", "주택"]
        job_keywords = ["취업", "일자리", "직장", "훈련", "교육", "구직", "창업"]
        
        # 현재 인텐트 확인
        intent = state.get("current_intent", "")
        
        # 기본 쿼리 - 단순화된 버전
        if intent == "housing":
            # 주거 관련 검색
            query = """
                SELECT * FROM policies
                WHERE (
                    정책키워드명 ILIKE ANY(%s)
                    OR 정책지원내용 ILIKE ANY(%s)
                    OR 추가신청자격조건내용 ILIKE ANY(%s)
                )
                AND (지원대상최소연령 IS NULL OR 지원대상최소연령 <= %s)
                AND (지원대상최대연령 IS NULL OR 지원대상최대연령 >= %s)
                AND (정책거주지역코드 IS NULL OR 정책거주지역코드 = %s)
                AND 사업기간시작일자 <= CURRENT_DATE
                AND (사업기간종료일자 IS NULL OR 사업기간종료일자 >= CURRENT_DATE)
                ORDER BY 
                    CASE WHEN 정책지원금액 IS NOT NULL THEN 정책지원금액 ELSE 0 END DESC,
                    정책명
                LIMIT 20
            """
            keywords = [f"%{k}%" for k in housing_keywords]
            params = [keywords, keywords, keywords, 
                     user_profile.get("age", 35), user_profile.get("age", 35), 
                     user_profile.get("region", "")]
        else:
            # 일자리 관련 검색
            query = """
                SELECT * FROM policies
                WHERE (
                    정책키워드명 ILIKE ANY(%s)
                    OR 정책지원내용 ILIKE ANY(%s)
                    OR 추가신청자격조건내용 ILIKE ANY(%s)
                )
                AND (지원대상최소연령 IS NULL OR 지원대상최소연령 <= %s)
                AND (지원대상최대연령 IS NULL OR 지원대상최대연령 >= %s)
                AND (정책거주지역코드 IS NULL OR 정책거주지역코드 = %s)
                AND 사업기간시작일자 <= CURRENT_DATE
                AND (사업기간종료일자 IS NULL OR 사업기간종료일자 >= CURRENT_DATE)
                ORDER BY 
                    CASE WHEN 정책지원금액 IS NOT NULL THEN 정책지원금액 ELSE 0 END DESC,
                    정책명
                LIMIT 20
            """
            keywords = [f"%{k}%" for k in job_keywords]
            params = [keywords, keywords, keywords, 
                     user_profile.get("age", 35), user_profile.get("age", 35), 
                     user_profile.get("region", "")]
        
        # 쿼리 실행
        logging.info(f"실행할 쿼리: {query}")
        logging.info(f"쿼리 파라미터: {params}")
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        logging.info(f"PostgreSQL 검색 결과: {len(results)}개")
        
        # 결과를 딕셔너리 리스트로 변환
        search_results = []
        for row in results:
            policy_dict = dict(row)
            # 날짜 필드 문자열 변환
            for key, value in policy_dict.items():
                if isinstance(value, datetime):
                    policy_dict[key] = value.strftime('%Y-%m-%d')
                elif value is None:
                    policy_dict[key] = "N/A"
            
            search_results.append(policy_dict)
        
        cur.close()
        
        # 검색 결과가 없으면 더 광범위한 검색 시도
        if not search_results:
            logging.warning("구체적 검색 결과가 없음. 더 광범위한 검색을 시도합니다.")
            
            # 더 광범위한 검색
            broad_query = """
                SELECT * FROM policies
                WHERE (지원대상최소연령 IS NULL OR 지원대상최소연령 <= %s)
                AND (지원대상최대연령 IS NULL OR 지원대상최대연령 >= %s)
                AND 사업기간시작일자 <= CURRENT_DATE
                AND (사업기간종료일자 IS NULL OR 사업기간종료일자 >= CURRENT_DATE)
                ORDER BY 
                    CASE WHEN 정책지원금액 IS NOT NULL THEN 정책지원금액 ELSE 0 END DESC,
                    정책명
                LIMIT 10
            """
            
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(broad_query, [user_profile.get("age", 35), user_profile.get("age", 35)])
            results = cur.fetchall()
            
            logging.info(f"광범위한 검색 결과: {len(results)}개")
            
            for row in results:
                policy_dict = dict(row)
                # 날짜 필드 문자열 변환
                for key, value in policy_dict.items():
                    if isinstance(value, datetime):
                        policy_dict[key] = value.strftime('%Y-%m-%d')
                    elif value is None:
                        policy_dict[key] = "N/A"
                
                search_results.append(policy_dict)
            
            cur.close()
        
        logging.info(f"최종 검색 결과: {len(search_results)}개")
        if search_results:
            logging.info(f"첫 번째 결과 샘플: {search_results[0].get('정책명', 'N/A')}")
        
        return {**state, "search_results": search_results, "error": None}
        
    except Exception as e:
        logging.error(f"PostgreSQL 검색 중 오류 발생: {str(e)}")
        logging.error(f"오류 상세: {type(e).__name__}: {str(e)}")
        return {**state, "search_results": [], "error": str(e)}

# Vector DB 검색 도구
def vector_search_tool(state: AgentState) -> AgentState:
    try:
        messages = state["messages"]
        last_message = messages[-1].content
        
        logging.info(f"Vector DB 검색 시작 - 쿼리: {last_message}")
        
        # Vector DB 초기화 확인
        if not hasattr(db_manager, 'retriever') or db_manager.retriever is None:
            logging.info("Vector DB를 로드하는 중...")
            db_manager.load_vector_db()
        
        # 리트리버를 사용한 검색 (example.py 방식)
        retrieved_docs = db_manager.retriever.invoke(last_message)
        
        logging.info(f"Vector DB에서 {len(retrieved_docs)}개 문서 검색됨")
        
        # 결과를 딕셔너리 형태로 변환
        search_results = []
        for i, doc in enumerate(retrieved_docs):
            # 메타데이터와 콘텐츠를 결합하여 정책 정보 생성
            policy_info = {
                "정책명": doc.metadata.get("정책명", f"정책_{i+1}"),
                "정책키워드명": doc.metadata.get("정책키워드명", ""),
                "정책지원내용": doc.page_content[:500] if doc.page_content else "N/A",  # 내용 길이 제한
                "추가신청자격조건내용": doc.metadata.get("추가신청자격조건내용", ""),
                "정책거주지역코드": doc.metadata.get("정책거주지역코드", "전국"),
                "지원대상최소연령": doc.metadata.get("지원대상최소연령", "N/A"),
                "지원대상최대연령": doc.metadata.get("지원대상최대연령", "N/A"),
                "소득조건구분코드": doc.metadata.get("소득조건구분코드", "N/A"),
                "결혼상태코드": doc.metadata.get("결혼상태코드", "N/A"),
                "신청시작일자": doc.metadata.get("신청시작일자", "N/A"),
                "신청종료일자": doc.metadata.get("신청종료일자", "N/A"),
                "정책지원금액": doc.metadata.get("정책지원금액", "N/A"),
                "similarity_score": 0.8 - (i * 0.1)  # 순서에 따른 유사도 점수
            }
            search_results.append(policy_info)
        
        logging.info(f"Vector DB 검색 결과 변환 완료: {len(search_results)}개")
        if search_results:
            logging.info(f"첫 번째 결과: {search_results[0].get('정책명', 'N/A')}")
        
        return {**state, "search_results": search_results, "error": None}
        
    except FileNotFoundError as e:
        logging.warning(f"Vector DB 파일을 찾을 수 없음: {str(e)}")
        logging.info("PostgreSQL 검색으로 fallback 실행")
        # Vector 검색 실패 시 PostgreSQL 검색으로 폴백
        return postgres_search_tool(state)
    except Exception as e:
        logging.error(f"Vector DB 검색 중 오류 발생: {str(e)}")
        logging.error(f"오류 상세: {type(e).__name__}: {str(e)}")
        logging.info("PostgreSQL 검색으로 fallback 실행")
        # Vector 검색 실패 시 PostgreSQL 검색으로 폴백
        return postgres_search_tool(state)

# 결과 재순위화 도구
def rerank_tool(state: AgentState) -> AgentState:
    try:
        search_results = state["search_results"]
        user_profile = state["user_profile"]
        
        # 검색 결과가 없으면 그대로 반환
        if not search_results:
            return {**state, "search_results": [], "error": None}
        
        def calculate_score(policy):
            score = 0.0
            
            # 1. 지원금액 점수 (최대 40점)
            try:
                policy_amount = policy.get("정책지원금액")
                if policy_amount and policy_amount != "N/A":
                    # 숫자 타입 변환 시도
                    if isinstance(policy_amount, str):
                        # 문자열에서 숫자만 추출
                        import re
                        numbers = re.findall(r'\d+', policy_amount.replace(',', ''))
                        if numbers:
                            policy_amount = int(numbers[0])
                        else:
                            policy_amount = 0
                    elif isinstance(policy_amount, (int, float)):
                        policy_amount = float(policy_amount)
                    else:
                        policy_amount = 0
                    
                    # 최대 금액 계산
                    max_amount = 0
                    for p in search_results:
                        p_amount = p.get("정책지원금액", 0)
                        if p_amount and p_amount != "N/A":
                            if isinstance(p_amount, str):
                                numbers = re.findall(r'\d+', p_amount.replace(',', ''))
                                if numbers:
                                    p_amount = int(numbers[0])
                                else:
                                    p_amount = 0
                            elif isinstance(p_amount, (int, float)):
                                p_amount = float(p_amount)
                            else:
                                p_amount = 0
                            max_amount = max(max_amount, p_amount)
                    
                    if max_amount > 0:
                        score += 40 * (policy_amount / max_amount)
                        
            except Exception as e:
                logging.warning(f"지원금액 점수 계산 중 오류: {str(e)}")
            
            # 2. 연령 적합도 점수 (최대 20점)
            try:
                age = user_profile.get("age")
                min_age = policy.get("지원대상최소연령")
                max_age = policy.get("지원대상최대연령")
                
                if age and min_age is not None and max_age is not None:
                    # 연령을 숫자로 변환
                    if isinstance(min_age, str) and min_age != "N/A":
                        min_age = float(min_age)
                    elif isinstance(min_age, (int, float)):
                        min_age = float(min_age)
                    else:
                        min_age = None
                        
                    if isinstance(max_age, str) and max_age != "N/A":
                        max_age = float(max_age)
                    elif isinstance(max_age, (int, float)):
                        max_age = float(max_age)
                    else:
                        max_age = None
                    
                    if min_age is not None and max_age is not None:
                        if min_age <= age <= max_age:
                            score += 20
                            
            except Exception as e:
                logging.warning(f"연령 적합도 점수 계산 중 오류: {str(e)}")
            
            # 3. 소득 조건 적합도 점수 (최대 15점)
            try:
                if policy.get("소득조건구분코드") == user_profile.get("income_code"):
                    score += 15
            except Exception as e:
                logging.warning(f"소득 조건 점수 계산 중 오류: {str(e)}")
            
            # 4. 지역 조건 적합도 점수 (최대 15점)
            try:
                if policy.get("정책거주지역코드") == user_profile.get("region"):
                    score += 15
            except Exception as e:
                logging.warning(f"지역 조건 점수 계산 중 오류: {str(e)}")
            
            # 5. Vector 검색 유사도 점수 (최대 10점)
            try:
                similarity_score = policy.get("similarity_score", 0)
                if isinstance(similarity_score, (int, float)):
                    score += 10 * similarity_score
            except Exception as e:
                logging.warning(f"유사도 점수 계산 중 오류: {str(e)}")
            
            return score
        
        # 각 정책에 점수 계산 및 추가
        for policy in search_results:
            try:
                policy["rerank_score"] = calculate_score(policy)
            except Exception as e:
                logging.warning(f"정책 점수 계산 중 오류: {str(e)}")
                policy["rerank_score"] = 0.0
        
        # 점수 기준으로 재정렬
        reranked_results = sorted(
            search_results,
            key=lambda x: x.get("rerank_score", 0),
            reverse=True
        )
        
        logging.info(f"재순위화 완료: {len(reranked_results)}개 정책")
        
        return {**state, "search_results": reranked_results, "error": None}
        
    except Exception as e:
        logging.error(f"재순위화 중 오류 발생: {str(e)}")
        # 오류 발생 시 원래 결과 그대로 반환
        return {**state, "error": None}

# 컨텍스트 빌더 노드
def context_builder_node(state: AgentState) -> AgentState:
    search_results = state["search_results"]
    
    # 검색 결과 디버깅 로그 추가 (안전한 로깅)
    logging.info(f"검색 결과 개수: {len(search_results)}")
    if search_results:
        # 첫 번째 검색 결과를 안전하게 로깅
        first_result_safe = {}
        for k, v in search_results[0].items():
            first_result_safe[k] = safe_log_string(str(v))
        logging.info(f"첫 번째 검색 결과: {first_result_safe}")
    
    # 검색 결과가 없을 경우 처리
    if not search_results:
        logging.warning("검색 결과가 없습니다.")
        return {**state, "context": "검색된 정책이 없습니다."}
    
    # 검색 결과를 컨텍스트로 변환 (안전한 문자열 처리)
    context_parts = []
    for i, p in enumerate(search_results[:5]):  # 상위 5개 정책만 사용
        # 각 필드를 안전하게 처리
        policy_name = safe_log_string(str(p.get('정책명', 'N/A')))
        support_content = safe_log_string(str(p.get('정책지원내용', 'N/A')))
        qualification = safe_log_string(str(p.get('추가신청자격조건내용', 'N/A')))
        amount = safe_log_string(str(p.get('정책지원금액', 'N/A')))
        region = safe_log_string(str(p.get('정책거주지역코드', 'N/A')))
        start_date = safe_log_string(str(p.get('신청시작일자', 'N/A')))
        end_date = safe_log_string(str(p.get('신청종료일자', 'N/A')))
        min_age = safe_log_string(str(p.get('지원대상최소연령', 'N/A')))
        max_age = safe_log_string(str(p.get('지원대상최대연령', 'N/A')))
        
        policy_text = f"""
정책 {i+1}:
- 정책명: {policy_name}
- 지원내용: {support_content}
- 신청자격: {qualification}
- 지원금액: {amount}
- 지원지역: {region}
- 신청기간: {start_date} ~ {end_date}
- 연령조건: {min_age}세 ~ {max_age}세
"""
        context_parts.append(policy_text.strip())
    
    context = "\n\n".join(context_parts)
    
    # 컨텍스트 디버깅 로그 (안전한 처리)
    logging.info(f"생성된 컨텍스트 길이: {len(context)}")
    safe_context_preview = safe_log_string(context[:200])
    logging.info(f"컨텍스트 미리보기: {safe_context_preview}...")
    
    return {**state, "context": context}

# LLM 응답 생성 노드
def llm_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    context = state.get("context", "")
    user_profile = state.get("user_profile", {})
    
    # 디버깅 로그 추가 (안전한 처리)
    logging.info(f"LLM 노드 - 컨텍스트 길이: {len(context)}")
    safe_context_check = safe_log_string(context[:100])
    logging.info(f"LLM 노드 - 컨텍스트 내용 확인: {safe_context_check}...")
    
    # 컨텍스트가 비어있거나 검색 결과가 없는 경우 처리
    if not context or context.strip() == "" or context == "검색된 정책이 없습니다.":
        logging.warning("컨텍스트가 비어있습니다. 일반적인 안내 메시지를 생성합니다.")
        
        # 일반적인 안내 메시지 생성
        fallback_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 청년 정책 추천 전문가입니다. 
            특정 정책을 찾지 못했더라도, 사용자의 질문에 대해 도움이 되는 일반적인 조언과 
            정책 검색을 위한 다음 단계를 안내해주세요."""),
            ("human", f"""사용자 질문: {messages[-1].content}
            사용자 정보: 나이 {user_profile.get('age', 'N/A')}세, 지역 {user_profile.get('region', 'N/A')}
            
            현재 구체적인 정책을 찾지 못했습니다. 
            사용자의 질문에 대해 일반적인 조언과 정책 검색을 위한 다음 단계를 안내해주세요.
            
            다음 사항을 포함해주세요:
            1. 질문과 관련된 일반적인 청년 정책 유형 설명
            2. 정책 검색을 위한 구체적인 방법 제안
            3. 관련 기관이나 웹사이트 정보
            4. 추가로 필요한 정보나 조건들""")
        ])
        
        llm = ChatOpenAI(model="gpt-4-turbo-preview")
        chain = fallback_prompt | llm | StrOutputParser()
        response = chain.invoke({})
        
        return {**state, "final_response": response}
    
    # 정상적인 정책 추천 프롬프트
    logging.info("정상적인 정책 추천 프롬프트를 사용합니다.")
    prompt = ChatPromptTemplate.from_messages([
        ("system", """당신은 청년 정책 추천 전문가입니다. 
        주어진 정책 정보를 바탕으로 사용자에게 가장 적합한 정책을 추천하고, 
        그 이유와 다음 행동 단계를 구체적으로 안내해주세요.
        
        응답 형식:
        1. 추천 정책 (1-2개)
        2. 추천 이유
        3. 신청 방법 및 절차
        4. 주의사항
        5. 추가 정보 확인 방법"""),
        ("human", f"""사용자 질문: {messages[-1].content}
        사용자 정보: 나이 {user_profile.get('age', 'N/A')}세, 지역 {user_profile.get('region', 'N/A')}
        
        검색된 정책 정보:
        {context}
        
        위 정책들 중에서 사용자에게 가장 적합한 정책을 추천하고, 
        그 이유와 구체적인 다음 행동 단계를 안내해주세요.""")
    ])
    
    # LLM 호출
    llm = ChatOpenAI(model="gpt-4-turbo-preview")
    chain = prompt | llm | StrOutputParser()
    
    try:
        response = chain.invoke({})
        logging.info(f"LLM 응답 생성 완료: {response[:100]}...")
        return {**state, "final_response": response}
    except Exception as e:
        logging.error(f"LLM 응답 생성 중 오류: {str(e)}")
        return {**state, "final_response": f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"}

# 그래프 구성
def create_graph() -> StateGraph:
    builder = StateGraph(AgentState)
    
    # 노드 추가
    builder.add_node("intent_classifier", intent_classifier_node)
    builder.add_node("housing_agent", housing_agent_node)
    builder.add_node("job_agent", job_agent_node)
    builder.add_node("context_builder", context_builder_node)
    builder.add_node("llm_response", llm_node)
    
    # 시작점 설정
    builder.set_entry_point("intent_classifier")
    
    # 인텐트에 따른 분기 (intent_classifier에서 바로 에이전트로)
    builder.add_conditional_edges(
        "intent_classifier",
        lambda x: "housing_agent" if x["current_intent"] == "housing" else "job_agent",
        {
            "housing_agent": "housing_agent",
            "job_agent": "job_agent"
        }
    )
    
    # 에이전트 처리 후 컨텍스트 빌더와 LLM 연결
    builder.add_edge("housing_agent", "context_builder")
    builder.add_edge("job_agent", "context_builder")
    builder.add_edge("context_builder", "llm_response")
    builder.add_edge("llm_response", END)
    
    return builder.compile()

# 그래프 실행 함수
def run_graph(messages: List[Any], user_profile: Dict, all_policies: List[Dict]) -> str:
    try:
        graph = create_graph()
        
        initial_state = {
            "messages": messages,
            "all_policies": all_policies,
            "filtered_policies": [],
            "user_profile": user_profile,
            "current_intent": "",
            "search_results": [],
            "final_response": "",
            "use_structured_search": False,
            "error": None,
            "context": ""
        }
        
        result = graph.invoke(initial_state)
        
        if result.get("error"):
            logging.error(f"그래프 실행 중 오류 발생: {result['error']}")
            return f"죄송합니다. 처리 중 오류가 발생했습니다: {result['error']}"
        
        return result["final_response"]
        
    except Exception as e:
        logging.error(f"그래프 실행 중 예외 발생: {str(e)}")
        return f"죄송합니다. 시스템 오류가 발생했습니다: {str(e)}"
