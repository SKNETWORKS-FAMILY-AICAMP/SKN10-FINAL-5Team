"""
응답 생성 노드 - SQL 결과를 바탕으로 자연어 응답 생성
"""
import logging
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from models.graph_state import GraphState
from models.query_models import PolicySelection
from config.settings import YouthPolicyRAGConfig

logger = logging.getLogger(__name__)


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
        
        config = YouthPolicyRAGConfig()
        query_analysis = state["query_analysis"]
        query = state["query"]
        sql_result = state.get("sql_result", [])
        
        # 1단계: 정책 선정을 위한 LLM 호출
        policy_selection_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 청년정책 전문가입니다. 
검색된 정책 데이터를 분석하여 사용자의 질문과 조건에 가장 적합한 정책들을 선정하고 친절한 답변을 제공해주세요.

**분류 정보:** {classification_type}
**사용자 질문:** {user_query}
**사용자 조건:** {user_conditions}
**검색된 정책 데이터:** {search_data}

**정책 선정 가이드라인:**
1. 사용자의 조건(나이, 거주지, 학력, 취업상태 등)에 가장 적합한 정책을 우선 선정
2. 사용자 질문의 키워드와 관련성이 높은 정책을 선정
3. 최대 10개까지의 정책을 선정
4. 선정된 각 정책에 대해 plcy_no, plcy_nm, plcy_expln_nm, lclsf_nm, mclsf_nm, zip_cd, inq_cnt 정보를 정확히 추출

**주의사항:**
- 검색 결과에서 실제 존재하는 정책만 선정
- 정책 정보는 검색 결과에서 정확히 추출

**답변 가이드라인:**
1. 검색 결과를 바탕으로 정확한 정보를 제공하세요
2. 정책명, 지원내용, 신청방법 등을 구체적으로 안내하세요
3. 사용자의 조건에 맞는 정책을 우선적으로 추천하세요
4. 검색 결과가 없거나 부족한 경우 그 이유를 설명하세요
5. 친근하고 도움이 되는 톤으로 답변하세요
6. 필요시 추가 문의 방법이나 관련 기관 정보를 제공하세요
7. 답변 시 markdown 형식을 사용하여 가독성을 높이세요
8. 적절한 이모지를 사용하여 답변을 더 친근하게 만드세요
9. 주거정책과 일자리 정책을 구분하여 답변하세요
10. 2개 이상의 정책목록 나열 시 구분할 수 있도록 정책 앞과 뒤에 --- 형태로 구분하세요
11. query_intent가 '정책 상세 설명'인 경우 해당 정책에 대해 사용자 질문에 답변을 제공하세요
"""),
            ("human", "위 검색 결과에서 사용자에게 적합한 정책들을 선정하고 사용자 질문에 대한 답변을 생성해주세요.")
        ])
        
        # 정책 선정을 위한 구조화된 LLM 체인
        llm_no_stream = config.chat_llm.bind(stream=False)
        policy_selection_llm = llm_no_stream.with_structured_output(PolicySelection)
        policy_selection_chain = policy_selection_prompt | policy_selection_llm
        
        # 정책 선정 실행
        policy_selection_result = policy_selection_chain.invoke({
            "classification_type": query_analysis.lclsf_nm,
            "user_query": query,
            "user_conditions": str(query_analysis),
            "search_data": str(sql_result)
        })
        
        logger.info(f"정책 선정 및 응답 완료: {len(policy_selection_result.selected_policies)}개 정책 선정")
        

        # 메시지 리스트에 AI 응답 추가
        ai_message = AIMessage(content=policy_selection_result.final_response)
        
        return {
            **state,
            "messages": state["messages"] + [ai_message],
            "selected_policies": policy_selection_result.selected_policies,
            "final_response": policy_selection_result.final_response
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
