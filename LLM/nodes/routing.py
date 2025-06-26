"""
라우팅 로직 - 분석 결과에 따른 경로 결정 및 질의 거부 처리
"""
import logging
from typing import Literal
from langchain_core.messages import AIMessage

from models.graph_state import GraphState

logger = logging.getLogger(__name__)


def route_after_analysis(state: GraphState) -> Literal["continue", "reject"]:
    """분석 결과에 따른 라우팅 결정"""
    if state.get("error"):
        return "reject"
    
    query_analysis = state.get("query_analysis")
    if not query_analysis:
        return "reject"
    
    # 주거 또는 일자리 관련이고 신뢰도가 임계값 이상인 경우만 계속 진행
    if query_analysis.lclsf_nm in ["주거", "일자리", "일반"]:
        logger.info(f"질의 승인: {query_analysis.lclsf_nm}")
        return "continue"
    else:
        logger.info(f"질의 거부: {query_analysis.lclsf_nm}")
        return "reject"


def reject_query_node(state: GraphState) -> GraphState:
    """질의 거부 노드"""
    logger.info("질의 거부 처리")
    
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
