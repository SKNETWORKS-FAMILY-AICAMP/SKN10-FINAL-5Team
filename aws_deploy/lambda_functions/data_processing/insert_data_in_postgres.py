"""
청년정책 CSV 데이터를 PostgreSQL 통합 테이블에 삽입하는 스크립트 (임베딩 포함)
- policies: 모든 정책 정보를 포함하는 통합 테이블
- policy_embeddings: 정책 임베딩 벡터 테이블
- 수정일시 비교를 통한 조건부 업데이트 지원
작성일: 2025-06-18
수정일: 2025-06-18 - 조건부 업데이트 로직 추가
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
import openai
import time
from typing import List, Tuple, Dict
import os
from dotenv import load_dotenv
from datetime import datetime

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
    
    def get_existing_policies_info(self) -> Dict[str, datetime]:
        """기존 정책의 정책번호와 최종수정일시 정보 조회"""
        query = """
        SELECT plcy_no, last_mdfcn_dt 
        FROM policies 
        WHERE plcy_no IS NOT NULL
        """
        
        self.cursor.execute(query)
        results = self.cursor.fetchall()
        
        existing_policies = {}
        for plcy_no, last_mdfcn_dt in results:
            if last_mdfcn_dt:
                # 문자열을 datetime으로 변환 (필요시)
                if isinstance(last_mdfcn_dt, str):
                    try:
                        last_mdfcn_dt = pd.to_datetime(last_mdfcn_dt)
                    except:
                        last_mdfcn_dt = None
                existing_policies[plcy_no] = last_mdfcn_dt
            else:
                existing_policies[plcy_no] = None
        
        logger.info(f"기존 정책 {len(existing_policies)}개 정보 조회 완료")
        return existing_policies
    
    def filter_data_for_update(self, df) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        데이터를 세 그룹으로 분류:
        1. 새로운 정책 (INSERT)
        2. 수정된 정책 (UPDATE) - 수정일시가 더 최신인 경우
        3. 변경 없는 정책 (SKIP) - 기존과 동일하거나 더 오래된 경우
        """
        existing_policies = self.get_existing_policies_info()
        
        new_policies = []
        updated_policies = []
        skipped_policies = []
        
        for _, row in df.iterrows():
            plcy_no = row['정책번호']
            new_last_mdfcn_dt = row['최종수정일시']
            
            # 새로운 데이터의 수정일시를 datetime으로 변환
            if pd.notna(new_last_mdfcn_dt):
                try:
                    new_last_mdfcn_dt = pd.to_datetime(new_last_mdfcn_dt)
                except:
                    new_last_mdfcn_dt = None
            else:
                new_last_mdfcn_dt = None
            
            if plcy_no not in existing_policies:
                # 새로운 정책
                new_policies.append(row)
                logger.debug(f"새로운 정책: {plcy_no}")
            else:
                existing_last_mdfcn_dt = existing_policies[plcy_no]
                
                # 수정일시 비교
                should_update = False
                
                if new_last_mdfcn_dt is None and existing_last_mdfcn_dt is None:
                    # 둘 다 수정일시가 없으면 업데이트
                    should_update = True
                elif new_last_mdfcn_dt is None:
                    # 새 데이터에 수정일시가 없으면 스킵
                    should_update = False
                elif existing_last_mdfcn_dt is None:
                    # 기존 데이터에 수정일시가 없으면 업데이트
                    should_update = True
                else:
                    # 둘 다 수정일시가 있으면 비교
                    should_update = new_last_mdfcn_dt > existing_last_mdfcn_dt
                
                if should_update:
                    updated_policies.append(row)
                    logger.debug(f"수정된 정책: {plcy_no} (기존: {existing_last_mdfcn_dt}, 새로운: {new_last_mdfcn_dt})")
                else:
                    skipped_policies.append(row)
                    logger.debug(f"변경 없는 정책: {plcy_no} (기존: {existing_last_mdfcn_dt}, 새로운: {new_last_mdfcn_dt})")
        
        new_df = pd.DataFrame(new_policies) if new_policies else pd.DataFrame()
        updated_df = pd.DataFrame(updated_policies) if updated_policies else pd.DataFrame()
        skipped_df = pd.DataFrame(skipped_policies) if skipped_policies else pd.DataFrame()
        
        logger.info(f"데이터 분류 완료 - 새로운: {len(new_df)}, 수정: {len(updated_df)}, 스킵: {len(skipped_df)}")
        
        return new_df, updated_df, skipped_df
    
    def create_embedding_text(self, row):
        """정책 데이터로부터 임베딩용 종합 텍스트 생성 (모든 테이블 데이터 포함)"""
        text_parts = []
        
        # ========== 정책 기본정보 (policies 테이블) ==========
        if pd.notna(row['정책명']):
            text_parts.append(f"정책명: {row['정책명']}")
        
        if pd.notna(row['정책설명내용']):
            text_parts.append(f"정책설명: {row['정책설명내용']}")
        
        if pd.notna(row['정책지원내용']):
            text_parts.append(f"지원내용: {row['정책지원내용']}")
        
        if pd.notna(row['정책신청방법내용']):
            text_parts.append(f"신청방법: {row['정책신청방법내용']}")
        
        if pd.notna(row['심사방법내용']):
            text_parts.append(f"심사방법: {row['심사방법내용']}")
        
        if pd.notna(row['제출서류내용']):
            text_parts.append(f"제출서류: {row['제출서류내용']}")
        
        if pd.notna(row['기타사항내용']):
            text_parts.append(f"기타사항: {row['기타사항내용']}")
        
        # ========== 정책 메타데이터 (policy_metadata 테이블) ==========
        if pd.notna(row['정책대분류명']):
            text_parts.append(f"대분류: {row['정책대분류명']}")
        
        if pd.notna(row['정책중분류명']):
            text_parts.append(f"중분류: {row['정책중분류명']}")
        
        if pd.notna(row['정책키워드명']):
            text_parts.append(f"키워드: {row['정책키워드명']}")
        
        if pd.notna(row['주관기관코드명']):
            text_parts.append(f"주관기관: {row['주관기관코드명']}")
        
        if pd.notna(row['운영기관코드명']):
            text_parts.append(f"운영기관: {row['운영기관코드명']}")
        
        if pd.notna(row['정책제공방법코드']):
            text_parts.append(f"제공방법: {row['정책제공방법코드']}")
        
        if pd.notna(row['신청기간구분코드']):
            text_parts.append(f"신청기간구분: {row['신청기간구분코드']}")
        
        if pd.notna(row['사업기간구분코드']):
            text_parts.append(f"사업기간구분: {row['사업기간구분코드']}")
        
        if pd.notna(row['사업기간기타내용']):
            text_parts.append(f"사업기간기타: {row['사업기간기타내용']}")
        
        if pd.notna(row['정책특화요건코드']):
            text_parts.append(f"특화요건: {row['정책특화요건코드']}")
        
        # ========== 정책 조건 (policy_conditions 테이블) ==========
        if pd.notna(row['지원대상최소연령']) and pd.notna(row['지원대상최대연령']):
            text_parts.append(f"지원연령: {int(row['지원대상최소연령'])}세부터 {int(row['지원대상최대연령'])}세까지")
        elif pd.notna(row['지원대상최소연령']):
            text_parts.append(f"최소연령: {int(row['지원대상최소연령'])}세 이상")
        elif pd.notna(row['지원대상최대연령']):
            text_parts.append(f"최대연령: {int(row['지원대상최대연령'])}세 이하")
        
        if pd.notna(row['결혼상태코드']):
            text_parts.append(f"결혼상태: {row['결혼상태코드']}")
        
        if pd.notna(row['정책전공요건코드']):
            text_parts.append(f"전공요건: {row['정책전공요건코드']}")
        
        if pd.notna(row['정책취업요건코드']):
            text_parts.append(f"취업요건: {row['정책취업요건코드']}")
        
        if pd.notna(row['정책학력요건코드']):
            text_parts.append(f"학력요건: {row['정책학력요건코드']}")
        
        if pd.notna(row['정책거주지역코드']):
            text_parts.append(f"거주지역: {row['정책거주지역코드']}")
        
        if pd.notna(row['소득조건구분코드']):
            text_parts.append(f"소득조건: {row['소득조건구분코드']}")
        
        # ========== 정책 조건 상세 (policy_condition_details 테이블) ==========
        if pd.notna(row['소득기타내용']):
            text_parts.append(f"소득기타조건: {row['소득기타내용']}")
        
        if pd.notna(row['추가신청자격조건내용']):
            text_parts.append(f"추가자격조건: {row['추가신청자격조건내용']}")
        
        if pd.notna(row['참여제안대상내용']):
            text_parts.append(f"참여대상: {row['참여제안대상내용']}")
        
        # ========== 날짜 정보 ==========
        try:
            if pd.notna(row['신청시작일자']) and pd.notna(row['신청종료일자']):
                start_date = pd.to_datetime(row['신청시작일자'], errors='coerce')
                end_date = pd.to_datetime(row['신청종료일자'], errors='coerce')
                if pd.notna(start_date) and pd.notna(end_date):
                    start_str = start_date.strftime('%Y년 %m월 %d일')
                    end_str = end_date.strftime('%Y년 %m월 %d일')
                    text_parts.append(f"신청기간: {start_str}부터 {end_str}까지")
        except:
            pass
        
        try:
            if pd.notna(row['사업기간시작일자']) and pd.notna(row['사업기간종료일자']):
                biz_start = pd.to_datetime(row['사업기간시작일자'], errors='coerce')
                biz_end = pd.to_datetime(row['사업기간종료일자'], errors='coerce')
                if pd.notna(biz_start) and pd.notna(biz_end):
                    biz_start_str = biz_start.strftime('%Y년 %m월 %d일')
                    biz_end_str = biz_end.strftime('%Y년 %m월 %d일')
                    text_parts.append(f"사업기간: {biz_start_str}부터 {biz_end_str}까지")
        except:
            pass
        
        # ========== URL 정보는 임베딩에서 제외 (의미적 검색에 부적합) ==========
        
        # 최종 텍스트 생성 (중복 제거 및 정리)
        final_text = " ".join(text_parts)
        
        # # 텍스트 길이 제한 (OpenAI 토큰 제한 고려)
        # if len(final_text) > 8000:  # 대략 2000 토큰 제한
        #     final_text = final_text[:8000] + "..."
        
        return final_text
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """배치로 임베딩 생성"""
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            try:
                response = openai.embeddings.create(
                    input=batch_texts,
                    model="text-embedding-3-large"
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
                logger.info(f"임베딩 생성 진행: {min(i + batch_size, len(texts))}/{len(texts)}")
                
                # API 속도 제한 방지
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"임베딩 생성 실패 (배치 {i//batch_size + 1}): {e}")
                # 실패한 배치에 대해 빈 임베딩 추가
                batch_embeddings = [[0.0] * 3072 for _ in batch_texts]
                embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def insert_policies(self, df, is_update=False):
        """통합 정책 테이블에 모든 정보 삽입 또는 업데이트"""
        if df.empty:
            logger.info(f"{'업데이트' if is_update else '삽입'}할 정책 데이터가 없습니다.")
            return
        
        policies_data = []
        
        for _, row in df.iterrows():
            policy_data = (
                # 기본 정책 정보
                row['정책번호'],
                row['정책명'],
                row['정책설명내용'],
                row['정책지원내용'],
                row['정책신청방법내용'],
                row['심사방법내용'],
                row['제출서류내용'],
                row['기타사항내용'],
                int(row['조회수']) if pd.notna(row['조회수']) else 0,
                row['최초등록일시'],
                row['최종수정일시'],
                row['신청시작일자'],
                row['신청종료일자'],
                
                # 정책 조건 정보
                int(row['지원대상최소연령']) if pd.notna(row['지원대상최소연령']) else None,
                int(row['지원대상최대연령']) if pd.notna(row['지원대상최대연령']) else None,
                row['결혼상태코드'],
                row['정책전공요건코드'],
                row['정책취업요건코드'],
                row['정책학력요건코드'],
                row['정책거주지역코드'],
                row['소득조건구분코드'],
                row['소득기타내용'],
                row['추가신청자격조건내용'],
                row['참여제안대상내용'],
                
                # 정책 메타데이터 정보
                row['정책대분류명'],
                row['정책중분류명'],
                row['정책제공방법코드'],
                row['정책키워드명'],
                row['주관기관코드명'],
                row['운영기관코드명'],
                row['신청기간구분코드'],
                row['사업기간구분코드'],
                row['사업기간시작일자'],
                row['사업기간종료일자'],
                row['사업기간기타내용'],
                row['정책특화요건코드'],
                
                # 정책 URL 정보
                row['신청URL주소'],
                row['참고URL주소1'],
                row['참고URL주소2']
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
        """
        
        execute_values(self.cursor, query, policies_data)
        self.conn.commit()
        logger.info(f"통합 정책 테이블에 {len(policies_data)}개 레코드 {'업데이트' if is_update else '삽입'} 완료")
    
    def insert_policy_embeddings(self, df, is_update=False):
        """정책 임베딩 정보 삽입 또는 업데이트"""
        if df.empty:
            logger.info(f"{'업데이트' if is_update else '삽입'}할 임베딩 데이터가 없습니다.")
            return
            
        if not openai.api_key:
            logger.warning("OpenAI API 키가 없어 임베딩 생성을 건너뜁니다.")
            return
        
        logger.info(f"정책 임베딩 {'업데이트' if is_update else '생성'} 시작...")
        
        # 임베딩용 텍스트 생성
        embedding_texts = []
        policy_numbers = []
        
        for _, row in df.iterrows():
            text = self.create_embedding_text(row)
            embedding_texts.append(text)
            policy_numbers.append(row['정책번호'])
        
        # 임베딩 생성
        embeddings = self.generate_embeddings_batch(embedding_texts)
        
        # 임베딩 데이터 삽입
        embedding_data = []
        for i, embedding in enumerate(embeddings):
            embedding_info = (
                policy_numbers[i],
                embedding
            )
            embedding_data.append(embedding_info)
        
        query = """
        INSERT INTO policy_embeddings (plcy_no, embedding)
        VALUES %s
        ON CONFLICT (plcy_no) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            updated_at = CURRENT_TIMESTAMP
        """
        
        execute_values(self.cursor, query, embedding_data)
        self.conn.commit()
        logger.info(f"정책 임베딩 테이블에 {len(embedding_data)}개 레코드 {'업데이트' if is_update else '삽입'} 완료")
    
    def insert_all_data(self, csv_file_path, include_embeddings=True):
        """전체 데이터 삽입 프로세스 (조건부 업데이트 포함)"""
        try:
            # CSV 데이터 로드 및 전처리
            df = self.load_csv_data(csv_file_path)
            df = self.preprocess_data(df)
            
            # DB 연결
            self.connect_db()
            
            # 데이터를 새로운/수정된/변경없음으로 분류
            new_df, updated_df, skipped_df = self.filter_data_for_update(df)
            
            # 새로운 정책 데이터 삽입
            if not new_df.empty:
                logger.info(f"새로운 정책 {len(new_df)}개 삽입 시작")
                self.insert_policies(new_df, is_update=False)
                
                if include_embeddings:
                    self.insert_policy_embeddings(new_df, is_update=False)
            
            # 수정된 정책 데이터 업데이트
            if not updated_df.empty:
                logger.info(f"수정된 정책 {len(updated_df)}개 업데이트 시작")
                self.insert_policies(updated_df, is_update=True)
                
                if include_embeddings:
                    self.insert_policy_embeddings(updated_df, is_update=True)
            
            # 요약 로그
            logger.info("=" * 50)
            logger.info("데이터 처리 요약:")
            logger.info(f"- 새로운 정책: {len(new_df)}개")
            logger.info(f"- 업데이트된 정책: {len(updated_df)}개") 
            logger.info(f"- 변경 없는 정책: {len(skipped_df)}개")
            logger.info(f"- 총 처리된 정책: {len(new_df) + len(updated_df)}개")
            logger.info(f"- 전체 입력 정책: {len(df)}개")
            logger.info("=" * 50)
            
            logger.info("모든 데이터 처리 완료")
            
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
    csv_file_path = '../청년정책목록_전처리완료_2025-06-17.csv'
    
    # OpenAI API 키 (환경변수에서 자동 로드)
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    # 데이터 삽입 실행
    inserter = YouthPolicyDataInserter(db_config, openai_api_key)
    inserter.insert_all_data(csv_file_path, include_embeddings=True)

if __name__ == "__main__":
    main()
