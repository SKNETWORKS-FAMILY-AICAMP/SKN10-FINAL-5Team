"""
데이터베이스 연결 관리 모듈
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """데이터베이스 연결 및 관리 클래스"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
    
    @contextmanager
    def get_connection(self):
        """데이터베이스 연결 컨텍스트 매니저"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"데이터베이스 연결 오류: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, sql_query: str) -> Dict[str, Any]:
        """SQL 쿼리 실행"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute(sql_query)
                results = cursor.fetchall()
                result_data = [dict(row) for row in results]
                
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
