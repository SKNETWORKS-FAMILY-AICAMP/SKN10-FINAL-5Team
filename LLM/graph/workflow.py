"""
LangGraph 워크플로우 구성
"""
from langgraph.graph import StateGraph, START, END

from models.graph_state import GraphState
from nodes.analysis import analyze_query_node
from nodes.sql_generation import generate_sql_query_node
from nodes.response import generate_response_node
from nodes.routing import reject_query_node, route_after_analysis


class YouthPolicyRAGWorkflow:
    """청년정책 RAG 워크플로우 클래스"""
    
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """LangGraph 워크플로우 구축"""
        builder = StateGraph(GraphState)
        
        # 노드 추가
        builder.add_node("analyze_query", analyze_query_node)
        builder.add_node("generate_sql_query", generate_sql_query_node)
        builder.add_node("generate_response", generate_response_node)
        builder.add_node("reject_query", reject_query_node)
        
        # 엣지 정의
        builder.add_edge(START, "analyze_query")
        builder.add_conditional_edges(
            "analyze_query",
            route_after_analysis,
            {
                "continue": "generate_sql_query",
                "reject": "reject_query"
            }
        )
        builder.add_edge("generate_sql_query", "generate_response")
        builder.add_edge("generate_response", END)
        builder.add_edge("reject_query", END)
        
        return builder.compile()
    
    def invoke(self, input_data):
        """워크플로우 실행"""
        return self.graph.invoke(input_data)


def build_graph() -> StateGraph:
    """그래프 빌더 함수 (기존 호환성 유지)"""
    workflow = YouthPolicyRAGWorkflow()
    return workflow.graph
