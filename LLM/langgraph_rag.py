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
import psycopg2
from psycopg2.extras import RealDictCursor
import openai
from datetime import datetime
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from pydantic import BaseModel, Field

# LangSmith imports
from langsmith import traceable
from langsmith.wrappers import wrap_openai

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class QueryClassification(BaseModel):
    """질의 분류를 위한 구조화된 출력 모델"""
    category: Literal["housing", "job", "other"] = Field(
        description="질의 카테고리: housing(주거), job(일자리), other(기타)"
    )
    subcategory: Optional[str] = Field(
        default=None,
        description="중분류: housing의 경우 'financial_support', 'subsidy_support', 'housing_support' 중 하나, job의 경우 'startup', 'training', 'employment_support' 중 하나"
    )
    confidence: float = Field(
        description="분류 신뢰도 (0.0-1.0)", 
        ge=0.0, 
        le=1.0
    )
    reasoning: str = Field(
        description="분류 근거 설명"
    )


class GraphState(TypedDict):
    """그래프 상태 정의"""
    messages: Annotated[List[BaseMessage], add_messages]  # LangGraph Studio 호환성을 위한 메시지 리스트
    query: str  # 사용자 질의
    classification: Optional[QueryClassification]  # 질의 분류 결과
    embedding: Optional[List[float]]  # 질의 임베딩
    policies: Optional[List[Dict[str, Any]]]  # 검색된 정책들
    policies_context: Optional[str]  # LLM용 정책 컨텍스트
    final_response: Optional[str]  # 최종 답변
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
        self.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', 0.7))
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
        self.confidence_threshold = 0.7  # 분류 신뢰도 임계값
        
        # OpenAI 클라이언트 설정
        openai.api_key = self.openai_api_key
        
        # LangSmith 래퍼 설정
        self.wrapped_openai = openai
        if os.getenv("LANGSMITH_API_KEY") and os.environ.get("LANGCHAIN_TRACING_V2") == "true":
            try:
                self.wrapped_openai = wrap_openai(openai)
                logger.info("LangSmith 추적이 활성화되었습니다.")
            except Exception as e:
                logger.warning(f"LangSmith 초기화 실패: {e}")


# 전역 설정 인스턴스
config = YouthPolicyRAGConfig()


@traceable
def classify_query_node(state: GraphState) -> GraphState:
    """질의 분류 노드"""
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
        
        # 구조화된 출력을 위한 시스템 프롬프트
        system_prompt = """
당신은 청년정책 질의 분류 전문가입니다. 
사용자의 질문을 다음과 같이 대분류와 중분류로 분류해주세요:

**대분류:**
1. housing: 주거 관련 정책
2. job: 일자리 관련 정책  
3. other: 그 외 모든 질문

**중분류 (housing인 경우):**
- financial_support: 대출, 이자, 전월세 등 금융지원 (전세자금 대출, 임차보증금 대출, 대출이자 지원 등)
- subsidy_support: 이사비, 부동산 중개비 등 보조금지원 (중개수수료 지원, 이사비 지원, 월세 보조금 등)
- housing_support: 임대주택, 기숙사 등 주거지원 (청년 임대주택, 기숙사, 주거공간 제공 등)

**중분류 (job인 경우):**
- startup: 창업 (창업 지원, 창업자금, 창업 교육, 창업보육센터 등)
- training: 전문인력양성, 훈련 (직업 훈련, 기술 교육, 자격증 취득 지원, 역량강화 등)
- employment_support: 취업 전후 지원 (취업 지원, 구직활동 지원, 취업 후 정착 지원, 인턴십 등)

**중분류 (other인 경우):**
- null (중분류 없음)

주거와 일자리 관련 키워드를 정확히 식별하고, 애매한 경우에는 other로 분류하세요.

결과를 다음 JSON 형식으로 출력해주세요:
{
    "category": "housing|job|other",
    "subcategory": "financial_support|subsidy_support|housing_support|startup|training|employment_support|null",
    "confidence": 0.0~1.0,
    "reasoning": "분류 근거 설명"
}
"""
        
        user_prompt = f"다음 질문을 분류하고 JSON 형식으로 결과를 제공해주세요: {user_message}"
        
        response = config.wrapped_openai.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
        )
        
        # JSON 응답 파싱
        response_json = json.loads(response.choices[0].message.content)
        
        # subcategory 처리 (null인 경우 None으로 변환)
        subcategory = response_json.get("subcategory")
        if subcategory == "null":
            subcategory = None
        
        classification = QueryClassification(
            category=response_json.get("category", "other"),
            subcategory=subcategory,
            confidence=response_json.get("confidence", 0.0),
            reasoning=response_json.get("reasoning", "분류 근거 없음")
        )
        
        logger.info(f"질의 분류 완료: {classification.category}/{classification.subcategory} (신뢰도: {classification.confidence})")
        
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
    if (classification.category in ["housing", "job"] and 
        classification.confidence >= config.confidence_threshold):
        logger.info(f"질의 승인: {classification.category} (신뢰도: {classification.confidence})")
        return "continue"
    else:
        logger.info(f"질의 거부: {classification.category} (신뢰도: {classification.confidence})")
        return "reject"


