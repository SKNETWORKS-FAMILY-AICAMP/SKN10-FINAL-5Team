import pandas as pd
import psycopg2
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_db():
    """PostgreSQL 데이터베이스 연결"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'your-rds-endpoint.amazonaws.com'),  # 실제 DB 호스트로 변경
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'youth_policy_db'),  # 실제 DB 명으로 변경
            user=os.getenv('DB_USER', 'postgres'),  # 실제 사용자명으로 변경
            password=os.getenv('DB_PASSWORD', 'your_password')  # 실제 비밀번호로 변경
        )
        return conn
    except Exception as e:
        logger.error(f"데이터베이스 연결 실패: {e}")
        return None

def read_csv_data(file_path):
    """CSV 파일 읽기"""
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        logger.info(f"CSV 파일 읽기 완료: {len(df)}개 행")
        return df
    except Exception as e:
        logger.error(f"CSV 파일 읽기 실패: {e}")
        return None

def insert_regions(conn, regions):
    """지역 데이터 삽입"""
    try:
        cursor = conn.cursor()
        
        # 기존 지역 데이터 조회
        cursor.execute("SELECT region_name FROM youth_policy_region")
        existing_regions = set(row[0] for row in cursor.fetchall())
        # 중복되지 않는 지역만 필터링 (parent_id는 NULL로 설정)
        new_regions = [(region, None) for region in regions if region not in existing_regions]
        
        if new_regions:
            # 배치 삽입 (parent_id는 일단 NULL로 설정)
            insert_query = """
                INSERT INTO youth_policy_region (region_name, parent_id)
                VALUES %s
            """
            execute_values(cursor, insert_query, new_regions)
            conn.commit()
            logger.info(f"{len(new_regions)}개 지역 데이터 삽입 완료")
        else:
            logger.info("삽입할 새로운 지역 데이터가 없습니다")
            
        cursor.close()
        
    except Exception as e:
        logger.error(f"지역 데이터 삽입 실패: {e}")
        conn.rollback()


def get_region_id(conn, region_name):
    """지역명으로 region_id 조회"""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT region_id FROM youth_policy_region WHERE region_name = %s", (region_name,))
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else None
    except Exception as e:
        logger.error(f"지역 ID 조회 실패: {e}")
        return None


def insert_conditions(conn, conditions):
    """조건 데이터 삽입"""
    try:
        cursor = conn.cursor()
        
        # 중복 체크를 위한 기존 데이터 조회 (정책번호, 조건명, 조건내용, region_id의 조합으로 체크)
        cursor.execute("SELECT plcy_no, condition_nm, condition_cn, region_id FROM youth_policy_condition")
        existing_conditions = set((row[0], row[1], row[2], row[3]) for row in cursor.fetchall())
        
        # 중복되지 않는 데이터만 필터링
        new_conditions = []
        for condition in conditions:
            if (condition[0], condition[1], condition[2], condition[3]) not in existing_conditions:
                new_conditions.append(condition)
        
        if new_conditions:
            # 배치 삽입
            insert_query = """
                INSERT INTO youth_policy_condition (plcy_no, condition_nm, condition_cn, region_id)
                VALUES %s
            """
            execute_values(cursor, insert_query, new_conditions)
            conn.commit()
            logger.info(f"{len(new_conditions)}개 조건 데이터 삽입 완료")
        else:
            logger.info("삽입할 새로운 조건 데이터가 없습니다")
            
        cursor.close()
        
    except Exception as e:
        logger.error(f"조건 데이터 삽입 실패: {e}")
        conn.rollback()

def process_conditions(conn, df):
    """조건 데이터 처리"""
    conditions = []
    all_regions = set()
    
    # 1단계: 모든 지역 정보 수집
    for index, row in df.iterrows():
        if pd.notna(row['정책거주지역코드']) and str(row['정책거주지역코드']).strip() != '전국':
            regions = [region.strip() for region in str(row['정책거주지역코드']).split(',')]
            for region in regions:
                if region and region != '전국':
                    all_regions.add(region)
    
    # 2단계: 지역 데이터 삽입
    if all_regions:
        insert_regions(conn, list(all_regions))
    
    # 3단계: 조건 데이터 생성
    for index, row in df.iterrows():
        plcy_no = row['정책번호']
        
        # 결혼상태 조건
        if pd.notna(row['결혼상태코드']) and str(row['결혼상태코드']).strip() != '제한없음':
            conditions.append((plcy_no, '결혼상태', str(row['결혼상태코드']).strip(), None))
        
        # 지역 조건 - 쉼표로 구분된 경우 각각 별도 조건으로 처리
        if pd.notna(row['정책거주지역코드']) and str(row['정책거주지역코드']).strip() != '전국':
            regions = [region.strip() for region in str(row['정책거주지역코드']).split(',')]
            for region in regions:
                if region and region != '전국':
                    region_id = get_region_id(conn, region)
                    conditions.append((plcy_no, '지역', region, region_id))
        
        # 전공요건 조건 - 쉼표로 구분된 경우 각각 별도 조건으로 처리
        if pd.notna(row['정책전공요건코드']) and str(row['정책전공요건코드']).strip() != '제한없음':
            majors = [major.strip() for major in str(row['정책전공요건코드']).split(',')]
            for major in majors:
                if major and major != '기타':
                    conditions.append((plcy_no, '전공요건', major, None))
        
        # 취업요건 조건 - 쉼표로 구분된 경우 각각 별도 조건으로 처리
        if pd.notna(row['정책취업요건코드']) and str(row['정책취업요건코드']).strip() != '제한없음':
            jobs = [job.strip() for job in str(row['정책취업요건코드']).split(',')]
            for job in jobs:
                if job and job != '기타':
                    conditions.append((plcy_no, '취업요건', job, None))
        
        # 학력요건 조건 - 쉼표로 구분된 경우 각각 별도 조건으로 처리
        if pd.notna(row['정책학력요건코드']) and str(row['정책학력요건코드']).strip() != '제한없음':
            educations = [education.strip() for education in str(row['정책학력요건코드']).split(',')]
            for education in educations:
                if education and education != '기타':
                    conditions.append((plcy_no, '학력요건', education, None))
    
    logger.info(f"총 {len(conditions)}개 조건 데이터 생성")
    return conditions

def main():
    """메인 함수"""
    # CSV 파일 경로
    csv_file_path = "청년정책목록_전처리완료_2025-06-17.csv"
    
    # CSV 데이터 읽기
    df = read_csv_data(csv_file_path)
    if df is None:
        return
    
    # 데이터베이스 연결
    conn = connect_to_db()
    if conn is None:
        return
    
    try:
        # 조건 데이터 처리 (지역 데이터도 함께 삽입)
        conditions = process_conditions(conn, df)
        
        if not conditions:
            logger.info("삽입할 조건 데이터가 없습니다")
            return
        
        # 조건 데이터 삽입
        insert_conditions(conn, conditions)
        
        # 결과 확인
        cursor = conn.cursor()
        
        # 지역 테이블 통계
        cursor.execute("SELECT COUNT(*) FROM youth_policy_region")
        region_count = cursor.fetchone()[0]
        logger.info(f"총 지역 데이터 개수: {region_count}")
        
        # 조건 테이블 통계
        cursor.execute("SELECT COUNT(*) FROM youth_policy_condition")
        total_count = cursor.fetchone()[0]
        logger.info(f"총 조건 데이터 개수: {total_count}")
        
        # 조건별 통계
        cursor.execute("""
            SELECT condition_nm, COUNT(*) 
            FROM youth_policy_condition 
            GROUP BY condition_nm 
            ORDER BY condition_nm
        """)
        stats = cursor.fetchall()
        logger.info("조건별 통계:")
        for condition_nm, count in stats:
            logger.info(f"  {condition_nm}: {count}개")
        
        # 지역별 조건 통계
        cursor.execute("""
            SELECT r.region_name, COUNT(c.condition_id) 
            FROM youth_policy_region r
            LEFT JOIN youth_policy_condition c ON r.region_id = c.region_id
            WHERE c.condition_nm = '지역'
            GROUP BY r.region_name
            ORDER BY COUNT(c.condition_id) DESC
            LIMIT 10
        """)
        region_stats = cursor.fetchall()
        logger.info("상위 10개 지역별 정책 수:")
        for region_name, count in region_stats:
            logger.info(f"  {region_name}: {count}개")
        
        cursor.close()
        
    finally:
        conn.close()
        logger.info("데이터베이스 연결 종료")

if __name__ == "__main__":
    main()