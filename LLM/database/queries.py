"""
데이터베이스 쿼리 실행 관련 유틸리티 함수
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def execute_postgresql_query(config, sql_query: str) -> Dict[str, Any]:
    """PostgreSQL 쿼리를 직접 실행하는 함수"""
    try:
        conn = psycopg2.connect(**config.db_config)
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


def get_postgresql_schema(config) -> str:
    """PostgreSQL 데이터베이스 스키마 정보를 가져오는 함수"""
    try:
        # 테이블 스키마 정보 쿼리 (policies 테이블만, 코멘트 포함)
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
        AND t.table_name IN ('policies')
        ORDER BY t.table_name, c.ordinal_position;
        """
        conn = psycopg2.connect(**config.db_config)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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
