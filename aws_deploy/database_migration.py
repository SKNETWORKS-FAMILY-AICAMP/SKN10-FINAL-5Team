#!/usr/bin/env python3
"""
AWS RDS PostgreSQL 데이터베이스 마이그레이션 스크립트
로컬 PostgreSQL에서 AWS RDS로 정책 데이터를 마이그레이션합니다.
"""

import psycopg2
import pandas as pd
import os
import sys
import json
import logging
from datetime import datetime
import boto3
from psycopg2.extras import RealDictCursor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        self.local_conn = None
        self.rds_conn = None
        self.secrets_client = boto3.client('secretsmanager', region_name='ap-northeast-2')
        
    def get_rds_credentials(self, secret_name):
        """Secrets Manager에서 RDS 자격 증명을 가져옵니다."""
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        except Exception as e:
            logger.error(f"RDS 자격 증명 가져오기 실패: {str(e)}")
            raise
    
    def connect_local_db(self):
        """로컬 PostgreSQL에 연결합니다."""
        try:
            self.local_conn = psycopg2.connect(
                dbname="postgres",
                user="postgres",
                password="postgres",
                host="localhost",
                port="5432"
            )
            logger.info("로컬 PostgreSQL 연결 성공")
        except Exception as e:
            logger.error(f"로컬 PostgreSQL 연결 실패: {str(e)}")
            raise
    
    def connect_rds(self, rds_endpoint, db_password):
        """AWS RDS에 연결합니다."""
        try:
            self.rds_conn = psycopg2.connect(
                dbname="youth_policy",
                user="postgres",
                password=db_password,
                host=rds_endpoint,
                port="5432"
            )
            logger.info("AWS RDS 연결 성공")
        except Exception as e:
            logger.error(f"AWS RDS 연결 실패: {str(e)}")
            raise
    
    def create_table_on_rds(self):
        """RDS에 policies 테이블을 생성합니다."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS policies (
            id SERIAL PRIMARY KEY,
            정책명 TEXT,
            정책키워드명 TEXT,
            정책지원내용 TEXT,
            사업운영기관명 TEXT,
            사업신청기관명 TEXT,
            정책거주지역코드 TEXT,
            정책거주지역명 TEXT,
            지원대상최소연령 INTEGER,
            지원대상최대연령 INTEGER,
            사업기간시작일자 DATE,
            사업기간종료일자 DATE,
            신청기간시작일자 DATE,
            신청기간종료일자 DATE,
            정책지원금액 BIGINT,
            정책지원금액상한 BIGINT,
            정책지원금액하한 BIGINT,
            지원금액기타설명 TEXT,
            소득조건구분코드 TEXT,
            소득조건구분명 TEXT,
            소득조건상세내용 TEXT,
            학력조건구분코드 TEXT,
            학력조건구분명 TEXT,
            전공계열구분코드 TEXT,
            전공계열구분명 TEXT,
            취업상태구분코드 TEXT,
            취업상태구분명 TEXT,
            특화분야구분코드 TEXT,
            특화분야구분명 TEXT,
            추가신청자격조건내용 TEXT,
            참여제안대상내용 TEXT,
            결혼상태코드 TEXT,
            결혼상태명 TEXT,
            정책취업요건코드 TEXT,
            정책학력요건코드 TEXT,
            정책특화요건코드 TEXT,
            기타요건 TEXT
        );
        
        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_policies_region ON policies(정책거주지역코드);
        CREATE INDEX IF NOT EXISTS idx_policies_age_min ON policies(지원대상최소연령);
        CREATE INDEX IF NOT EXISTS idx_policies_age_max ON policies(지원대상최대연령);
        CREATE INDEX IF NOT EXISTS idx_policies_income ON policies(소득조건구분코드);
        CREATE INDEX IF NOT EXISTS idx_policies_amount ON policies(정책지원금액);
        CREATE INDEX IF NOT EXISTS idx_policies_start_date ON policies(사업기간시작일자);
        CREATE INDEX IF NOT EXISTS idx_policies_end_date ON policies(사업기간종료일자);
        
        -- 전문 검색 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_policies_keyword_gin ON policies USING gin(to_tsvector('korean', 정책키워드명));
        CREATE INDEX IF NOT EXISTS idx_policies_content_gin ON policies USING gin(to_tsvector('korean', 정책지원내용));
        CREATE INDEX IF NOT EXISTS idx_policies_qualification_gin ON policies USING gin(to_tsvector('korean', 추가신청자격조건내용));
        """
        
        try:
            with self.rds_conn.cursor() as cur:
                cur.execute(create_table_sql)
                self.rds_conn.commit()
                logger.info("RDS에 policies 테이블 생성 완료")
        except Exception as e:
            logger.error(f"테이블 생성 실패: {str(e)}")
            raise
    
    def migrate_data(self):
        """로컬 DB에서 RDS로 데이터를 마이그레이션합니다."""
        try:
            # 로컬 DB에서 모든 데이터 가져오기
            with self.local_conn.cursor(cursor_factory=RealDictCursor) as local_cur:
                local_cur.execute("SELECT * FROM policies")
                local_data = local_cur.fetchall()
                
            logger.info(f"로컬 DB에서 {len(local_data)}개 레코드 조회")
            
            # RDS에 데이터 삽입
            with self.rds_conn.cursor() as rds_cur:
                # 기존 데이터 삭제 (선택적)
                rds_cur.execute("TRUNCATE TABLE policies RESTART IDENTITY")
                
                # 데이터 삽입
                for row in local_data:
                    # id 컬럼 제외하고 삽입
                    columns = [col for col in row.keys() if col != 'id']
                    values = [row[col] for col in columns]
                    
                    placeholders = ','.join(['%s'] * len(values))
                    columns_str = ','.join([f'"{col}"' for col in columns])
                    
                    insert_sql = f"INSERT INTO policies ({columns_str}) VALUES ({placeholders})"
                    rds_cur.execute(insert_sql, values)
                
                self.rds_conn.commit()
                
            logger.info(f"RDS로 {len(local_data)}개 레코드 마이그레이션 완료")
            
        except Exception as e:
            logger.error(f"데이터 마이그레이션 실패: {str(e)}")
            if self.rds_conn:
                self.rds_conn.rollback()
            raise
    
    def verify_migration(self):
        """마이그레이션 결과를 검증합니다."""
        try:
            # 로컬 DB 레코드 수 확인
            with self.local_conn.cursor() as local_cur:
                local_cur.execute("SELECT COUNT(*) FROM policies")
                local_count = local_cur.fetchone()[0]
            
            # RDS 레코드 수 확인
            with self.rds_conn.cursor() as rds_cur:
                rds_cur.execute("SELECT COUNT(*) FROM policies")
                rds_count = rds_cur.fetchone()[0]
            
            # 샘플 데이터 비교
            with self.rds_conn.cursor(cursor_factory=RealDictCursor) as rds_cur:
                rds_cur.execute("SELECT * FROM policies LIMIT 5")
                sample_data = rds_cur.fetchall()
            
            logger.info(f"검증 결과:")
            logger.info(f"  로컬 DB: {local_count}개 레코드")
            logger.info(f"  RDS: {rds_count}개 레코드")
            logger.info(f"  마이그레이션 성공: {local_count == rds_count}")
            
            if sample_data:
                logger.info(f"  샘플 정책: {sample_data[0]['정책명']}")
            
            return local_count == rds_count
            
        except Exception as e:
            logger.error(f"마이그레이션 검증 실패: {str(e)}")
            return False
    
    def close_connections(self):
        """데이터베이스 연결을 종료합니다."""
        if self.local_conn:
            self.local_conn.close()
            logger.info("로컬 DB 연결 종료")
            
        if self.rds_conn:
            self.rds_conn.close()
            logger.info("RDS 연결 종료")

