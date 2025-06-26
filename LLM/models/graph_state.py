"""
GraphState 정의 - LangGraph에서 사용하는 상태 모델
"""
from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from .query_models import QueryAnalysis


class GraphState(TypedDict):
    """그래프 상태 정의"""
    messages: Annotated[List[BaseMessage], add_messages]  # LangGraph Studio 호환성을 위한 메시지 리스트
    query: str  # 사용자 질의
    query_analysis: Optional[QueryAnalysis]  # 질의 분석 결과 (분류 + 조건 추출)
    generated_sql: Optional[str]  # 정책 검색을 위한 필터 쿼리
    sql_result: Optional[str]
    selected_policies: Optional[List[Dict[str, Any]]]  # LLM이 선정한 정책 목록 (딕셔너리 형태)
    final_response: Optional[str]  # 최종 답변
    error: Optional[str]  # 오류 메시지
    timestamp: str  # 처리 시각
