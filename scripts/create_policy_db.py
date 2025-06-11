import pandas as pd
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine
import logging
import os
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

# AWS RDS 연결 설정 (환경변수 기반)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "database": os.getenv("DB_NAME", "youth_policy")
}

def get_connection_string(include_db=True):
    """데이터베이스 연결 문자열 생성"""
    if include_db:
        return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    else:
        return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/postgres"

def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            connect_timeout=10
        )
        conn.close()
        logging.info(f"AWS RDS 연결 성공: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        return True
    except Exception as e:
        logging.error(f"AWS RDS 연결 실패: {str(e)}")
        return False

def create_database():
    """PostgreSQL 데이터베이스 생성"""
    try:
        # AWS RDS 연결 테스트
        if not test_connection():
            raise Exception("AWS RDS 연결에 실패했습니다. 엔드포인트와 보안 그룹 설정을 확인하세요.")
        
        # 기본 postgres 데이터베이스에 연결
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            connect_timeout=10
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # youth_policy 데이터베이스가 이미 존재하는지 확인
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_CONFIG["database"],))
        exists = cur.fetchone()
        
        if not exists:
            # 데이터베이스 생성
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_CONFIG["database"])))
            logging.info(f"{DB_CONFIG['database']} 데이터베이스가 AWS RDS에 생성되었습니다.")
        else:
            logging.info(f"{DB_CONFIG['database']} 데이터베이스가 이미 존재합니다.")
            
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
            dbname=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            connect_timeout=10
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
        
        # 인덱스 생성 (텍스트 검색 최적화)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_policies_keywords ON policies USING gin (to_tsvector('korean', 정책키워드명));
            CREATE INDEX IF NOT EXISTS idx_policies_support ON policies USING gin (to_tsvector('korean', 정책지원내용));
            CREATE INDEX IF NOT EXISTS idx_policies_qualification ON policies USING gin (to_tsvector('korean', 추가신청자격조건내용));
            CREATE INDEX IF NOT EXISTS idx_policies_age ON policies (지원대상최소연령, 지원대상최대연령);
            CREATE INDEX IF NOT EXISTS idx_policies_region ON policies (정책거주지역코드);
            CREATE INDEX IF NOT EXISTS idx_policies_dates ON policies (사업기간시작일자, 사업기간종료일자);
        """)
        
        conn.commit()
        logging.info("정책 테이블과 인덱스가 AWS RDS에 생성되었습니다.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logging.error(f"테이블 생성 중 오류 발생: {str(e)}")
        raise

def load_data():
    """CSV 파일에서 데이터 로드"""
    try:
        # CSV 파일 경로 확인
        csv_path = 'data/청년정책목록_전처리완료_2025-06-09.csv'
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {csv_path}")
        
        # CSV 파일 읽기
        df = pd.read_csv(csv_path, encoding='utf-8')
        logging.info(f"CSV 파일에서 {len(df)}개의 정책 데이터를 읽었습니다.")
        
        # SQLAlchemy 엔진 생성 (AWS RDS 연결)
        engine = create_engine(
            get_connection_string(),
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={
                "connect_timeout": 10,
                "application_name": "youth_policy_loader"
            }
        )
        
        # 데이터프레임을 PostgreSQL에 저장
        df.to_sql('policies', engine, if_exists='replace', index=False, method='multi', chunksize=1000)
        
        logging.info(f"{len(df)}개의 정책 데이터가 AWS RDS에 성공적으로 로드되었습니다.")
        
        # 엔진 정리
        engine.dispose()
        
    except Exception as e:
        logging.error(f"데이터 로드 중 오류 발생: {str(e)}")
        raise

def verify_data():
    """데이터 로드 검증"""
    try:
        conn = psycopg2.connect(
            dbname=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"]
        )
        cur = conn.cursor()
        
        # 총 레코드 수 확인
        cur.execute("SELECT COUNT(*) FROM policies")
        count = cur.fetchone()[0]
        
        # 샘플 데이터 확인
        cur.execute("SELECT 정책명, 정책키워드명 FROM policies LIMIT 5")
        samples = cur.fetchall()
        
        logging.info(f"데이터 검증 완료: 총 {count}개의 정책이 저장되었습니다.")
        for policy in samples:
            logging.info(f"샘플: {policy[0]} - {policy[1]}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logging.error(f"데이터 검증 중 오류 발생: {str(e)}")
        raise

def main():
    """메인 실행 함수"""
    try:
        logging.info("AWS RDS 데이터베이스 생성 프로세스를 시작합니다.")
        logging.info(f"연결 대상: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        
        create_database()
        create_tables()
        load_data()
        verify_data()
        
        logging.info("AWS RDS 데이터베이스 생성이 완료되었습니다.")
        logging.info(f"연결 문자열: {get_connection_string()}")
        
    except Exception as e:
        logging.error(f"프로세스 실행 중 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    # 환경변수 확인
    required_env_vars = ["DB_HOST", "DB_USER", "DB_PASSWORD"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logging.warning(f"다음 환경변수가 설정되지 않았습니다: {missing_vars}")
        logging.warning("기본값을 사용합니다. 프로덕션 환경에서는 반드시 설정하세요.")
    
    main() 