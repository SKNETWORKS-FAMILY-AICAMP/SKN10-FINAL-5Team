#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG (Retrieval-Augmented Generation) 시스템
사용자 질문을 임베딩하여 PostgreSQL의 정책 데이터와 유사도 분석 후 답변 생성
"""

import os
import openai
import psycopg2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import logging
from datetime import datetime

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PolicyDocument:
    """정책 문서 정보를 담는 데이터 클래스"""
    plcy_no: str
    plcy_nm: str
    plcy_expln_cn: str
    plcy_sprt_cn: str
    plcy_aply_mthd_cn: str
    lclsf_nm: str
    mclsf_nm: str
    similarity_score: float
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    sprvsn_inst_cd_nm: Optional[str] = None
    aply_url_addr: Optional[str] = None

class YouthPolicyRAG:
    """청년 정책 RAG 시스템"""
    
    def __init__(self):
        """RAG 시스템 초기화"""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        openai.api_key = self.openai_api_key
        
        # PostgreSQL 연결 설정
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'youth_policy'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }
        
        # 임베딩 모델 설정
        self.embedding_model = "text-embedding-3-large"
        self.embedding_dimension = 3072
        
        # 검색 파라미터
        self.top_k = 5  # 상위 K개 문서 검색
        self.similarity_threshold = 0.5  # 유사도 임계값
        
    def connect_db(self) -> psycopg2.extensions.connection:
        """PostgreSQL 데이터베이스 연결"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
    
    def get_embedding(self, text: str) -> List[float]:
        """텍스트를 OpenAI의 text-embedding-3-large 모델로 임베딩"""
        try:
            # 텍스트 전처리
            text = text.strip().replace('\n', ' ')
            if not text:
                raise ValueError("빈 텍스트는 임베딩할 수 없습니다.")
            
            # OpenAI API 호출
            response = openai.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            logger.info(f"임베딩 생성 완료: 차원 {len(embedding)}")
            return embedding
            
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            raise
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def search_similar_policies(self, query_embedding: List[float], top_k: int = None) -> List[PolicyDocument]:
        """임베딩 유사도 기반 정책 검색"""
        if top_k is None:
            top_k = self.top_k
            
        conn = None
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            
            # pgvector의 코사인 유사도를 사용한 검색 쿼리
            query = """
            SELECT 
                p.plcy_no,
                p.plcy_nm,
                p.plcy_expln_cn,
                p.plcy_sprt_cn,
                p.plcy_aply_mthd_cn,
                pm.lclsf_nm,
                pm.mclsf_nm,
                pc.sprt_trgt_min_age,
                pc.sprt_trgt_max_age,
                pm.sprvsn_inst_cd_nm,
                pu.aply_url_addr,
                (pe.embedding <=> %s::vector) as distance
            FROM policies p
            JOIN policy_embeddings pe ON p.plcy_no = pe.plcy_no
            LEFT JOIN policy_metadata pm ON p.plcy_no = pm.plcy_no
            LEFT JOIN policy_conditions pc ON p.plcy_no = pc.plcy_no
            LEFT JOIN policy_urls pu ON p.plcy_no = pu.plcy_no
            ORDER BY pe.embedding <=> %s::vector
            LIMIT %s;
            """
            
            # 임베딩을 문자열로 변환 (PostgreSQL vector 타입 형식)
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            
            cursor.execute(query, (embedding_str, embedding_str, top_k))
            results = cursor.fetchall()
            
            policies = []
            for row in results:
                # 거리를 유사도로 변환 (1 - distance)
                similarity_score = 1 - row[11]
                
                # 유사도 임계값 적용
                if similarity_score >= self.similarity_threshold:
                    policy = PolicyDocument(
                        plcy_no=row[0],
                        plcy_nm=row[1],
                        plcy_expln_cn=row[2] or "",
                        plcy_sprt_cn=row[3] or "",
                        plcy_aply_mthd_cn=row[4] or "",
                        lclsf_nm=row[5] or "",
                        mclsf_nm=row[6] or "",
                        age_min=row[7],
                        age_max=row[8],
                        sprvsn_inst_cd_nm=row[9] or "",
                        aply_url_addr=row[10] or "",
                        similarity_score=similarity_score
                    )
                    policies.append(policy)
            
            logger.info(f"검색된 정책 수: {len(policies)}")
            return policies
            
        except Exception as e:
            logger.error(f"정책 검색 실패: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def generate_context(self, policies: List[PolicyDocument]) -> str:
        """검색된 정책들을 컨텍스트로 변환"""
        if not policies:
            return "관련 정책을 찾을 수 없습니다."
        
        context_parts = []
        for i, policy in enumerate(policies, 1):
            age_info = ""
            if policy.age_min is not None and policy.age_max is not None:
                age_info = f" (지원연령: {policy.age_min}~{policy.age_max}세)"
            elif policy.age_min is not None:
                age_info = f" (지원연령: {policy.age_min}세 이상)"
            elif policy.age_max is not None:
                age_info = f" (지원연령: {policy.age_max}세 이하)"
            
            context = f"""
정책 {i}: {policy.plcy_nm}{age_info}
- 정책번호: {policy.plcy_no}
- 분류: {policy.lclsf_nm} > {policy.mclsf_nm}
- 정책설명: {policy.plcy_expln_cn[:200]}{'...' if len(policy.plcy_expln_cn) > 200 else ''}
- 지원내용: {policy.plcy_sprt_cn[:200]}{'...' if len(policy.plcy_sprt_cn) > 200 else ''}
- 신청방법: {policy.plcy_aply_mthd_cn[:150]}{'...' if len(policy.plcy_aply_mthd_cn) > 150 else ''}
- 주관기관: {policy.sprvsn_inst_cd_nm}
- 유사도: {policy.similarity_score:.3f}
"""
            if policy.aply_url_addr:
                context += f"- 신청URL: {policy.aply_url_addr}\n"
            
            context_parts.append(context.strip())
        
        return "\n\n".join(context_parts)
    
    def generate_answer(self, query: str, context: str) -> str:
        """GPT 모델을 사용하여 답변 생성"""
        try:
            system_prompt = """
당신은 청년 정책 전문 상담사입니다. 사용자의 질문에 대해 제공된 정책 정보를 바탕으로 정확하고 도움이 되는 답변을 제공하세요.
답변 시 정책번호를 포함하여, 사용자가 쉽게 이해할 수 있도록 상세하게 설명해주세요.
"""
            
            user_prompt = f"""
사용자 질문: {query}

관련 정책 정보:
{context}

위 정보를 바탕으로 사용자의 질문에 대한 상세하고 도움이 되는 답변을 작성해주세요.
"""
            
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content
            logger.info("답변 생성 완료")
            return answer
            
        except Exception as e:
            logger.error(f"답변 생성 실패: {e}")
            return f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {str(e)}"
    
    def ask(self, query: str) -> Dict[str, any]:
        """사용자 질문에 대한 RAG 기반 답변 생성"""
        try:
            start_time = datetime.now()
            logger.info(f"질문 처리 시작: {query}")
            
            # 1. 질문 임베딩 생성
            query_embedding = self.get_embedding(query)
            
            # 2. 유사한 정책 검색
            similar_policies = self.search_similar_policies(query_embedding)
            
            if not similar_policies:
                return {
                    "answer": "죄송합니다. 질문과 관련된 청년 정책을 찾을 수 없습니다. 다른 키워드로 다시 검색해보시거나, 관련 기관에 직접 문의해보시기 바랍니다.",
                    "policies": [],
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
            
            # 3. 컨텍스트 생성
            context = self.generate_context(similar_policies)
            
            # 4. 답변 생성
            answer = self.generate_answer(query, context)
            
            # 5. 결과 반환
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"질문 처리 완료 ({processing_time:.2f}초)")
            
            return {
                "answer": answer,
                "policies": [
                    {
                        "policy_number": policy.plcy_no,
                        "policy_name": policy.plcy_nm,
                        "category": f"{policy.lclsf_nm} > {policy.mclsf_nm}",
                        "similarity_score": policy.similarity_score,
                        "age_range": f"{policy.age_min or '제한없음'}~{policy.age_max or '제한없음'}세",
                        "institution": policy.sprvsn_inst_cd_nm,
                        "apply_url": policy.aply_url_addr
                    }
                    for policy in similar_policies
                ],
                "processing_time": processing_time
            }
            
        except Exception as e:
            logger.error(f"질문 처리 실패: {e}")
            return {
                "answer": f"죄송합니다. 질문 처리 중 오류가 발생했습니다: {str(e)}",
                "policies": [],
                "processing_time": 0
            }

def main():
    """테스트용 메인 함수"""
    try:
        # RAG 시스템 초기화
        rag = YouthPolicyRAG()
        
        # 테스트 질문들
        test_queries = [
            "서울사는 28세 남자가 받을 수 있는 창업 지원 정책이 있나요?",
        ]
        
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"질문: {query}")
            print('='*60)
            
            result = rag.ask(query)
            print(f"\n답변:\n{result['answer']}")
            print(f"\n관련 정책 수: {len(result['policies'])}")
            print(f"처리 시간: {result['processing_time']:.2f}초")
            
            if result['policies']:
                print("\n관련 정책 목록:")
                for i, policy in enumerate(result['policies'], 1):
                    print(f"{i}. {policy['policy_name']} (유사도: {policy['similarity_score']:.3f})")
            
            print("\n" + "-"*60)
    
    except Exception as e:
        logger.error(f"메인 함수 실행 실패: {e}")

if __name__ == "__main__":
    main()