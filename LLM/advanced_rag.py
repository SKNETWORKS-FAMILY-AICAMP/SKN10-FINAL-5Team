"""
LangGraph Studio용 청년정책 RAG 시스템
주거 관련 정책과 일자리 관련 정책에 대해서만 답변하고, 
그 외 질문에 대해서는 답변을 거부하는 시스템
"""
import os
import json
import logging
from typing import List, Dict, Any, Optional, Literal, Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# LangChain imports
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# LangChain SQL imports
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
import psycopg2
from psycopg2.extras import RealDictCursor

# HTML 생성을 위한 추가 imports
import markdown
from markdown.extensions import codehilite
import html


# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QueryClassification(BaseModel):
    """질의 분류를 위한 구조화된 출력 모델"""
    lclsf_nm: Literal["주거", "일자리", "일반", "그 외 정책", "기타"] = Field(
        description="대분류(lclsf_nm): 주거, 일자리, 일반, 그 외 정책, 기타"
    )
    mclsf_nm: Optional[Literal[
        "대출, 이자, 전월세 등 금융지원",
        "임대주택, 기숙사 등 주거지원", 
        "이사비, 부동산 중개비 등 보조금지원",
        "전문인력양성, 훈련",
        "창업",
        "취업 전후 지원"
    ]] = Field(
        default=None,
        description="중분류(mclsf_nm): 주거-금융지원/주거지원/보조금지원, 일자리-훈련/창업/취업지원, 기타-없음"
    )
    query_keywords: str = Field(
        default=None,
        description="사용자 질문에서 추출된 키워드"
    )
    confidence: float = Field(
        description="분류 신뢰도 (0.0-1.0)", 
        ge=0.0, 
        le=1.0
    )
    reasoning: str = Field(
        description="분류 근거 설명"
    )


class UserConditions(BaseModel):
    """사용자 조건 추출을 위한 구조화된 출력 모델"""
    age: Optional[int] = Field(
        default=None,
        description="사용자 나이"
    )
    mrg_stts_cd: Optional[Literal["기혼", "미혼"]] = Field(
        default=None,
        description="결혼 상태"
    )
    plcy_major_cd: Optional[Literal["인문계열", "자연계열", "사회계열", "상경계열", "이학계열", "공학계열", "예체능계열", "농산업계열"]] = Field(
        default=None,
        description="전공 계열"
    )
    job_cd: Optional[Literal["재직자", "미취업자", "자영업자", "(예비)창업자", "영농종사자", "비정규직"]] = Field(
        default=None,
        description="취업 상태"
    )
    school_cd: Optional[Literal["고졸 미만", "고교 재학", "고졸 예정", "고교 졸업", "대학 재학", "대졸 예정", "대학 졸업", "석·박사"]] = Field(
        default=None,
        description="학력 상태"
    )
    zip_cd: Optional[str] = Field(
        default=None,
        description="거주지 (광역시/도, 시군구)"
    )
    earn_etc_cn: Optional[str] = Field(
        default=None,
        description="소득 요건 (예: 중위소득 150% 이하, 월소득 200만원 이하 등)"
    )
    additional_requirement: Optional[str] = Field(
        default=None,
        description="기타 추가 요건이나 상황"
    )
    confidence: float = Field(
        description="조건 추출 신뢰도 (0.0-1.0)",
        ge=0.0,
        le=1.0
    )

class SQLQueryGeneration(BaseModel):
    """SQL 쿼리 생성을 위한 구조화된 출력 모델"""
    sql_query: str = Field(
        description="생성된 PostgreSQL 쿼리"
    )
    explanation: str = Field(
        description="쿼리 생성 근거 및 설명"
    )
    confidence: float = Field(
        description="쿼리 생성 신뢰도 (0.0-1.0)",
        ge=0.0,
        le=1.0
    )

