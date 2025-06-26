"""
LangGraph Studio용 청년정책 RAG 시스템 메인 파일
주거 관련 정책과 일자리 관련 정책에 대해서만 답변하고, 
그 외 질문에 대해서는 답변을 거부하는 시스템
"""
from graph.workflow import YouthPolicyRAGWorkflow
from utils.logging import setup_logging

# 로깅 설정
logger = setup_logging()

# LangGraph Studio에서 사용할 그래프 인스턴스
workflow = YouthPolicyRAGWorkflow()
graph = workflow.graph

if __name__ == "__main__":
    # 테스트 실행 코드
    from langchain_core.messages import HumanMessage
    
    test_input = {
        "messages": [HumanMessage(content="서울에 사는 25세 대학생입니다. 주거 지원 정책이 있나요?")],
        "timestamp": "2025-06-25"
    }
    
    try:
        result = workflow.invoke(test_input)
        print("=== 실행 결과 ===")
        print(f"최종 응답: {result.get('final_response', '응답 없음')}")
        print(f"선정된 정책 수: {len(result.get('selected_policies', []))}")
    except Exception as e:
        logger.error(f"테스트 실행 실패: {e}")
        print(f"오류 발생: {e}")