def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        print("사용법: python database_migration.py <RDS_ENDPOINT>")
        print("예시: python database_migration.py youth-policy-api-postgres.xxx.ap-northeast-2.rds.amazonaws.com")
        sys.exit(1)
    
    rds_endpoint = sys.argv[1]
    secret_name = "youth-policy-api-db-password"
    
    migrator = DatabaseMigrator()
    
    try:
        logger.info("=== 데이터베이스 마이그레이션 시작 ===")
        
        # 1. RDS 자격 증명 가져오기
        logger.info("RDS 자격 증명 가져오는 중...")
        db_password = migrator.get_rds_credentials(secret_name)
        
        # 2. 데이터베이스 연결
        logger.info("데이터베이스 연결 중...")
        migrator.connect_local_db()
        migrator.connect_rds(rds_endpoint, db_password)
        
        # 3. RDS에 테이블 생성
        logger.info("RDS에 테이블 생성 중...")
        migrator.create_table_on_rds()
        
        # 4. 데이터 마이그레이션
        logger.info("데이터 마이그레이션 중...")
        migrator.migrate_data()
        
        # 5. 마이그레이션 검증
        logger.info("마이그레이션 검증 중...")
        if migrator.verify_migration():
            logger.info("✅ 마이그레이션 성공!")
        else:
            logger.error("❌ 마이그레이션 검증 실패!")
            sys.exit(1)
        
        logger.info("=== 데이터베이스 마이그레이션 완료 ===")
        
    except Exception as e:
        logger.error(f"마이그레이션 중 오류 발생: {str(e)}")
        sys.exit(1)
        
    finally:
        migrator.close_connections()

if __name__ == "__main__":
    main() 