class GraphState(TypedDict):
    """그래프 상태 정의"""
    messages: Annotated[List[BaseMessage], add_messages]  # LangGraph Studio 호환성을 위한 메시지 리스트
    query: str  # 사용자 질의
    classification: Optional[QueryClassification]  # 질의 분류 결과
    user_conditions: Optional[UserConditions]  # 사용자 조건 추출 결과
    generated_sql: Optional[str]  # 정책 검색을 위한 필터 쿼리
    sql_result: Optional[str]
    final_response: Optional[str]  # 최종 답변
    html_content: Optional[str]  # HTML 형식의 최종 결과
    error: Optional[str]  # 오류 메시지
    timestamp: str  # 처리 시각


class YouthPolicyRAGConfig:
    """RAG 시스템 설정"""
    def __init__(self):
        # 데이터베이스 설정
        self.db_config = {
            'host': os.getenv("DB_HOST", 'localhost'),
            'database': os.getenv("DB_NAME", 'youth_policy'),
            'user': os.getenv("DB_USER", 'postgres'),
            'password': os.getenv("DB_PASSWORD", 'your_password'),
            'port': os.getenv("DB_PORT", 5432)
        }
        
        # OpenAI 설정
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        # RAG 설정
        self.top_k = int(os.getenv('TOP_K', 10))
        self.confidence_threshold = os.getenv('CONFIDENCE_THRESHOLD', 0.5)  # 분류 신뢰도 임계값
        
        # PostgreSQL URI 생성
        self.db_uri = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"

        # LangChain LLM 설정
        try:
            self.chat_llm = ChatOpenAI(
                api_key=self.openai_api_key,
                temperature=0,
                verbose=True,
                model="gpt-4o",
            )
            logger.info("LangChain LLM 초기화 완료")
        except Exception as e:
            logger.warning(f"LangChain LLM 초기화 실패: {e}")
            self.chat_llm = None
        # SQLDatabase 설정
        try:
            self.sql_database = SQLDatabase.from_uri(self.db_uri)
            logger.info("SQLDatabase 초기화 완료")
        except Exception as e:
            logger.warning(f"SQLDatabase 초기화 실패: {e}")
            self.sql_database = None
        
        # LangChain ChatOpenAI 모델 설정 (질의 분류용)
        self.thinking_model = ChatOpenAI(
            api_key=self.openai_api_key,
            model="o3-mini",
        )


# 전역 설정 인스턴스
config = YouthPolicyRAGConfig()


def classify_query_node(state: GraphState) -> GraphState:
    """질의 분류 노드 - LangChain structured output 사용"""
    try:
        logger.info("질의 분류 시작")
        
        # 메시지에서 마지막 사용자 메시지 추출
        user_message = None
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                user_message = message.content
                break
        
        if not user_message:
            raise ValueError("사용자 메시지를 찾을 수 없습니다.")
        
        # 프롬프트 템플릿 정의
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 청년정책 질의 분류 전문가입니다. 
사용자의 질문을 다음과 같이 대분류(lclsf_nm)와 중분류(mclsf_nm)로 분류해주세요:

**대분류 (lclsf_nm):**
- '주거': 전월세 대출, 임대주택, 기숙사, 이사비 지원, 부동산 중개비 지원 등 관련 정책
- '일자리': 일자리, 창업, 취업, 전문인력양성, 훈련, 기업지원 등 관련 정책
- '일반': 정책과 관련한 일반적인 질문이나 정보 요청
- '그 외 정책': 주거와 일자리 관련이 아닌 기타 정책이나 질문
- '기타': 그 외 모든 질문

**중분류 (mclsf_nm):**
- 어떤 상황이든 null로 분류해주세요.

주거와 일자리 관련 키워드를 정확히 식별하고, 애매한 경우에는 기타로 분류하세요.

