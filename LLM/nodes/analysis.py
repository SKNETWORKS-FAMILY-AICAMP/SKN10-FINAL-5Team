"""
질의 분석 노드 - 사용자 질문을 분석하여 분류와 조건을 추출
"""
import logging
from typing import Dict, Any
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from models.graph_state import GraphState
from models.query_models import QueryAnalysis
from config.settings import YouthPolicyRAGConfig

logger = logging.getLogger(__name__)


class QueryAnalysisNode:
    """질의 분석 노드 클래스"""
    
    def __init__(self, config: YouthPolicyRAGConfig):
        self.config = config
        self._setup_analysis_chain()
    
    def _setup_analysis_chain(self):
        """분석 체인 설정"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 청년정책 질의 분석 전문가입니다. 
사용자의 질문을 분석하여 질의 분류와 개인 조건 추출을 동시에 수행해주세요.

**1. 질의 분류 (lclsf_nm):**
- '주거': 전월세 대출, 임대주택, 기숙사, 이사비 지원, 부동산 중개비 지원 등 관련 정책
- '일자리': 일자리, 창업, 취업, 전문인력양성, 훈련, 기업지원 등 관련 정책
- '일반': 정책과 관련한 일반적인 질문이나 정보 요청, 신청방법, 맞춤 정책 검색, 추천 등의 질문
- '기타': 그 외 정책과는 관계 없는 질문

**키워드 (query_keywords):**
- 사용자 질문에서 추출된 키워드, 정책 검색 시 유사도 판단에 사용됩니다.

**의도 (query_intent):**
- '맞춤 정책 검색': 사용자의 조건에 맞는 정책을 찾는 질문
- '정책 상세 설명': 특정 정책에 대한 자세한 설명을 요청하는 질문
- '기타': 그 외의 질문이나 요청

**2. 사용자 조건 추출:**
1. age: 나이 (숫자로)
2. mrg_stts_cd: 결혼 상태 ('기혼', '미혼')
3. plcy_major_cd: 전공 계열 ('인문계열', '자연계열', '사회계열', '상경계열', '이학계열', '공학계열', '예체능계열', '농산업계열')
4. job_cd: 취업 상태 ('재직자', '미취업자', '자영업자', '(예비)창업자', '영농종사자', '비정규직')
5. school_cd: 학력 상태 ('고졸 미만', '고교 재학', '고졸 예정', '고교 졸업', '대학 재학', '대졸 예정', '대학 졸업', '석·박사')
6. zip_cd: 거주지 (광역지자체, 기초지자체 형태로)
7. earn_etc_cn: 소득 요건 (구체적인 소득 수준이나 조건)
8. additional_requirement: 기초생활수급자, 한부모가정, 농업인, 중소기업 등 추가적인 조건

**추출 규칙:**
- 명시적으로 언급되지 않은 조건은 None으로 설정
- 거주지는 "서울특별시", "대구광역시", "경상북도", "전북특별자치도", "강원특별자치도", "서울특별시 구로구", "경기도 수원시 팔달구" 의 형태로 추출
- 소득은 "월소득 200만원 이하", "중위소득 150% 이하" 등의 형태로 추출
- classification_confidence는 분류의 명확성을 기준으로 평가
- extraction_confidence는 추출된 정보의 명확성과 완성도를 기준으로 평가"""),
            ("human", "다음 질문을 분석해주세요: {query}")
        ])
        
        llm_no_stream = self.config.thinking_model.bind(stream=False)
        structured_llm = llm_no_stream.with_structured_output(QueryAnalysis)
        self.analysis_chain = prompt | structured_llm
    
    def process(self, state: GraphState) -> GraphState:
        """질의 분석 처리"""
        try:
            logger.info("질의 분석 시작 (분류 + 조건 추출)")
            
            # 메시지에서 마지막 사용자 메시지 추출
            user_message = self._extract_user_message(state["messages"])
            
            if not user_message:
                raise ValueError("사용자 메시지를 찾을 수 없습니다.")
            
            # 질의 분석 실행
            query_analysis = self.analysis_chain.invoke({"query": user_message})
            logger.info(f"질의 분석 완료: {query_analysis}")
            
            return {
                **state,
                "query": user_message,
                "query_analysis": query_analysis
            }
            
        except Exception as e:
            logger.error(f"질의 분석 실패: {e}")
            return {
                **state,
                "error": f"질의 분석 실패: {str(e)}"
            }
    
    def _extract_user_message(self, messages) -> str:
        """메시지 리스트에서 사용자 메시지 추출"""
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                return message.content
        return None


# 노드 함수 (LangGraph 호환성을 위해)
def analyze_query_node(state: GraphState) -> GraphState:
    """질의 분석 노드 함수"""
    config = YouthPolicyRAGConfig()
    node = QueryAnalysisNode(config)
    return node.process(state)
