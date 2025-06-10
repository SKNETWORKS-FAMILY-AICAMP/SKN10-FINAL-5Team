import pandas as pd
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/db_creation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

def create_database():
    """PostgreSQL 데이터베이스 생성"""
    try:
        # 기본 postgres 데이터베이스에 연결
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # youth_policy 데이터베이스가 이미 존재하는지 확인
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'youth_policy'")
        exists = cur.fetchone()
        
        if not exists:
            # 데이터베이스 생성
            cur.execute(sql.SQL("CREATE DATABASE youth_policy"))
            logging.info("youth_policy 데이터베이스가 생성되었습니다.")
        else:
            logging.info("youth_policy 데이터베이스가 이미 존재합니다.")
            
        cur.close()
        conn.close()
        
    except Exception as e:
        logging.error(f"데이터베이스 생성 중 오류 발생: {str(e)}")
        raise

def create_tables():
    """정책 테이블 생성"""
    try:
        # youth_policy 데이터베이스에 연결
        conn = psycopg2.connect(
            dbname="youth_policy",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        
        # 정책 테이블 생성
        cur.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                id SERIAL PRIMARY KEY,
                정책명 VARCHAR(255),
                정책키워드명 TEXT,
                정책지원내용 TEXT,
                추가신청자격조건내용 TEXT,
                정책지원금액 INTEGER,
                지원대상최소연령 INTEGER,
                지원대상최대연령 INTEGER,
                소득조건구분코드 VARCHAR(10),
                정책거주지역코드 VARCHAR(10),
                결혼상태코드 VARCHAR(10),
                정책취업요건코드 VARCHAR(10),
                정책학력요건코드 VARCHAR(10),
                정책특화요건코드 VARCHAR(10),
                사업기간시작일자 DATE,
                사업기간종료일자 DATE,
                신청기간시작일자 DATE,
                신청기간종료일자 DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 인덱스 생성
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_policies_keywords ON policies USING gin (to_tsvector('korean', 정책키워드명));
            CREATE INDEX IF NOT EXISTS idx_policies_support ON policies USING gin (to_tsvector('korean', 정책지원내용));
            CREATE INDEX IF NOT EXISTS idx_policies_qualification ON policies USING gin (to_tsvector('korean', 추가신청자격조건내용));
        """)
        
        conn.commit()
        logging.info("정책 테이블과 인덱스가 생성되었습니다.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logging.error(f"테이블 생성 중 오류 발생: {str(e)}")
        raise

def load_data():
    """CSV 파일에서 데이터 로드"""
    try:
        # CSV 파일 읽기
        df = pd.read_csv('data/청년정책목록_전처리완료_2025-06-09.csv')
        
        # SQLAlchemy 엔진 생성
        engine = create_engine('postgresql://postgres:postgres@localhost:5432/youth_policy')
        
        # 데이터프레임을 PostgreSQL에 저장
        df.to_sql('policies', engine, if_exists='replace', index=False)
        
        logging.info(f"{len(df)}개의 정책 데이터가 성공적으로 로드되었습니다.")
        
    except Exception as e:
        logging.error(f"데이터 로드 중 오류 발생: {str(e)}")
        raise

def main():
    """메인 실행 함수"""
    try:
        logging.info("데이터베이스 생성 프로세스를 시작합니다.")
        create_database()
        create_tables()
        load_data()
        logging.info("데이터베이스 생성이 완료되었습니다.")
        
    except Exception as e:
        logging.error(f"프로세스 실행 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    main() 