**키워드 (query_keywords):**
- 사용자 질문에서 추출된 키워드, 정책 검색 시 유사도 판단에 사용됩니다.             
"""),
            ("human", "다음 질문을 분류해주세요: {query}")
        ])
        # 구조화된 출력을 위한 체인 생성 (streaming 비활성화)
        llm_no_stream = config.thinking_model.bind(stream=False)
        structured_llm = llm_no_stream.with_structured_output(QueryClassification)
        chain = prompt | structured_llm
        
        # 분류 실행
        classification = chain.invoke({"query": user_message})
        
        logger.info(f"질의 분류 완료: {classification.lclsf_nm}/{classification.mclsf_nm} (신뢰도: {classification.confidence})")
        
        return {
            **state,
            "query": user_message,
            "classification": classification
        }
        
    except Exception as e:
        logger.error(f"질의 분류 실패: {e}")
        return {
            **state,
            "error": f"질의 분류 실패: {str(e)}"
        }


def route_after_classification(state: GraphState) -> Literal["continue", "reject"]:
    """분류 결과에 따른 라우팅 결정"""
    if state.get("error"):
        return "reject"
    
    classification = state.get("classification")
    if not classification:
        return "reject"
    # 주거 또는 일자리 관련이고 신뢰도가 임계값 이상인 경우만 계속 진행
    if classification.lclsf_nm in ["주거", "일자리", "일반"]:
        logger.info(f"질의 승인: {classification.lclsf_nm} (신뢰도: {classification.confidence})")
        return "continue"
    else:
        logger.info(f"질의 거부: {classification.lclsf_nm} (신뢰도: {classification.confidence})")
        return "reject"


def extract_user_conditions_node(state: GraphState) -> GraphState:
    """사용자 조건 추출 노드 - LangChain structured output 사용"""
    try:
        logger.info("사용자 조건 추출 시작")
        
        # 프롬프트 템플릿 정의
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 사용자의 질문에서 개인 조건을 추출하는 전문가입니다.
사용자의 질문을 분석하여 다음 조건들을 추출해주세요:

**추출할 조건들:**
1. age: 나이 (숫자로)
2. mrg_stts_cd: 결혼 상태 ('기혼', '미혼' 중 하나)
3. plcy_major_cd: 전공 계열 ('인문계열', '자연계열', '사회계열', '상경계열', '이학계열', '공학계열', '예체능계열', '농산업계열' 중 하나)
4. job_cd: 취업 상태 ('재직자', '미취업자', '자영업자', '(예비)창업자', '영농종사자', '비정규직' 중 하나)
5. school_cd: 학력 상태 ('고졸 미만', '고교 재학', '고졸 예정', '고교 졸업', '대학 재학', '대졸 예정', '대학 졸업', '석·박사' 중 하나)
6. zip_cd: 거주지 (광역지자체, 기초지자체 형태로)
7. earn_etc_cn: 소득 요건 (구체적인 소득 수준이나 조건)
8. additional_requirement: 기초생활수급자, 한부모가정, 농업인, 중소기업 등 추가적인 조건

**추출 규칙:**
- 명시적으로 언급되지 않은 조건은 None으로 설정
- 추론이나 가정하지 말고, 명확히 언급된 내용만 추출
- 거주지는 "서울특별시", "대구광역시", "경상북도", "전북특별자치도", "강원특별자치도", "서울특별시 구로구", "경기도 수원시 팔달구" 의 형태로 추출
- 소득은 "월소득 200만원 이하", "중위소득 150% 이하" 등의 형태로 추출
- 신뢰도는 추출된 정보의 명확성과 완성도를 기준으로 평가"""),
            ("human", "다음 질문에서 사용자의 개인 조건을 추출해주세요: {query}")
        ])
        # 구조화된 출력을 위한 체인 생성 (streaming 비활성화)
        llm_no_stream = config.thinking_model.bind(stream=False)
        structured_llm = llm_no_stream.with_structured_output(UserConditions)
        chain = prompt | structured_llm
        
        # 조건 추출 실행
        user_conditions = chain.invoke({"query": state['query']})
        
        logger.info(f"사용자 조건 추출 완료 (신뢰도: {user_conditions.confidence})")
        logger.info(f"추출된 조건: 나이={user_conditions.age}, 결혼상태={user_conditions.mrg_stts_cd}, 거주지={user_conditions.zip_cd}")
        
        return {
            **state,
            "user_conditions": user_conditions
        }
        
    except Exception as e:
        logger.error(f"사용자 조건 추출 실패: {e}")
        return {
            **state,
            "error": f"사용자 조건 추출 실패: {str(e)}"
        }


