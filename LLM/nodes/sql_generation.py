"""
SQL 쿼리 생성 및 실행 노드
"""
import logging
from models.graph_state import GraphState
from config.settings import YouthPolicyRAGConfig
from chains.llm_chains import create_direct_sql_chain
from database.queries import execute_postgresql_query

logger = logging.getLogger(__name__)


def generate_sql_query_node(state: GraphState) -> GraphState:
    """SQL 쿼리를 생성하고 실행하는 노드"""
    logger.info("SQL 쿼리 생성 및 실행 시작 노드")
    
    query_analysis = state["query_analysis"]
    query = state["query"]
    config = YouthPolicyRAGConfig()
        
    try:
        # 직접 SQL 쿼리 생성 체인 생성
        sql_chain = create_direct_sql_chain(config, query_analysis)
        
        # SQL 쿼리 생성
        logger.info("SQL 쿼리 생성 중...")
        sql_generation = sql_chain.invoke({"query": query})
        
        logger.info(f"SQL 쿼리 생성 완료.")
        
        # SQL 쿼리 실행
        sql_result = execute_postgresql_query(config, sql_generation.sql_query)
        
        if not sql_result["success"]:
            raise Exception(f"SQL 실행 실패: {sql_result['error']}")
        
        logger.info(f"쿼리 실행 완료: {sql_result['row_count']}개 결과 반환")
        
        return {
            **state,
            "generated_sql": sql_generation.sql_query,
            "sql_result": sql_result['data'],
        }
        
    except Exception as e:
        logger.error(f"SQL 쿼리 처리 실패: {e}")
        error_message = f"정책 검색 중 오류가 발생했습니다: {str(e)}"
        return {
            **state,
            "error": error_message
        }
