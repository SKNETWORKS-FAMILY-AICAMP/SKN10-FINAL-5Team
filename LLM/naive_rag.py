"""
Naive RAG (Retrieval-Augmented Generation) 시스템
사용자 질의를 임베딩하고 벡터 DB에서 유사한 문서를 검색하여 GPT-4o로 답변을 생성하는 시스템
"""
import os
import pickle
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import numpy as np
import faiss
from openai import OpenAI
import pandas as pd

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NaiveRAG:
    """
    간단한 RAG 시스템 구현
    """
    
    def __init__(self, 
                 vector_db_path: str = "../data/vector_db_openai_large_combined",
                 model_name: str = "gpt-4o",
                 embedding_model: str = "text-embedding-3-large",
                 top_k: int = 5):
        """
        RAG 시스템 초기화
        
        Args:
            vector_db_path: 벡터 DB 파일들이 위치한 경로
            model_name: 답변 생성에 사용할 GPT 모델명
            embedding_model: 임베딩 생성에 사용할 OpenAI 모델명
            top_k: 검색할 문서 수
        """
        self.vector_db_path = vector_db_path
        self.model_name = model_name
        self.embedding_model = embedding_model
        self.top_k = top_k
        
        # OpenAI 클라이언트 초기화
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        
        self.client = OpenAI(api_key=api_key)
        
        # 벡터 DB 로드
        self._load_vector_db()
        
    def _load_vector_db(self):
        """벡터 데이터베이스 로드"""
        try:
            # FAISS 인덱스 로드
            index_path = os.path.join(self.vector_db_path, "index.faiss")
            self.index = faiss.read_index(index_path)
            logger.info(f"FAISS 인덱스 로드 완료: {self.index.ntotal}개 벡터")
            
            # 문서 텍스트 로드
            documents_path = os.path.join(self.vector_db_path, "documents.pkl")
            with open(documents_path, 'rb') as f:
                self.documents = pickle.load(f)
            logger.info(f"문서 텍스트 로드 완료: {len(self.documents)}개 문서")
            
            # 메타데이터 로드
            metadata_path = os.path.join(self.vector_db_path, "metadata.pkl")
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            logger.info(f"메타데이터 로드 완료: {len(self.metadata)}개 항목")
            
        except Exception as e:
            logger.error(f"벡터 DB 로드 실패: {str(e)}")
            raise
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """텍스트를 임베딩 벡터로 변환"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            return embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {str(e)}")
            raise
    
    def search_similar_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        쿼리와 유사한 문서 검색
        
        Args:
            query: 사용자 질의
            
        Returns:
            검색된 문서들의 리스트 (텍스트, 메타데이터, 유사도 포함)
        """
        try:
            # 쿼리 임베딩 생성
            query_embedding = self._get_embedding(query)
            query_embedding = query_embedding.reshape(1, -1)
            
            # FAISS로 유사한 문서 검색
            distances, indices = self.index.search(query_embedding, self.top_k)
            
            # 검색 결과 구성
            results = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.documents):  # 유효한 인덱스인지 확인
                    result = {
                        'rank': i + 1,
                        'document': self.documents[idx],
                        'metadata': self.metadata[idx] if idx < len(self.metadata) else {},
                        'similarity_score': float(1 / (1 + distance)),  # 거리를 유사도로 변환
                        'distance': float(distance)
                    }
                    results.append(result)
            
            logger.info(f"검색 완료: {len(results)}개 문서 검색됨")
            return results
            
        except Exception as e:
            logger.error(f"문서 검색 실패: {str(e)}")
            raise
    
    def generate_answer(self, query: str, retrieved_docs: List[Dict[str, Any]]) -> str:
        """
        검색된 문서를 바탕으로 답변 생성
        
        Args:
            query: 사용자 질의
            retrieved_docs: 검색된 문서들
            
        Returns:
            생성된 답변
        """
        try:
            # 검색된 문서들을 컨텍스트로 구성
            context = ""
            for i, doc in enumerate(retrieved_docs):
                policy_name = doc['metadata'].get('정책명', f'정책 {i+1}')
                context += f"[정책 {i+1}: {policy_name}]\n"
                context += f"{doc['document']}\n\n"
            
            # 프롬프트 구성
            prompt = f"""
당신은 청년정책 전문 상담사입니다. 아래 제공된 청년정책 정보를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공해주세요.

**사용자 질문:**
{query}

**관련 청년정책 정보:**
{context}

**답변 지침:**
1. 제공된 정책 정보만을 바탕으로 답변하세요
2. 정책명, 지원내용, 신청방법, 지원대상 등을 명확히 제시하세요
3. 여러 정책이 관련있다면 모두 소개해주세요
4. 정확하지 않은 정보는 제공하지 마세요
5. 친근하고 도움이 되는 톤으로 답변하세요

**답변:**
"""
            
            # GPT-4o로 답변 생성
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "당신은 청년정책 전문 상담사입니다. 제공된 정책 정보를 바탕으로 정확하고 도움이 되는 답변을 제공합니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            answer = response.choices[0].message.content
            logger.info("답변 생성 완료")
            return answer
            
        except Exception as e:
            logger.error(f"답변 생성 실패: {str(e)}")
            raise
    
    def ask(self, query: str) -> Dict[str, Any]:
        """
        질의에 대한 전체 RAG 파이프라인 실행
        
        Args:
            query: 사용자 질의
            
        Returns:
            검색된 문서들과 생성된 답변을 포함한 결과
        """
        try:
            logger.info(f"질의 처리 시작: {query}")
            
            # 1. 문서 검색
            retrieved_docs = self.search_similar_documents(query)
            
            # 2. 답변 생성
            answer = self.generate_answer(query, retrieved_docs)
            
            # 3. 결과 구성
            result = {
                'query': query,
                'answer': answer,
                'retrieved_documents': retrieved_docs,
                'num_retrieved': len(retrieved_docs)
            }
            
            logger.info("질의 처리 완료")
            return result
            
        except Exception as e:
            logger.error(f"질의 처리 실패: {str(e)}")
            raise

