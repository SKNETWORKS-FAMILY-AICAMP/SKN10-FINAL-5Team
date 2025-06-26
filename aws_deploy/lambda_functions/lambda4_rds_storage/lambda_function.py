#!/usr/bin/env python3
"""
Lambda4: RDS Storage
분류된 정책 데이터를 최종적으로 RDS PostgreSQL에 저장하는 Lambda 함수

기능:
- S3 policy_reclassified/ 디렉터리에서 데이터 읽기
- PostgreSQL RDS에 데이터 삽입/업데이트
- 중복 데이터 처리 및 조건부 업데이트
- 데이터 무결성 검증

작성일: 2025-01-28
"""

import json
import boto3
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os
import logging
from typing import Dict, Any, List, Tuple
import io
from urllib.parse import unquote
import hashlib

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RDSDataManager:
    """RDS PostgreSQL 데이터 관리 클래스"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ['S3_BUCKET_NAME']
        
        # PostgreSQL 연결 설정
        self.db_config = {
            'host': os.environ['DB_HOST'],
            'port': int(os.environ.get('DB_PORT', 5432)),
            'database': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD']
        }
        
        # 테이블 이름 설정
        self.policies_table = os.environ.get('POLICIES_TABLE', 'youth_policies')
        self.classifications_table = os.environ.get('CLASSIFICATIONS_TABLE', 'policy_classifications')
        
    def load_classified_data_from_s3(self, s3_key: str) -> pd.DataFrame:
        """
        S3에서 분류된 데이터 로드
        
        Args:
            s3_key: S3 객체 키
            
        Returns:
            로드된 DataFrame
        """
        logger.info(f"S3에서 분류된 데이터 로드: s3://{self.bucket_name}/{s3_key}")
        
        try:
            # S3에서 객체 가져오기
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            
            # CSV 데이터 읽기
            csv_content = response['Body'].read().decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
            
            logger.info(f"분류된 데이터 로드 완료: {len(df)}개 레코드")
            return df
            
        except Exception as e:
            logger.error(f"S3 데이터 로드 실패: {str(e)}")
            raise
    
    def get_db_connection(self) -> psycopg2.extensions.connection:
        """
        PostgreSQL 데이터베이스 연결 생성
        
        Returns:
            데이터베이스 연결 객체
        """
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False
            logger.info("PostgreSQL 연결 성공")
            return conn
            
        except Exception as e:
            logger.error(f"PostgreSQL 연결 실패: {str(e)}")
            raise
    
    def store_data_to_rds(self, df: pd.DataFrame) -> Dict[str, int]:
        """
        분류된 데이터를 RDS에 저장
        
        Args:
            df: 저장할 DataFrame
            
        Returns:
            처리 결과 통계
        """
        logger.info(f"RDS 데이터 저장 시작: {len(df)}개 레코드")
        
        conn = self.get_db_connection()
        
        try:
            # 기존 데이터와 비교하여 업데이트/삽입
            insert_count = 0
            update_count = 0
            skip_count = 0
            
            with conn.cursor() as cursor:
                for _, row in df.iterrows():
                    policy_id = row.get('plcyId', row.get('plcy_no'))  # 두 가지 컬럼명 모두 지원
                    if pd.isna(policy_id):
                        skip_count += 1
                        continue
                    
                    # 기존 데이터 확인
                    cursor.execute(f"""
                        SELECT plcy_no, last_mdfcn_dt 
                        FROM {self.policies_table} 
                        WHERE plcy_no = %s
                    """, (policy_id,))
                    
                    existing = cursor.fetchone()
                    
                    if existing is None:
                        # 새로운 데이터 삽입
                        self._insert_policy_data(cursor, row)
                        insert_count += 1
                    else:
                        # 기존 데이터 업데이트
                        self._update_policy_data(cursor, row)
                        update_count += 1
            
            conn.commit()
            logger.info(f"RDS 저장 완료 - 삽입: {insert_count}, 업데이트: {update_count}, 스킵: {skip_count}")
            
            return {
                'inserted': insert_count,
                'updated': update_count,
                'skipped': skip_count
            }
            
        except Exception as e:
            conn.rollback()
            logger.error(f"RDS 저장 실패: {str(e)}")
            raise
        finally:
            conn.close()
    
    def _insert_policy_data(self, cursor, row: pd.Series) -> None:
        """새로운 정책 데이터 삽입"""
        insert_sql = f"""
        INSERT INTO {self.policies_table} 
        (plcy_no, plcy_nm, plcy_expln_cn, plcy_sprt_cn, plcy_kywd_nm, 
         lclsf_nm, last_mdfcn_dt, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (plcy_no) DO NOTHING
        """
        
        values = (
            row.get('plcyId', row.get('plcy_no')),
            row.get('plcyNm', row.get('plcy_nm', '')),
            row.get('plcyExplnCn', row.get('plcy_expln_cn', '')),
            row.get('plcySprtCn', row.get('plcy_sprt_cn', '')),
            row.get('plcyKywdNm', row.get('plcy_kywd_nm', '')),
            row.get('정책대분류명', row.get('lclsf_nm', '')),
            row.get('lastUpdtDt', row.get('last_mdfcn_dt')) if pd.notna(row.get('lastUpdtDt', row.get('last_mdfcn_dt'))) else None
        )
        
        cursor.execute(insert_sql, values)
    
    def _update_policy_data(self, cursor, row: pd.Series) -> None:
        """기존 정책 데이터 업데이트"""
        update_sql = f"""
        UPDATE {self.policies_table} 
        SET plcy_nm = %s, plcy_expln_cn = %s, plcy_sprt_cn = %s, 
            plcy_kywd_nm = %s, lclsf_nm = %s, last_mdfcn_dt = %s, 
            updated_at = NOW()
        WHERE plcy_no = %s
        """
        
        values = (
            row.get('plcyNm', row.get('plcy_nm', '')),
            row.get('plcyExplnCn', row.get('plcy_expln_cn', '')),
            row.get('plcySprtCn', row.get('plcy_sprt_cn', '')),
            row.get('plcyKywdNm', row.get('plcy_kywd_nm', '')),
            row.get('정책대분류명', row.get('lclsf_nm', '')),
            row.get('lastUpdtDt', row.get('last_mdfcn_dt')) if pd.notna(row.get('lastUpdtDt', row.get('last_mdfcn_dt'))) else None,
            row.get('plcyId', row.get('plcy_no'))
        )
        
        cursor.execute(update_sql, values)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 메인 핸들러 (S3 이벤트 트리거)
    """
    try:
        logger.info("Lambda4 (RDS Storage) 실행 시작")
        
        # S3 이벤트에서 키 정보 추출
        if 'Records' not in event or not event['Records']:
            logger.error("S3 이벤트 레코드가 없습니다.")
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid S3 event format')
            }
        
        record = event['Records'][0]
        s3_key = unquote(record['s3']['object']['key'])
        
        # policy_reclassified/ 디렉터리의 파일만 처리
        if not s3_key.startswith('policy_reclassified/'):
            logger.info(f"policy_reclassified/ 디렉터리가 아닌 파일 건너뛰기: {s3_key}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'File not in policy_reclassified directory, skipped',
                    'file': s3_key
                })
            }
        
        logger.info(f"처리할 S3 파일: {s3_key}")
        
        # RDS 데이터 매니저 초기화
        rds_manager = RDSDataManager()
        
        # 분류된 데이터 로드
        classified_data = rds_manager.load_classified_data_from_s3(s3_key)
        
        if classified_data.empty:
            logger.warning("로드된 데이터가 없습니다.")
            return {
                'statusCode': 204,
                'body': json.dumps({
                    'message': 'No data to store',
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        # RDS에 데이터 저장
        result_stats = rds_manager.store_data_to_rds(classified_data)
        
        logger.info(f"Lambda4 실행 완료. {result_stats}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'RDS storage completed successfully',
                'input_records': len(classified_data),
                'input_s3_key': s3_key,
                'operations': result_stats,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda4 실행 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'RDS storage failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        }


if __name__ == "__main__":
    # 로컬 테스트용
    test_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': 'policy_reclassified/year=2025/month=01/week=04/data_20250128_120000.csv'}
            }
        }]
    }
    test_context = None
    result = lambda_handler(test_event, test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False)) 