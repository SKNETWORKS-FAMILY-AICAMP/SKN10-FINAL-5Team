"""
청년정책 CSV 데이터를 PostgreSQL 통합 테이블에 삽입하는 스크립트 (임베딩 포함)
- policies: 모든 정책 정보를 포함하는 통합 테이블
- policy_embeddings: 정책 임베딩 벡터 테이블
작성일: 2025-06-18
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
import openai
import time
from typing import List
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouthPolicyDataInserter:
    def __init__(self, db_config, openai_api_key=None):
        """
        DB 연결 설정 및 OpenAI 클라이언트 초기화
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        self.code_mapping = {}
        
        # OpenAI 클라이언트 설정
        if openai_api_key:
            openai.api_key = openai_api_key
        else:
            openai.api_key = os.getenv('OPENAI_API_KEY')
        
        if not openai.api_key:
            logger.warning("OpenAI API 키가 설정되지 않았습니다. 임베딩 생성이 불가능합니다.")
        
    def connect_db(self):
        """DB 연결"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            logger.info("데이터베이스 연결 성공")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
    
    def close_db(self):
        """DB 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("데이터베이스 연결 종료")
    
    def load_csv_data(self, csv_file_path):
        """CSV 파일 로드"""
        try:
            df = pd.read_csv(csv_file_path)
            logger.info(f"CSV 파일 로드 완료: {len(df)}개 레코드")
            return df
        except Exception as e:
            logger.error(f"CSV 파일 로드 실패: {e}")
            raise
    
    def preprocess_data(self, df):
        """데이터 전처리"""
        # NaN 값을 None으로 변환
        df = df.where(pd.notnull(df), None)
        
        # 숫자형 컬럼 처리
        numeric_columns = ['조회수', '지원대상최소연령', '지원대상최대연령']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        logger.info("데이터 전처리 완료")
        return df
    
    def insert_policies(self, df):
        """통합 정책 테이블에 모든 정보 삽입 및 업데이트된 정책번호 반환"""
        policies_data = []
        
        for _, row in df.iterrows():
            policy_data = (
                # 기본 정책 정보
                row['정책명'],
                row['정책설명내용'],
                row['정책지원내용'],
                row['정책신청방법내용'],
                row['심사방법내용'],
                row['제출서류내용'],
                row['기타사항내용'],
                )
            policies_data.append(policy_data)
        
        query = """
        INSERT INTO policies (
            plcy_no, plcy_nm, plcy_expln_cn, plcy_sprt_cn, plcy_aply_mthd_cn,
            srng_mthd_cn, sbmsn_dcmnt_cn, etc_mttr_cn, inq_cnt, frst_reg_dt,
            last_mdfcn_dt, aply_bgng_ymd, aply_end_ymd,
            sprt_trgt_min_age, sprt_trgt_max_age, mrg_stts_cd, plcy_major_cd,
            job_cd, school_cd, zip_cd, earn_cnd_se_cd, earn_etc_cn,
            add_aply_qlfcc_cn, ptcp_prp_trgt_cn,
            lclsf_nm, mclsf_nm, plcy_pvsn_mthd_cd, plcy_kywd_nm,
            sprvsn_inst_cd_nm, oper_inst_cd_nm, aply_prd_se_cd, biz_prd_se_cd,
            biz_prd_bgng_ymd, biz_prd_end_ymd, biz_prd_etc_cn, s_biz_cd,
            aply_url_addr, ref_url_addr1, ref_url_addr2
        ) VALUES %s
        ON CONFLICT (plcy_no) DO UPDATE SET
            plcy_nm = EXCLUDED.plcy_nm,
            plcy_expln_cn = EXCLUDED.plcy_expln_cn,
            plcy_sprt_cn = EXCLUDED.plcy_sprt_cn,
            plcy_aply_mthd_cn = EXCLUDED.plcy_aply_mthd_cn,
            srng_mthd_cn = EXCLUDED.srng_mthd_cn,
            sbmsn_dcmnt_cn = EXCLUDED.sbmsn_dcmnt_cn,
            etc_mttr_cn = EXCLUDED.etc_mttr_cn,
            inq_cnt = EXCLUDED.inq_cnt,
            frst_reg_dt = EXCLUDED.frst_reg_dt,
            last_mdfcn_dt = EXCLUDED.last_mdfcn_dt,
            aply_bgng_ymd = EXCLUDED.aply_bgng_ymd,
            aply_end_ymd = EXCLUDED.aply_end_ymd,
            sprt_trgt_min_age = EXCLUDED.sprt_trgt_min_age,
            sprt_trgt_max_age = EXCLUDED.sprt_trgt_max_age,
            mrg_stts_cd = EXCLUDED.mrg_stts_cd,
            plcy_major_cd = EXCLUDED.plcy_major_cd,
            job_cd = EXCLUDED.job_cd,
            school_cd = EXCLUDED.school_cd,
            zip_cd = EXCLUDED.zip_cd,
            earn_cnd_se_cd = EXCLUDED.earn_cnd_se_cd,
            earn_etc_cn = EXCLUDED.earn_etc_cn,
            add_aply_qlfcc_cn = EXCLUDED.add_aply_qlfcc_cn,
            ptcp_prp_trgt_cn = EXCLUDED.ptcp_prp_trgt_cn,
            lclsf_nm = EXCLUDED.lclsf_nm,
            mclsf_nm = EXCLUDED.mclsf_nm,
            plcy_pvsn_mthd_cd = EXCLUDED.plcy_pvsn_mthd_cd,
            plcy_kywd_nm = EXCLUDED.plcy_kywd_nm,
            sprvsn_inst_cd_nm = EXCLUDED.sprvsn_inst_cd_nm,
            oper_inst_cd_nm = EXCLUDED.oper_inst_cd_nm,
            aply_prd_se_cd = EXCLUDED.aply_prd_se_cd,
            biz_prd_se_cd = EXCLUDED.biz_prd_se_cd,
            biz_prd_bgng_ymd = EXCLUDED.biz_prd_bgng_ymd,
            biz_prd_end_ymd = EXCLUDED.biz_prd_end_ymd,
            biz_prd_etc_cn = EXCLUDED.biz_prd_etc_cn,
            s_biz_cd = EXCLUDED.s_biz_cd,
            aply_url_addr = EXCLUDED.aply_url_addr,
            ref_url_addr1 = EXCLUDED.ref_url_addr1,
            ref_url_addr2 = EXCLUDED.ref_url_addr2,
            updated_at = CURRENT_TIMESTAMP
        WHERE EXCLUDED.last_mdfcn_dt > policies.last_mdfcn_dt 
            OR policies.last_mdfcn_dt IS NULL
        """
        
        # 업데이트된 정책번호들을 저장할 임시 테이블 생성
        self.cursor.execute("""
            DROP TABLE IF EXISTS temp_updated_policies;
            CREATE TEMPORARY TABLE temp_updated_policies (
                plcy_no VARCHAR(50)
            )
        """)
        
        execute_values(self.cursor, query, policies_data)
        
        # 업데이트된 정책번호들을 임시 테이블에 저장
        policy_numbers = [policy[0] for policy in policies_data]  # 정책번호들
        policy_numbers_placeholders = ','.join(['%s'] * len(policy_numbers))
        
        # 실제로 삽입되거나 업데이트된 정책들을 찾기
        update_check_query = f"""
        INSERT INTO temp_updated_policies (plcy_no)
        SELECT p.plcy_no 
        FROM policies p
        WHERE p.plcy_no IN ({policy_numbers_placeholders})
        AND (
            p.updated_at >= CURRENT_TIMESTAMP - INTERVAL '1 minute'
            OR p.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 minute'
        )
        """
        
        self.cursor.execute(update_check_query, policy_numbers)
        self.conn.commit()
        
        # 업데이트된 정책번호들 조회
        self.cursor.execute("SELECT plcy_no FROM temp_updated_policies")
        updated_policy_numbers = [row[0] for row in self.cursor.fetchall()]
        
        logger.info(f"통합 정책 테이블에 {len(policies_data)}개 레코드 처리 완료 (업데이트 대상: {len(updated_policy_numbers)}개)")        
        return updated_policy_numbers
    
    def insert_policy_conditions(self, df):
        """정책 조건 정보 테이블에 데이터 삽입"""
        conditions_data = []
        
        for _, row in df.iterrows():
            policy_no = row['정책번호']
            
            # 결혼상태 조건
            if pd.notna(row['결혼상태코드']) and row['결혼상태코드'] != '제한없음':
                conditions_data.append((policy_no, 'mrg_stts_cd', row['결혼상태코드']))

            # 전공 조건 (콤마로 분리된 전공코드는 각각 별도 레코드로 생성)
            if pd.notna(row['정책전공요건코드']) and row['정책전공요건코드'] != '제한없음':
                majors = [major.strip() for major in str(row['정책전공요건코드']).split(',')]
                for major in majors:
                    if major:  # 빈 문자열이 아닌 경우만 추가
                        conditions_data.append((policy_no, 'plcy_major_cd', major))

            # 취업 조건 (콤마로 분리된 취업요건코드는 각각 별도 레코드로 생성)
            if pd.notna(row['정책취업요건코드']) and row['정책취업요건코드'] != '제한없음':
                jobs = [job.strip() for job in str(row['정책취업요건코드']).split(',')]
                for job in jobs:
                    if job:  # 빈 문자열이 아닌 경우만 추가
                        conditions_data.append((policy_no, 'job_cd', job))

            # 학력 조건 (콤마로 분리된 학력요건코드는 각각 별도 레코드로 생성)
            if pd.notna(row['정책학력요건코드']) and row['정책학력요건코드'] != '제한없음':
                schools = [school.strip() for school in str(row['정책학력요건코드']).split(',')]
                for school in schools:
                    if school:  # 빈 문자열이 아닌 경우만 추가
                        conditions_data.append((policy_no, 'school_cd', school))

            # 거주지역 조건 (콤마로 분리된 지역은 각각 별도 레코드로 생성)
            if pd.notna(row['정책거주지역코드']) and row['정책거주지역코드'] != '전국':
                regions = [region.strip() for region in str(row['정책거주지역코드']).split(',')]
                for region in regions:
                    if region:  # 빈 문자열이 아닌 경우만 추가
                        conditions_data.append((policy_no, 'zip_cd', region))

            # 소득 조건 (무관이 아닌 경우 소득기타내용을 데이터로 사용)
            if pd.notna(row['소득조건구분코드']) and row['소득조건구분코드'] != '무관':
                income_desc = row['소득기타내용'] if pd.notna(row['소득기타내용']) else row['소득조건구분코드']
                conditions_data.append((policy_no, 'earn_etc_cn', income_desc))
            
            # 추가 자격 조건 (추가신청자격조건내용과 참여제안대상내용 통합)
            additional_conditions = []
            if pd.notna(row['추가신청자격조건내용']):
                additional_conditions.append(row['추가신청자격조건내용'])
            if pd.notna(row['참여제안대상내용']):
                additional_conditions.append(row['참여제안대상내용'])
            
            if additional_conditions:
                combined_condition = " / ".join(additional_conditions)
                conditions_data.append((policy_no, 'additional_requirement', combined_condition))
        
        if conditions_data:
            query = """
            INSERT INTO policy_conditions (plcy_no, condition_type, condition_desc)
            VALUES %s
            ON CONFLICT DO NOTHING
            """
            
            execute_values(self.cursor, query, conditions_data)
            self.conn.commit()
            logger.info(f"정책 조건 테이블에 {len(conditions_data)}개 레코드 삽입 완료")
        else:
            logger.info("삽입할 정책 조건 데이터가 없습니다.")
    
    def insert_all_data(self, csv_file_path, include_embeddings=True):
        """전체 데이터 삽입 프로세스"""
        try:
            # CSV 데이터 로드 및 전처리
            df = self.load_csv_data(csv_file_path)
            df = self.preprocess_data(df)
            
            # DB 연결
            self.connect_db()            

            # 통합 정책 테이블에 데이터 삽입
            logger.info("통합 정책 테이블 데이터 삽입 시작")
            updated_policy_numbers = self.insert_policies(df)
            
            # 정책 조건 테이블에 데이터 삽입
            logger.info("정책 조건 테이블 데이터 삽입 시작")
            self.insert_policy_conditions(df)
            
            logger.info("모든 데이터 삽입 완료")
            
        except Exception as e:
            logger.error(f"데이터 삽입 중 오류 발생: {e}")
            if self.conn:
                self.conn.rollback()
            raise
        finally:
            self.close_db()

def main():
    # DB 연결 설정
    db_config = {
        'host': os.getenv("DB_HOST", 'localhost'),
        'database': os.getenv("DB_NAME", 'youth_policy_db'),
        'user': os.getenv("DB_USER", 'postgres'),
        'password': os.getenv("DB_PASSWORD", 'your_password'),
        'port': os.getenv("DB_PORT", 5432)
    }
    
    # CSV 파일 경로
    csv_file_path = '../청년정책목록_전처리완료_2025-06-20.csv'
    
    # OpenAI API 키 (환경변수에서 자동 로드)
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    # 데이터 삽입 실행
    inserter = YouthPolicyDataInserter(db_config, openai_api_key)
    inserter.insert_all_data(csv_file_path, include_embeddings=True)

if __name__ == "__main__":
    main()