def generate_sql_query_node(state: GraphState) -> GraphState:
    """SQL 쿼리를 생성하고 실행하는 노드"""
    try:
        logger.info("SQL 쿼리 생성 및 실행 시작")
        
        classification = state["classification"]
        user_conditions = state.get("user_conditions")
        query = state["query"]
        
        try:
            # 직접 SQL 쿼리 생성 체인 생성
            sql_chain = create_direct_sql_chain(config, classification, user_conditions)
            
            # SQL 쿼리 생성
            logger.info("SQL 쿼리 생성 중...")
            sql_generation = sql_chain.invoke({"query": query})
            
            logger.info(f"생성된 SQL 쿼리: {sql_generation.sql_query}")
            logger.info(f"쿼리 생성 근거: {sql_generation.explanation}")
            
            # SQL 쿼리 실행
            logger.info("PostgreSQL 쿼리 실행 중...")
            sql_result = execute_postgresql_query(config, sql_generation.sql_query)
            
            if not sql_result["success"]:
                raise Exception(f"SQL 실행 실패: {sql_result['error']}")
            
            logger.info(f"쿼리 실행 완료: {sql_result['row_count']}개 결과 반환")
            
            return {
                **state,
                "generated_sql": sql_generation.sql_query,
                "sql_result": sql_result['data'],
                "sql_explanation": sql_generation.explanation
            }
            
        except Exception as e:
            logger.error(f"SQL 쿼리 처리 실패: {e}")
            error_message = f"정책 검색 중 오류가 발생했습니다: {str(e)}"
            return {
                **state,
                "error": error_message
            }
        
    except Exception as e:
        logger.error(f"SQL 쿼리 노드 실행 실패: {e}")
        return {
            **state,
            "error": f"SQL 쿼리 생성 중 오류가 발생했습니다: {str(e)}"
        }


def generate_response_node(state: GraphState) -> GraphState:
    """SQL 쿼리 결과를 바탕으로 자연어 응답을 생성하는 노드"""
    try:
        logger.info("자연어 응답 생성 시작")
        
        # 에러가 있는 경우 에러 메시지 반환
        if state.get("error"):
            ai_message = AIMessage(content=state["error"])
            return {
                **state,
                "messages": state["messages"] + [ai_message]
            }
        
        classification = state["classification"]
        query = state["query"]
        sql_result = state.get("sql_result", [])
        
        # 결과를 바탕으로 자연어 응답 생성
        response_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 청년정책 전문 상담사입니다. 
데이터베이스 검색 결과를 바탕으로 사용자에게 도움이 되는 정확하고 친절한 답변을 제공해주세요.

**분류 정보:** {classification_type}
**사용자 질문:** {user_query}
**검색된 데이터:** {search_data}

**답변 가이드라인:**
1. 검색 결과를 바탕으로 정확한 정보를 제공하세요
2. 정책명, 지원내용, 신청방법 등을 구체적으로 안내하세요
3. 사용자의 조건에 맞는 정책을 우선적으로 추천하세요
4. 검색 결과가 없거나 부족한 경우 그 이유를 설명하세요
5. 친근하고 도움이 되는 톤으로 답변하세요
6. 필요시 추가 문의 방법이나 관련 기관 정보를 제공하세요
7. 답변 시 markdown 형식을 사용하여 가독성을 높이세요
8. 적절한 이모지를 사용하여 답변을 더 친근하게 만드세요
9. 주거정책과 일자리 정책을 구분하여 답변하세요"""),
            ("human", "위 검색 결과를 바탕으로 사용자 질문에 대한 답변을 생성해주세요.")
        ])
        
        response_chain = response_prompt | config.chat_llm
        final_response = response_chain.invoke({
            "classification_type": classification.lclsf_nm,
            "user_query": query,
            "search_data": str(sql_result)
        })
        
        logger.info("자연어 응답 생성 완료")
        
        # 메시지 리스트에 AI 응답 추가
        ai_message = AIMessage(content=final_response.content)
        
        return {
            **state,
            "messages": state["messages"] + [ai_message],
            "final_response": final_response.content
        }
        
    except Exception as e:
        logger.error(f"응답 생성 실패: {e}")
        error_message = f"응답 생성 중 오류가 발생했습니다: {str(e)}"
        ai_message = AIMessage(content=error_message)
        
        return {
            **state,
            "messages": state["messages"] + [ai_message],
            "error": error_message
        }

def reject_query_node(state: GraphState) -> GraphState:
    """질의 거부 노드"""
    logger.info("질의 거부 처리")
    
    classification = state.get("classification")
    
    if state.get("error"):
        response = f"""죄송합니다. 질문을 처리하는 중 오류가 발생했습니다.

