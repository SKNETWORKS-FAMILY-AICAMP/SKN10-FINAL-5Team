"""
청년정책 RAG 시스템
사용자 질의에 대해 유사도 기반으로 관련 정책을 검색하고 LLM에게 컨텍스트를 제공하는 시스템
작성일: 2025-06-18
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import openai
from dotenv import load_dotenv
from datetime import datetime

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YouthPolicyRAG:
    """청년정책 RAG 시스템 클래스"""
    
    def __init__(self, db_config: Dict[str, Any], openai_api_key: Optional[str] = None):
        """
        RAG 시스템 초기화
        
        Args:
            db_config: PostgreSQL 데이터베이스 연결 설정
            openai_api_key: OpenAI API 키
        """
        self.db_config = db_config
        self.conn = None
        self.cursor = None
        
        # OpenAI 클라이언트 설정
        if openai_api_key:
            openai.api_key = openai_api_key
        else:
            openai.api_key = os.getenv('OPENAI_API_KEY')
        
        if not openai.api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        
        # RAG 설정
        self.top_k = int(os.getenv('TOP_K', 5))
        self.similarity_threshold = float(os.getenv('SIMILARITY_THRESHOLD', 0.7))
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
        
        logger.info("RAG 시스템 초기화 완료")
    
    def connect_db(self):
        """데이터베이스 연결"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("데이터베이스 연결 성공")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
    
    def close_db(self):
        """데이터베이스 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("데이터베이스 연결 종료")
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        사용자 질의에 대한 임베딩 생성
        
        Args:
            query: 사용자 질의 텍스트
        
        Returns:
            임베딩 벡터
        """
        try:
            response = openai.embeddings.create(
                input=query,
                model=self.embedding_model
            )
            embedding = response.data[0].embedding
            logger.info(f"질의 임베딩 생성 완료: {len(embedding)}차원")
            return embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            raise
    
    def search_similar_policies(self, query_embedding: List[float], top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        임베딩 유사도를 기반으로 관련 정책 검색
        
        Args:
            query_embedding: 질의 임베딩 벡터
            top_k: 검색할 정책 수
        
        Returns:
            유사한 정책들의 리스트
        """
        if top_k is None:
            top_k = self.top_k
        
        # 각 검색마다 새로운 DB 연결 사용
        conn = None
        cursor = None
        
        try:
            # 새 DB 연결 생성
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            logger.info("데이터베이스 연결 성공")
            
            # pgvector의 코사인 유사도를 사용한 검색 쿼리 - policies 테이블의 모든 컬럼 조회
            search_query = """
            SELECT 
                -- 기본 정책 정보
                p.plcy_no,
                p.plcy_nm,
                p.plcy_expln_cn,
                p.plcy_sprt_cn,
                p.plcy_aply_mthd_cn,
                p.srng_mthd_cn,
                p.sbmsn_dcmnt_cn,
                p.etc_mttr_cn,
                p.inq_cnt,
                p.aply_bgng_ymd,
                p.aply_end_ymd,
                
                -- 정책 조건 정보
                p.sprt_trgt_min_age,
                p.sprt_trgt_max_age,
                p.mrg_stts_cd,
                p.plcy_major_cd,
                p.job_cd,
                p.school_cd,
                p.zip_cd,
                p.earn_cnd_se_cd,
                p.earn_etc_cn,
                p.add_aply_qlfcc_cn,
                p.ptcp_prp_trgt_cn,
                
                -- 정책 메타데이터 정보
                p.lclsf_nm,
                p.mclsf_nm,
                p.plcy_pvsn_mthd_cd,
                p.plcy_kywd_nm,
                p.sprvsn_inst_cd_nm,
                p.oper_inst_cd_nm,
                p.aply_prd_se_cd,
                p.biz_prd_se_cd,
                p.biz_prd_bgng_ymd,
                p.biz_prd_end_ymd,
                p.biz_prd_etc_cn,
                p.s_biz_cd,
                
                -- 정책 URL 정보
                p.aply_url_addr,
                p.ref_url_addr1,
                p.ref_url_addr2,
                
                -- 유사도 점수
                (1 - (pe.embedding <=> %s::vector)) AS similarity_score
            FROM policies p
            JOIN policy_embeddings pe ON p.plcy_no = pe.plcy_no
            WHERE (1 - (pe.embedding <=> %s::vector)) >= %s
            ORDER BY pe.embedding <=> %s::vector
            LIMIT %s;
            """
            
            # 임베딩을 문자열로 변환
            embedding_str = str(query_embedding)
            
            cursor.execute(search_query, (
                embedding_str, 
                embedding_str, 
                self.similarity_threshold,
                embedding_str,
                top_k
            ))
            
            results = cursor.fetchall()
            
            # 결과를 딕셔너리 리스트로 변환
            policies = []
            for row in results:
                policy = dict(row)
                
                # 날짜 형식 변환 (DATE 타입)
                date_fields = ['aply_bgng_ymd', 'aply_end_ymd', 'biz_prd_bgng_ymd', 'biz_prd_end_ymd']
                for field in date_fields:
                    if policy.get(field):
                        policy[field] = policy[field].strftime('%Y-%m-%d') if policy[field] else None
                
                policies.append(policy)
            
            logger.info(f"검색 완료: {len(policies)}개 정책 찾음")
            return policies
            
        except Exception as e:
            logger.error(f"정책 검색 실패: {e}")
            raise
        finally:
            # DB 연결 정리
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def format_policies_for_llm(self, policies: List[Dict[str, Any]]) -> str:
        """
        검색된 정책들을 LLM용 JSON 형식으로 포맷팅
        
        Args:
            policies: 검색된 정책 리스트
        
        Returns:
            JSON 형식의 정책 정보 문자열
        """
        formatted_policies = []
        
        for policy in policies:
            formatted_policy = {
                # 기본 정책 정보
                "정책번호": policy.get('plcy_no'),
                "정책명": policy.get('plcy_nm'),
                "정책설명": policy.get('plcy_expln_cn'),
                "지원내용": policy.get('plcy_sprt_cn'),
                "신청방법": policy.get('plcy_aply_mthd_cn'),
                "심사방법": policy.get('srng_mthd_cn'),
                "제출서류": policy.get('sbmsn_dcmnt_cn'),
                "기타사항": policy.get('etc_mttr_cn'),
                "조회수": policy.get('inq_cnt'),
                
                # 신청 및 사업 기간
                "신청기간": {
                    "시작일": policy.get('aply_bgng_ymd'),
                    "종료일": policy.get('aply_end_ymd'),
                    "기간구분코드": policy.get('aply_prd_se_cd')
                },
                "사업기간": {
                    "시작일": policy.get('biz_prd_bgng_ymd'),
                    "종료일": policy.get('biz_prd_end_ymd'),
                    "기간구분코드": policy.get('biz_prd_se_cd'),
                    "기타내용": policy.get('biz_prd_etc_cn')
                },
                
                # 지원 대상 조건
                "지원대상연령": {
                    "최소": policy.get('sprt_trgt_min_age'),
                    "최대": policy.get('sprt_trgt_max_age')
                },
                "결혼상태코드": policy.get('mrg_stts_cd'),
                "전공요건코드": policy.get('plcy_major_cd'),
                "취업요건코드": policy.get('job_cd'),
                "학력요건코드": policy.get('school_cd'),
                "거주지역코드": policy.get('zip_cd'),
                "소득조건": {
                    "구분코드": policy.get('earn_cnd_se_cd'),
                    "기타내용": policy.get('earn_etc_cn')
                },
                "추가신청자격요건": policy.get('add_aply_qlfcc_cn'),
                "참여제안대상내용": policy.get('ptcp_prp_trgt_cn'),
                
                # 정책 분류 및 메타데이터
                "정책분류": {
                    "대분류": policy.get('lclsf_nm'),
                    "중분류": policy.get('mclsf_nm')
                },
                "정책제공방법코드": policy.get('plcy_pvsn_mthd_cd'),
                "키워드": policy.get('plcy_kywd_nm'),
                "주관기관": policy.get('sprvsn_inst_cd_nm'),
                "운영기관": policy.get('oper_inst_cd_nm'),
                "정책특화요건코드": policy.get('s_biz_cd'),
                
                # URL 정보
                "관련URL": {
                    "신청URL": policy.get('aply_url_addr'),
                    "참고URL1": policy.get('ref_url_addr1'),
                    "참고URL2": policy.get('ref_url_addr2')
                },
                
                # 시스템 정보
                "유사도점수": round(policy.get('similarity_score', 0), 4)
            }
            formatted_policies.append(formatted_policy)
        
        return json.dumps(formatted_policies, ensure_ascii=False, indent=2)
    
    def generate_llm_response(self, query: str, policies_context: str) -> str:
        """
        LLM을 사용하여 최종 답변 생성
        
        Args:
            query: 사용자 질의
            policies_context: 검색된 정책 정보 (JSON 형식)
        
        Returns:
            LLM이 생성한 답변
        """
        try:
            system_prompt = """
당신은 청년정책 전문 상담사입니다. 사용자의 질문에 대해 제공된 정책 정보를 바탕으로 정확하고 도움이 되는 답변을 제공해주세요.

답변 시 다음 사항을 고려해주세요:
1. 정책번호를 포함하여 답변해주세요.
2. 제공된 정책 정보에 없는 내용은 추측하지 말고, 정확한 정보만을 바탕으로 답변해주세요.
"""
            
            user_prompt = f"""
사용자 질문: {query}

관련 정책 정보:
{policies_context}

위 정책 정보를 바탕으로 사용자의 질문에 대해 상세하고 도움이 되는 답변을 제공해주세요.
"""
            
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            logger.info("LLM 답변 생성 완료")
            return answer
            
        except Exception as e:
            logger.error(f"LLM 답변 생성 실패: {e}")
            raise
    
    def query(self, user_query: str, include_llm_response: bool = True) -> Dict[str, Any]:
        """
        전체 RAG 파이프라인 실행
        
        Args:
            user_query: 사용자 질의
            include_llm_response: LLM 답변 포함 여부
        
        Returns:
            검색 결과와 LLM 답변을 포함한 딕셔너리
        """
        # 각 질의마다 새로운 DB 연결 사용
        conn = None
        cursor = None
        
        try:
            logger.info(f"사용자 질의: {user_query}")
            
            # 1. 질의 임베딩 생성
            query_embedding = self.generate_query_embedding(user_query)
            
            # 2. 유사한 정책 검색
            similar_policies = self.search_similar_policies(query_embedding)
            
            # 3. 정책 정보 포맷팅
            policies_context = self.format_policies_for_llm(similar_policies)
            
            result = {
                "query": user_query,
                "timestamp": datetime.now().isoformat(),
                "found_policies_count": len(similar_policies),
                "policies": similar_policies,
                "policies_json": policies_context
            }
            
            # 4. LLM 답변 생성 (선택적)
            if include_llm_response:
                llm_response = self.generate_llm_response(user_query, policies_context)
                result["llm_response"] = llm_response
            
            logger.info("RAG 파이프라인 실행 완료")
            return result
            
        except Exception as e:
            logger.error(f"RAG 파이프라인 실행 실패: {e}")
            raise


def main():
    """RAG 시스템 테스트"""
    # DB 연결 설정
    db_config = {
        'host': os.getenv("DB_HOST", 'localhost'),
        'database': os.getenv("DB_NAME", 'youth_policy'),
        'user': os.getenv("DB_USER", 'postgres'),
        'password': os.getenv("DB_PASSWORD", 'your_password'),
        'port': os.getenv("DB_PORT", 5432)
    }
    
    # RAG 시스템 초기화
    rag = YouthPolicyRAG(db_config)
    
    # 테스트 질의들
    test_queries = [
        "제가 부산광역시 부산진구에 거주하고 있는데 청년 우대 반값 중개수수료 사업 정책을 받을 수 있나요?",
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"질문: {query}")
        print('='*80)
        
        try:
            result = rag.query(query)
            
            print(f"\n검색된 정책 수: {result['found_policies_count']}")
            
            if result['found_policies_count'] > 0:
                print("\n=== 검색된 정책들 ===")
                for i, policy in enumerate(result['policies'], 1):
                    print(f"\n{i}. {policy['plcy_nm']}")
                    print(f"   유사도: {policy.get('similarity_score', 0):.4f}")
                    print(f"   분류: {policy['lclsf_nm']} > {policy['mclsf_nm']}")
                
                print(f"\n=== LLM 답변 ===")
                print(result['llm_response'])
            else:
                print("관련 정책을 찾을 수 없습니다.")
                
        except Exception as e:
            print(f"오류 발생: {e}")


if __name__ == "__main__":
    main()