@traceable
def generate_embedding_node(state: GraphState) -> GraphState:
    """임베딩 생성 노드"""
    try:
        logger.info("임베딩 생성 시작")
        
        response = config.wrapped_openai.embeddings.create(
            input=state["query"],
            model=config.embedding_model
        )
        embedding = response.data[0].embedding
        
        logger.info(f"임베딩 생성 완료: {len(embedding)}차원")
        
        return {
            **state,
            "embedding": embedding
        }
        
    except Exception as e:
        logger.error(f"임베딩 생성 실패: {e}")
        return {
            **state,
            "error": f"임베딩 생성 실패: {str(e)}"
        }


@traceable
def search_policies_node(state: GraphState) -> GraphState:
    """정책 검색 노드"""
    try:
        logger.info("정책 검색 시작")
        
        embedding = state["embedding"]
        if not embedding:
            raise ValueError("임베딩이 없습니다.")
        
        # 데이터베이스 연결 및 검색
        conn = psycopg2.connect(**config.db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 분류에 따른 필터링 추가
        classification = state["classification"]
        category_filter = ""
        
        if classification.category == "housing":
            # 주거 관련 정책 필터
            base_filter = "p.lclsf_nm = '주거'"
            
            # 중분류에 따른 추가 필터링
            if classification.subcategory == "financial_support":
                category_filter = f"""
                AND (
                    {base_filter}
                    AND (
                        p.mclsf_nm = '대출, 이자, 전월세 등 금융지원'
                    )
                )
                """
            elif classification.subcategory == "subsidy_support":
                category_filter = f"""
                AND (
                    {base_filter}
                    AND (
                        p.mclsf_nm = '이사비, 부동산 중개비 등 보조금지원'
                    )
                )
                """
            elif classification.subcategory == "housing_support":
                category_filter = f"""
                AND (
                    {base_filter}
                    AND (
                        p.mclsf_nm = '임대주택, 기숙사 등 주거지원'
                    )
                )
                """
            else:
                category_filter = f"""
                AND (
                    {base_filter}
                )
                """
                
        elif classification.category == "job":
            # 일자리 관련 정책 필터
            base_filter = "p.lclsf_nm = '일자리'"
            
            # 중분류에 따른 추가 필터링
            if classification.subcategory == "startup":
                category_filter = f"""
                AND (
                    {base_filter}
                    AND (
                        p.mclsf_nm = '창업'
                    )
                )
                """
            elif classification.subcategory == "training":
                category_filter = f"""
                AND (
                    {base_filter}
                    AND (
                        p.mclsf_nm = '전문인력양성, 훈련'
                    )
                )
                """
            elif classification.subcategory == "employment_support":
                category_filter = f"""
                AND (
                    {base_filter}
                    AND (
                        p.mclsf_nm = '취업 전후 지원'
                    )
                )
                """
            else:
                category_filter = f"""
                AND (
                    {base_filter}
                )
                """
        
        search_query = f"""
        SELECT 
            -- 기본 정책 정보
            p.plcy_no,
            p.plcy_nm,
            p.plcy_expln_cn,
            p.plcy_sprt_cn,
            p.plcy_aply_mthd_cn,
            p.srng_mthd_cn,
            p.sbmsn_dcmnt_cn,
            p.etc_mttr_cn,
            p.inq_cnt,
            p.aply_bgng_ymd,
            p.aply_end_ymd,
            
            -- 정책 조건 정보
            p.sprt_trgt_min_age,
            p.sprt_trgt_max_age,
            p.mrg_stts_cd,
            p.plcy_major_cd,
            p.job_cd,
            p.school_cd,
            p.zip_cd,
            p.earn_cnd_se_cd,
            p.earn_etc_cn,
            p.add_aply_qlfcc_cn,
            p.ptcp_prp_trgt_cn,
            
            -- 정책 메타데이터 정보
            p.lclsf_nm,
            p.mclsf_nm,
            p.plcy_pvsn_mthd_cd,
            p.plcy_kywd_nm,
            p.sprvsn_inst_cd_nm,
            p.oper_inst_cd_nm,
            p.aply_prd_se_cd,
            p.biz_prd_se_cd,
            p.biz_prd_bgng_ymd,
            p.biz_prd_end_ymd,
            p.biz_prd_etc_cn,
            p.s_biz_cd,
            
            -- 정책 URL 정보
            p.aply_url_addr,
            p.ref_url_addr1,
            p.ref_url_addr2,
            
            -- 유사도 점수
            (1 - (pe.embedding <=> %s::vector)) AS similarity_score
        FROM policies p
        JOIN policy_embeddings pe ON p.plcy_no = pe.plcy_no
        WHERE (1 - (pe.embedding <=> %s::vector)) >= %s
        {category_filter}
        ORDER BY pe.embedding <=> %s::vector
        LIMIT %s;
        """
        
        embedding_str = str(embedding)
        cursor.execute(search_query, (
            embedding_str, embedding_str, config.similarity_threshold,
            embedding_str, config.top_k
        ))
        
        results = cursor.fetchall()
        
        # 결과 처리
        policies = []
        for row in results:
            policy = dict(row)
            # 날짜 형식 변환
            date_fields = ['aply_bgng_ymd', 'aply_end_ymd', 'biz_prd_bgng_ymd', 'biz_prd_end_ymd']
            for field in date_fields:
                if policy.get(field):
                    policy[field] = policy[field].strftime('%Y-%m-%d') if policy[field] else None
            policies.append(policy)
        
        # 정책 컨텍스트 생성
        policies_context = format_policies_for_llm(policies)
        
        cursor.close()
        conn.close()
        
        logger.info(f"정책 검색 완료: {len(policies)}개 정책 발견")
        
        return {
            **state,
            "policies": policies,
            "policies_context": policies_context
        }
        
    except Exception as e:
        logger.error(f"정책 검색 실패: {e}")
        return {
            **state,
            "error": f"정책 검색 실패: {str(e)}"
        }


def format_policies_for_llm(policies: List[Dict[str, Any]]) -> str:
    """검색된 정책들을 LLM용 JSON 형식으로 포맷팅"""
    formatted_policies = []
    
    for policy in policies:
        formatted_policy = {
            # 기본 정책 정보
            "정책번호": policy.get('plcy_no'),
            "정책명": policy.get('plcy_nm'),
            "정책설명": policy.get('plcy_expln_cn'),
            "지원내용": policy.get('plcy_sprt_cn'),
            "신청방법": policy.get('plcy_aply_mthd_cn'),
            "심사방법": policy.get('srng_mthd_cn'),
            "제출서류": policy.get('sbmsn_dcmnt_cn'),
            "기타사항": policy.get('etc_mttr_cn'),
            "조회수": policy.get('inq_cnt'),
            
            # 신청 및 사업 기간
            "신청기간": {
                "시작일": policy.get('aply_bgng_ymd'),
                "종료일": policy.get('aply_end_ymd'),
                "기간구분코드": policy.get('aply_prd_se_cd')
            },
            "사업기간": {
                "시작일": policy.get('biz_prd_bgng_ymd'),
                "종료일": policy.get('biz_prd_end_ymd'),
                "기간구분코드": policy.get('biz_prd_se_cd'),
                "기타내용": policy.get('biz_prd_etc_cn')
            },
            
            # 지원 대상 조건
            "지원대상연령": {
                "최소": policy.get('sprt_trgt_min_age'),
                "최대": policy.get('sprt_trgt_max_age')
            },
            "결혼상태코드": policy.get('mrg_stts_cd'),
            "전공요건코드": policy.get('plcy_major_cd'),
            "취업요건코드": policy.get('job_cd'),
            "학력요건코드": policy.get('school_cd'),
            "거주지역코드": policy.get('zip_cd'),
            "소득조건": {
                "구분코드": policy.get('earn_cnd_se_cd'),
                "기타내용": policy.get('earn_etc_cn')
            },
            "추가신청자격요건": policy.get('add_aply_qlfcc_cn'),
            "참여제안대상내용": policy.get('ptcp_prp_trgt_cn'),
            
            # 정책 분류 및 메타데이터
            "정책분류": {
                "대분류": policy.get('lclsf_nm'),
                "중분류": policy.get('mclsf_nm')
            },
            "정책제공방법코드": policy.get('plcy_pvsn_mthd_cd'),
            "키워드": policy.get('plcy_kywd_nm'),
            "주관기관": policy.get('sprvsn_inst_cd_nm'),
            "운영기관": policy.get('oper_inst_cd_nm'),
            "정책특화요건코드": policy.get('s_biz_cd'),
            
            # URL 정보
            "관련URL": {
                "신청URL": policy.get('aply_url_addr'),
                "참고URL1": policy.get('ref_url_addr1'),
                "참고URL2": policy.get('ref_url_addr2')
            },
            
            # 시스템 정보
            "유사도점수": round(policy.get('similarity_score', 0), 4)
        }
        formatted_policies.append(formatted_policy)
    
    return json.dumps(formatted_policies, ensure_ascii=False, indent=2)


@traceable
def generate_response_node(state: GraphState) -> GraphState:
    """최종 답변 생성 노드"""
    try:
        logger.info("최종 답변 생성 시작")
        
        policies = state.get("policies", [])
        policies_context = state.get("policies_context", "")
        classification = state.get("classification")
        
        if not policies:
            response = f"""죄송합니다. '{state['query']}'에 대한 관련 {classification.category} 정책을 찾을 수 없습니다.

다른 키워드로 다시 검색해보시거나, 더 구체적인 질문을 해주시면 도움을 드리겠습니다."""
        else:
            system_prompt = f"""
당신은 청년정책 전문 상담사입니다. 
사용자가 {classification.category}({'주거' if classification.category == 'housing' else '일자리'}) 관련 정책에 대해 질문했습니다.

제공된 정책 정보를 바탕으로 정확하고 도움이 되는 답변을 제공해주세요.

답변 시 다음 사항을 고려해주세요:
1. 정책번호와 정책명을 명확히 포함하세요.
2. 제공된 정책 정보에 없는 내용은 추측하지 말고, 정확한 정보만을 바탕으로 답변해주세요.
"""
            
            user_prompt = f"""
사용자 질문: {state['query']}

관련 정책 정보:
{policies_context}

위 정책 정보를 바탕으로 사용자의 질문에 대해 상세하고 도움이 되는 답변을 제공해주세요.
"""
            
            response_obj = config.wrapped_openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            response = response_obj.choices[0].message.content
        
        logger.info("최종 답변 생성 완료")
        
        # 메시지 리스트에 AI 응답 추가
        ai_message = AIMessage(content=response)
        
        return {
            **state,
            "messages": state["messages"] + [ai_message],
            "final_response": response
        }
        
    except Exception as e:
        logger.error(f"답변 생성 실패: {e}")
        error_message = f"답변 생성 실패: {str(e)}"
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

현재 질문은 '{classification.category if classification else '분류불가'}' 카테고리로 분류되어 답변을 드릴 수 없습니다.

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


def build_graph() -> StateGraph:
    """LangGraph 워크플로우 구축"""
    # StateGraph 생성
    builder = StateGraph(GraphState)
    
    # 노드 추가
    builder.add_node("classify_query", classify_query_node)
    builder.add_node("generate_embedding", generate_embedding_node)
    builder.add_node("search_policies", search_policies_node)
    builder.add_node("generate_response", generate_response_node)
    builder.add_node("reject_query", reject_query_node)
    
    # 엣지 정의
    builder.add_edge(START, "classify_query")
    
    # 조건부 엣지: 분류 결과에 따라 라우팅
    builder.add_conditional_edges(
        "classify_query",
        route_after_classification,
        {
            "continue": "generate_embedding",
            "reject": "reject_query"
        }
    )
    
    builder.add_edge("generate_embedding", "search_policies")
    builder.add_edge("search_policies", "generate_response")
    builder.add_edge("generate_response", END)
    builder.add_edge("reject_query", END)
    
    return builder.compile()


# LangGraph Studio에서 사용할 그래프 인스턴스
graph = build_graph()