오류: {state['error']}

다시 시도해 주시기 바랍니다."""
    else:
        response = f"""죄송합니다. 저는 청년들의 **주거 관련 정책**과 **일자리 관련 정책**에 대해서만 도움을 드릴 수 있습니다.

다음과 같은 질문에 대해 도움을 드릴 수 있습니다:

**🏠 주거 관련 정책:**
- 임대료 지원, 주택 구입 지원
- 중개수수료 지원, 전세자금 대출
- 주거급여, 청년 임대주택 등

**💼 일자리 관련 정책:**
- 취업 지원, 창업 지원
- 직업 훈련, 인턴십 프로그램
- 취업 수당, 고용보험 등

주거나 일자리와 관련된 질문으로 다시 문의해 주시면 더 나은 도움을 드리겠습니다."""
    
    # 메시지 리스트에 AI 응답 추가
    ai_message = AIMessage(content=response)
    
    return {
        **state,
        "messages": state["messages"] + [ai_message],
        "final_response": response
    }

def get_postgresql_schema(config) -> str:
    """PostgreSQL 데이터베이스 스키마 정보를 가져오는 함수"""
    try:
        # config의 db_config를 사용하여 직접 연결
        conn = psycopg2.connect(
            host=config.db_config['host'],
            database=config.db_config['database'],
            user=config.db_config['user'],
            password=config.db_config['password'],
            port=config.db_config['port']
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 테이블 스키마 정보 쿼리 (policies, policy_conditions 테이블만, 코멘트 포함)
        schema_query = """
        SELECT 
            t.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            COALESCE(col_desc.description, '') as column_comment,
            COALESCE(table_desc.description, '') as table_comment
        FROM information_schema.tables t
        JOIN information_schema.columns c ON t.table_name = c.table_name
        LEFT JOIN pg_catalog.pg_description table_desc 
            ON table_desc.objoid = (SELECT oid FROM pg_catalog.pg_class WHERE relname = t.table_name)
            AND table_desc.objsubid = 0
        LEFT JOIN pg_catalog.pg_description col_desc 
            ON col_desc.objoid = (SELECT oid FROM pg_catalog.pg_class WHERE relname = t.table_name)
            AND col_desc.objsubid = c.ordinal_position
        WHERE t.table_schema = 'public'
        AND t.table_type = 'BASE TABLE'
        AND t.table_name IN ('policies', 'policy_conditions')
        ORDER BY t.table_name, c.ordinal_position;
        """
        
        cursor.execute(schema_query)
        schema_results = cursor.fetchall()

        # 스키마 정보를 문자열로 포맷팅 (코멘트 포함)
        schema_info = "PostgreSQL Database Schema:\n\n"
        current_table = None
        
        for row in schema_results:
            if current_table != row['table_name']:
                if current_table is not None:
                    schema_info += "\n"
                current_table = row['table_name']
                table_comment = f" -- {row['table_comment']}" if row['table_comment'] else ""
                schema_info += f"Table: {row['table_name']}{table_comment}\n"
            
            nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
            default = f"DEFAULT {row['column_default']}" if row['column_default'] else ""
            column_comment = f" -- {row['column_comment']}" if row['column_comment'] else ""
            schema_info += f"  - {row['column_name']}: {row['data_type']} {nullable} {default}{column_comment}\n"
        
        cursor.close()
        conn.close()
        
        return schema_info
        
    except Exception as e:
        logger.error(f"스키마 정보 가져오기 실패: {e}")
        return "스키마 정보를 가져올 수 없습니다."


def execute_postgresql_query(config, sql_query: str) -> Dict[str, Any]:
    """PostgreSQL 쿼리를 직접 실행하는 함수"""
    try:
        # config의 db_config를 사용하여 직접 연결
        conn = psycopg2.connect(
            host=config.db_config['host'],
            database=config.db_config['database'],
            user=config.db_config['user'],
            password=config.db_config['password'],
            port=config.db_config['port']
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 쿼리 실행
        cursor.execute(sql_query)
        results = cursor.fetchall()
        
        # 결과를 딕셔너리 형태로 변환
        result_data = [dict(row) for row in results]
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "data": result_data,
            "row_count": len(result_data)
        }
        
    except Exception as e:
        logger.error(f"PostgreSQL 쿼리 실행 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


def create_direct_sql_chain(config, classification_type, user_condition):
    """직접 SQL 쿼리를 생성하는 LLM 체인을 생성하는 함수"""
    
    # 데이터베이스 스키마 정보 가져오기
    schema_info = get_postgresql_schema(config)
    
    # SQL 쿼리 생성을 위한 프롬프트 템플릿
    sql_prompt = ChatPromptTemplate.from_messages([
        ("system", f"""당신은 PostgreSQL 전문가입니다. 주어진 자연어 질문을 바탕으로 정확한 PostgreSQL 쿼리를 생성해주세요.