def process_csv_queries(csv_path: str = "../data/query_testset.csv", 
                        output_path: str = None) -> None:
    """
    CSV 파일의 쿼리들을 처리하고 결과를 저장
    
    Args:
        csv_path: 입력 CSV 파일 경로
        output_path: 출력 CSV 파일 경로 (None이면 원본 파일을 덮어쓰기)
    """
    try:
        # RAG 시스템 초기화
        logger.info("RAG 시스템 초기화 중...")
        rag = NaiveRAG()
        
        # CSV 파일 읽기
        logger.info(f"CSV 파일 읽기: {csv_path}")
        df = pd.read_csv(csv_path)
        
        # 컬럼명 정리 (공백 제거)
        df.columns = df.columns.str.strip()
        
        # naive_rag_answer 컬럼이 없으면 생성
        if 'naive_rag_answer' not in df.columns:
            df['naive_rag_answer'] = ''
        
        logger.info(f"총 {len(df)}개의 쿼리 처리 시작")
        
        # 각 쿼리 처리
        for idx in df.index:
            query = df.loc[idx, 'query'].strip()
            
            # 이미 답변이 있으면 건너뛰기 (빈 문자열이 아닌 경우)
            if pd.notna(df.loc[idx, 'naive_rag_answer']) and df.loc[idx, 'naive_rag_answer'].strip():
                logger.info(f"[{idx+1}/{len(df)}] 이미 답변 존재, 건너뛰기: {query[:50]}...")
                continue
            
            logger.info(f"[{idx+1}/{len(df)}] 처리 중: {query[:50]}...")
            
            try:
                # RAG 시스템으로 답변 생성
                result = rag.ask(query)
                answer = result['answer']
                
                # DataFrame에 답변 저장
                df.loc[idx, 'naive_rag_answer'] = answer
                
                logger.info(f"[{idx+1}/{len(df)}] 답변 생성 완료")
                
                # 중간 저장 (5개마다)
                if (idx + 1) % 5 == 0:
                    output_file = output_path if output_path else csv_path
                    df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    logger.info(f"중간 저장 완료: {idx+1}개 처리됨")
                
            except Exception as e:
                logger.error(f"[{idx+1}/{len(df)}] 쿼리 처리 실패: {str(e)}")
                df.loc[idx, 'naive_rag_answer'] = f"오류 발생: {str(e)}"
        
        # 최종 저장
        output_file = output_path if output_path else csv_path
        df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"모든 쿼리 처리 완료. 결과 저장: {output_file}")
        
        # 결과 요약
        completed = df['naive_rag_answer'].notna().sum()
        logger.info(f"처리 완료: {completed}/{len(df)}개 쿼리")
        
    except Exception as e:
        logger.error(f"CSV 처리 실패: {str(e)}")
        raise

def main():
    """테스트용 메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Naive RAG 시스템')
    parser.add_argument('--mode', choices=['test', 'csv'], default='csv',
                       help='실행 모드: test (테스트 쿼리), csv (CSV 파일 처리)')
    parser.add_argument('--csv_path', default='../data/query_testset.csv',
                       help='입력 CSV 파일 경로')
    parser.add_argument('--output_path', default=None,
                       help='출력 CSV 파일 경로 (기본값: 입력 파일 덮어쓰기)')
    
    args = parser.parse_args()
    
    try:
        if args.mode == 'csv':
            # CSV 파일 처리 모드
            process_csv_queries(args.csv_path, args.output_path)
        else:
            # 테스트 모드
            # RAG 시스템 초기화
            rag = NaiveRAG()
            
            # 테스트 질의들
            test_queries = [
                "청년 주거 지원 정책에는 어떤 것들이 있나요?",
                "취업 준비생을 위한 지원 정책을 알려주세요",
                "서울에서 받을 수 있는 청년 정책은 무엇인가요?"
            ]
            
            for query in test_queries:
                print(f"\n{'='*50}")
                print(f"질의: {query}")
                print(f"{'='*50}")
                
                result = rag.ask(query)
                
                print(f"\n[답변]")
                print(result['answer'])
                
                print(f"\n[검색된 문서 수]: {result['num_retrieved']}")
                for i, doc in enumerate(result['retrieved_documents'][:3]):  # 상위 3개만 표시
                    policy_name = doc['metadata'].get('정책명', f'정책 {i+1}')
                    print(f"  {i+1}. {policy_name} (유사도: {doc['similarity_score']:.3f})")
            
    except Exception as e:
        logger.error(f"메인 실행 실패: {str(e)}")

if __name__ == "__main__":
    main()