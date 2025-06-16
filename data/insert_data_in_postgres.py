import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouthPolicyDBInserter:
    def __init__(self):
        """
        AWS RDS PostgreSQL 연결 설정
        환경변수를 통해 DB 연결 정보를 설정하세요.
        """
        self.db_config = {
            'host': os.getenv('DB_HOST', 'your-rds-endpoint.amazonaws.com'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'youth_policy_db'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'your_password')
        }
        self.connection = None
        self.cursor = None
    
    def connect_db(self):
        """데이터베이스 연결"""
        try:
            self.connection = psycopg2.connect(**self.db_config)
            self.cursor = self.connection.cursor()
            logger.info("데이터베이스 연결 성공")
            return True
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            return False
    
    def close_db(self):
        """데이터베이스 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("데이터베이스 연결 종료")
    
    def preprocess_data(self, df):
        """데이터 전처리"""
        logger.info("데이터 전처리 시작")
        
        # 컬럼명을 영어로 매핑
        column_mapping = {
            '정책번호': 'plcy_no',
            '정책제공방법코드': 'plcy_pvsn_mthd_cd',
            '정책명': 'plcy_nm',
            '정책키워드명': 'plcy_kywd_nm',
            '정책설명내용': 'plcy_expln_cn',
            '정책대분류명': 'lclsf_nm',
            '정책중분류명': 'mclsf_nm',
            '정책지원내용': 'plcy_sprt_cn',
            '주관기관코드명': 'sprvsn_inst_cd_nm',
            '운영기관코드명': 'oper_inst_cd_nm',
            '신청기간구분코드': 'aply_prd_se_cd',
            '사업기간구분코드': 'biz_prd_se_cd',
            '사업기간시작일자': 'biz_prd_bgng_ymd',
            '사업기간종료일자': 'biz_prd_end_ymd',
            '사업기간기타내용': 'biz_prd_etc_cn',
            '정책신청방법내용': 'plcy_aply_mthd_cn',
            '심사방법내용': 'srng_mthd_cn',
            '신청URL주소': 'aply_url_addr',
            '제출서류내용': 'sbmsn_dcmnt_cn',
            '기타사항내용': 'etc_mttr_cn',
            '참고URL주소1': 'ref_url_addr1',
            '참고URL주소2': 'ref_url_addr2',
            '지원도착순서여부': 'sprt_arvl_seq_yn',
            '지원대상최소연령': 'sprt_trgt_min_age',
            '지원대상최대연령': 'sprt_trgt_max_age',
            '결혼상태코드': 'mrg_stts_cd',
            '소득조건구분코드': 'earn_cnd_se_cd',
            '소득기타내용': 'earn_etc_cn',
            '추가신청자격조건내용': 'add_aply_qlfcnd_cn',
            '참여제안대상내용': 'ptcp_prp_trgt_cn',
            '조회수': 'inq_cnt',
            '정책거주지역코드': 'zip_cd',
            '정책전공요건코드': 'plcy_major_cd',
            '정책취업요건코드': 'job_cd',
            '정책학력요건코드': 'school_cd',
            '최초등록일시': 'frst_reg_dt',
            '최종수정일시': 'last_mdfcn_dt',
            '정책특화요건코드': 's_biz_cd',
            '신청시작일자': 'aply_start_date',
            '신청종료일자': 'aply_end_date'
        }
        
        # 컬럼명 변경
        df = df.rename(columns=column_mapping)
        
        # 날짜 형식 변환 함수
        def convert_date(date_str):
            if pd.isna(date_str) or date_str == '' or date_str == 'NaN':
                return None
            try:
                # YYYY-MM-DD 형식으로 변환
                if isinstance(date_str, str) and len(date_str) == 10:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                return None
            except:
                return None
        
        # 날짜 컬럼 처리
        date_columns = ['biz_prd_bgng_ymd', 'biz_prd_end_ymd', 'aply_start_date', 'aply_end_date']
        for col in date_columns:
            if col in df.columns:
                df[col] = df[col].apply(convert_date)
        
        # 타임스탬프 컬럼 처리
        timestamp_columns = ['frst_reg_dt', 'last_mdfcn_dt']
        for col in timestamp_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # 숫자 컬럼 처리
        numeric_columns = ['sprt_trgt_min_age', 'sprt_trgt_max_age', 'inq_cnt']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0).astype(int)
        
        # Y/N 컬럼 처리
        if 'sprt_arvl_seq_yn' in df.columns:
            df['sprt_arvl_seq_yn'] = df['sprt_arvl_seq_yn'].fillna('N')
        
        # 텍스트 컬럼의 null 값을 빈 문자열로 처리
        text_columns = [col for col in df.columns if col not in date_columns + timestamp_columns + numeric_columns + ['sprt_arvl_seq_yn']]
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna('')
        logger.info(f"데이터 전처리 완료: {len(df)}개 행")
        return df
    
    def get_column_list(self):
        """컬럼 리스트 반환"""
        return [
            'plcy_no', 'plcy_pvsn_mthd_cd', 'plcy_nm', 'plcy_kywd_nm', 'plcy_expln_cn',
            'lclsf_nm', 'mclsf_nm', 'plcy_sprt_cn', 'sprvsn_inst_cd_nm', 'oper_inst_cd_nm',
            'aply_prd_se_cd', 'biz_prd_se_cd', 'biz_prd_bgng_ymd', 'biz_prd_end_ymd',
            'biz_prd_etc_cn', 'plcy_aply_mthd_cn', 'srng_mthd_cn', 'aply_url_addr',
            'sbmsn_dcmnt_cn', 'etc_mttr_cn', 'ref_url_addr1', 'ref_url_addr2',
            'sprt_arvl_seq_yn', 'sprt_trgt_min_age', 'sprt_trgt_max_age', 'mrg_stts_cd',
            'earn_cnd_se_cd', 'earn_etc_cn', 'add_aply_qlfcnd_cn', 'ptcp_prp_trgt_cn',
            'inq_cnt', 'zip_cd', 'plcy_major_cd', 'job_cd', 'school_cd',
            'aply_start_date', 'aply_end_date', 'frst_reg_dt', 'last_mdfcn_dt', 's_biz_cd'
        ]
    
    def create_insert_query(self, table_name='youth_policy'):
        """INSERT 쿼리 생성 (execute_values용)"""
        columns = self.get_column_list()
        column_str = ', '.join(columns)
        
        # execute_values에서는 %s를 사용하지 않고 VALUES 부분만 정의
        query = f"""
        INSERT INTO {table_name} ({column_str}) 
        VALUES %s
        ON CONFLICT (plcy_no) DO UPDATE SET
            plcy_pvsn_mthd_cd = EXCLUDED.plcy_pvsn_mthd_cd,
            plcy_nm = EXCLUDED.plcy_nm,
            plcy_kywd_nm = EXCLUDED.plcy_kywd_nm,
            plcy_expln_cn = EXCLUDED.plcy_expln_cn,
            lclsf_nm = EXCLUDED.lclsf_nm,
            mclsf_nm = EXCLUDED.mclsf_nm,
            plcy_sprt_cn = EXCLUDED.plcy_sprt_cn,
            sprvsn_inst_cd_nm = EXCLUDED.sprvsn_inst_cd_nm,
            oper_inst_cd_nm = EXCLUDED.oper_inst_cd_nm,
            aply_prd_se_cd = EXCLUDED.aply_prd_se_cd,
            biz_prd_se_cd = EXCLUDED.biz_prd_se_cd,
            biz_prd_bgng_ymd = EXCLUDED.biz_prd_bgng_ymd,
            biz_prd_end_ymd = EXCLUDED.biz_prd_end_ymd,
            biz_prd_etc_cn = EXCLUDED.biz_prd_etc_cn,
            plcy_aply_mthd_cn = EXCLUDED.plcy_aply_mthd_cn,
            srng_mthd_cn = EXCLUDED.srng_mthd_cn,
            aply_url_addr = EXCLUDED.aply_url_addr,
            sbmsn_dcmnt_cn = EXCLUDED.sbmsn_dcmnt_cn,
            etc_mttr_cn = EXCLUDED.etc_mttr_cn,
            ref_url_addr1 = EXCLUDED.ref_url_addr1,
            ref_url_addr2 = EXCLUDED.ref_url_addr2,
            sprt_arvl_seq_yn = EXCLUDED.sprt_arvl_seq_yn,
            sprt_trgt_min_age = EXCLUDED.sprt_trgt_min_age,
            sprt_trgt_max_age = EXCLUDED.sprt_trgt_max_age,
            mrg_stts_cd = EXCLUDED.mrg_stts_cd,
            earn_cnd_se_cd = EXCLUDED.earn_cnd_se_cd,
            earn_etc_cn = EXCLUDED.earn_etc_cn,
            add_aply_qlfcnd_cn = EXCLUDED.add_aply_qlfcnd_cn,
            ptcp_prp_trgt_cn = EXCLUDED.ptcp_prp_trgt_cn,
            inq_cnt = EXCLUDED.inq_cnt,
            zip_cd = EXCLUDED.zip_cd,
            plcy_major_cd = EXCLUDED.plcy_major_cd,
            job_cd = EXCLUDED.job_cd,
            school_cd = EXCLUDED.school_cd,
            aply_start_date = EXCLUDED.aply_start_date,
            aply_end_date = EXCLUDED.aply_end_date,
            last_mdfcn_dt = CURRENT_TIMESTAMP,
            s_biz_cd = EXCLUDED.s_biz_cd
        """
        return query
    
    def insert_data_batch(self, df, batch_size=1000):
        """배치 단위로 데이터 삽입"""
        try:
            query = self.create_insert_query()
            total_rows = len(df)
            inserted_rows = 0
            
            # 컬럼 순서에 맞게 데이터 정렬
            column_order = [
                'plcy_no', 'plcy_pvsn_mthd_cd', 'plcy_nm', 'plcy_kywd_nm', 'plcy_expln_cn',
                'lclsf_nm', 'mclsf_nm', 'plcy_sprt_cn', 'sprvsn_inst_cd_nm', 'oper_inst_cd_nm',
                'aply_prd_se_cd', 'biz_prd_se_cd', 'biz_prd_bgng_ymd', 'biz_prd_end_ymd',
                'biz_prd_etc_cn', 'plcy_aply_mthd_cn', 'srng_mthd_cn', 'aply_url_addr',
                'sbmsn_dcmnt_cn', 'etc_mttr_cn', 'ref_url_addr1', 'ref_url_addr2',
                'sprt_arvl_seq_yn', 'sprt_trgt_min_age', 'sprt_trgt_max_age', 'mrg_stts_cd',
                'earn_cnd_se_cd', 'earn_etc_cn', 'add_aply_qlfcnd_cn', 'ptcp_prp_trgt_cn',
                'inq_cnt', 'zip_cd', 'plcy_major_cd', 'job_cd', 'school_cd',
                'aply_start_date', 'aply_end_date', 'frst_reg_dt', 'last_mdfcn_dt', 's_biz_cd'
            ]
            
            # 배치 단위로 처리
            for i in range(0, total_rows, batch_size):
                batch_df = df.iloc[i:i+batch_size]
                
                # 데이터를 튜플 리스트로 변환
                data_tuples = []
                for _, row in batch_df.iterrows():
                    row_data = []
                    for col in column_order:
                        value = row.get(col)
                        if pd.isna(value):
                            row_data.append(None)
                        else:
                            row_data.append(value)
                    data_tuples.append(tuple(row_data))
                
                # 배치 삽입 실행
                execute_values(
                    self.cursor, 
                    query, 
                    data_tuples,
                    template=None,
                    page_size=batch_size
                )
                
                inserted_rows += len(batch_df)
                logger.info(f"배치 삽입 완료: {inserted_rows}/{total_rows} ({(inserted_rows/total_rows)*100:.1f}%)")
            
            # 커밋
            self.connection.commit()
            logger.info(f"전체 데이터 삽입 완료: {inserted_rows}개 행")
            return True
            
        except Exception as e:
            logger.error(f"데이터 삽입 중 오류 발생: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def run_insert(self, csv_file_path):
        """메인 실행 함수"""
        try:
            # 1. CSV 파일 읽기
            logger.info(f"CSV 파일 읽기 시작: {csv_file_path}")
            df = pd.read_csv(csv_file_path, encoding='utf-8')
            logger.info(f"CSV 파일 읽기 완료: {len(df)}개 행, {len(df.columns)}개 컬럼")
            
            # 2. 데이터 전처리
            df = self.preprocess_data(df)
            
            # 3. 데이터베이스 연결
            if not self.connect_db():
                return False
            
            # 4. 데이터 삽입
            success = self.insert_data_batch(df)
            
            # 5. 연결 종료
            self.close_db()
            
            return success
            
        except Exception as e:
            logger.error(f"실행 중 오류 발생: {e}")
            return False

def main():
    """메인 함수"""
    # CSV 파일 경로
    csv_file_path = r"c:\dev\SKN10-FINAL-5Team\data\청년정책목록_전처리완료_2025-06-16.csv"
    
    # 환경변수 설정 확인
    required_env_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"다음 환경변수가 설정되지 않았습니다: {missing_vars}")
        logger.warning("기본값을 사용하거나 코드에서 직접 설정해주세요.")
    
    # 데이터 삽입 실행
    inserter = YouthPolicyDBInserter()
    success = inserter.run_insert(csv_file_path)
    
    if success:
        logger.info("청년정책 데이터 삽입이 성공적으로 완료되었습니다!")
    else:
        logger.error("청년정책 데이터 삽입이 실패했습니다.")

if __name__ == "__main__":
    main()