**데이터베이스 스키마:**
{schema_info}


mrg_stts_cd -> ('기혼', '미혼', '제한없음')
plcy_major_cd -> ('인문계열', '자연계열', '사회계열', '상경계열', '이학계열', '공학계열', '예체능계열', '농산업계열', '제한없음')
job_cd -> ('재직자', '미취업자', '자영업자', '(예비)창업자', '영농종사자', '비정규직', '제한없음')
school_cd -> ('고졸 미만', '고교 재학', '고졸 예정', '고교 졸업', '대학 재학', '대졸 예정', '대학 졸업', '석·박사', '제한없음')
zip_cd -> string 값 (예: '전국', '서울특별시', '대구광역시', '경상북도', '전북특별자치도', '서울 구로구', '대구 달서구', '경기도 수원시', '경기도 수원시 팔달구')
earn_etc_cn -> string 값 (예: '중위소득 150% 이하', '월소득 200만원 이하')

**분류 정보:** {classification_type}
**조건 정보:** {user_condition}

**쿼리 생성 규칙:**
1. 반드시 PostgreSQL 문법을 사용하세요
2. 안전한 쿼리만 생성하세요 (SELECT문만 허용, INSERT/UPDATE/DELETE 금지)
3. 테이블명과 컬럼명을 정확히 사용하세요
5. LIMIT을 사용하여 결과 수를 10개로 제한하세요
6. 분류 정보로 policies 테이블의 lclsf_nm을 사용하여 필터링하세요
    - lclsf_nm 이 '일반'인 경우 policies 테이블의 lclsf_nm 컬럼을 '주거' 또는 '일자리'로 필터링합니다.
    - lclsf_nm 이 '일반'인 경우 policies 테이블의 lclsf_nm의 '주거', '일자리'를 각각 5개씩 반환합니다.
7. 나이 정보는 policies 테이블의 sprt_trgt_min_age, sprt_trgt_max_age 컬럼을 사용하여 필터링하세요
    - sprt_trgt_min_age와 sprt_trgt_max_age 가 0 인 경우는 필터링하지 않습니다.
    - 예: sprt_trgt_min_age <= {user_condition.age} AND sprt_trgt_max_age >= {user_condition.age} OR (sprt_trgt_min_age = 0 AND sprt_trgt_max_age = 0)
8. mrg_stts_cd 검색 시 IN (조건 정보,'제한없음') 형태로 필터링하세요
9. school_cd, plcy_major_cd, job_cd 검색 시 '제한없음'과 해당 조건을 필터링 하세요
    - 예 school_cd ILIKE '%대학 졸업%' OR school_cd = '제한없음'
    - 예 plcy_major_cd ILIKE '%인문계열%' OR plcy_major_cd = '제한없음'
10. zip_cd 검색 시 전국, 해당지역, 해당 지역의 상위 지역을 포함하여 필터링 해야 합니다.
    - zip_cd 데이터가 예를들을 '경기도 수원시 팔달구'이면 '경기도', '경기도 수원시', '경기도 수원시 팔달구' 데이터를 모두 포함해야 합니다.
    - 예 zip_cd ILIKE '%경기도 수원시 팔달구%' OR zip_cd ILIKE '%경기도 수원시%' OR zip_cd ILIKE '%경기도%' OR zip_cd = '전국'
11. earn_etc_cn은 유사도를 판단하는데 사용합니다.
    - 예 ORDER BY similarity(earn_etc_cn, 조건 정보의 earn_etc_cn) DESC
12. additional_requirement도 필터링은 하지 않고 add_aply_qlfcc_cn, ptcp_prp_trgt_cn 컬럼과 유사도 판단으로 사용합니다.
    - 예 ORDER BY similarity(add_aply_qlfcc_cn, additional_requirement) DESC, similarity(ptcp_prp_trgt_cn, additional_requirement) DESC
13. query_keywords는 policies 테이블의 plcy_nm, plcy_expl_cn 컬럼과 유사도 판단으로 사용합니다.
    - 예 ORDER BY similarity(plcy_nm, query_keywords) DESC, similarity(plcy_expl_cn, query_keywords) DESC
    - query_keywords 정렬은 반드시 사용을 해야 합니다.
14. policies 테이블의 모든 컬럼을 SELECT 하여 반환하세요
15. 사용자 조건과 제일 유사한 정책으로 정렬하도록 쿼리를 구성해주세요
    - 정렬 순서: zip_cd > mrg_stts_cd, school_cd, plcy_major_cd, job_cd > query_keywords >earn_etc_cn, additional_requirement
16. 필터링 할 때는 분류 정보, 조건 정보만 사용해서 쿼리를 구성해야 합니다

**주의사항:**
- 쿼리는 반드시 실행 가능한 형태여야 합니다
- 존재하지 않는 테이블이나 컬럼을 참조하지 마세요
- SQL injection을 방지하기 위해 안전한 쿼리만 생성하세요
- SELECT DISTINCT를 사용할 때 ORDER BY에 사용되는 모든 표현식은 SELECT 목록에 포함되어야 합니다
- similarity 함수나 복잡한 ORDER BY 표현식을 사용할 때는 SELECT DISTINCT 대신 일반 SELECT를 사용하세요
- 중복 제거가 필요한 경우 서브쿼리나 윈도우 함수를 사용하여 해결하세요

"""),
        ("human", "다음 질문에 PostgreSQL 쿼리를 생성해주세요: {query}")
    ])
    # 구조화된 출력을 위한 LLM 체인 (streaming 비활성화)
    llm_no_stream = config.thinking_model.bind(stream=False)
    structured_llm = llm_no_stream.with_structured_output(SQLQueryGeneration)
    sql_chain = sql_prompt | structured_llm
    
    return sql_chain


def build_graph() -> StateGraph:
    """LangGraph 워크플로우 구축"""
    # StateGraph 생성
    builder = StateGraph(GraphState)
    # 노드 추가
    builder.add_node("classify_query", classify_query_node)
    builder.add_node("extract_user_conditions", extract_user_conditions_node)
    builder.add_node("generate_sql_query", generate_sql_query_node)
    builder.add_node("generate_response", generate_response_node)
    builder.add_node("reject_query", reject_query_node)
    
    # 엣지 정의
    builder.add_edge(START, "classify_query")
    # 조건부 엣지: 분류 결과에 따라 라우팅
    builder.add_conditional_edges(
        "classify_query",
        route_after_classification,
        {
            "continue": "extract_user_conditions",
            "reject": "reject_query"
        }
    )
    builder.add_edge("extract_user_conditions", "generate_sql_query")
    builder.add_edge("generate_sql_query", "generate_response")
    builder.add_edge("generate_response", END)
    builder.add_edge("reject_query", END)
    
    return builder.compile()


# LangGraph Studio에서 사용할 그래프 인스턴스
graph = build_graph()
