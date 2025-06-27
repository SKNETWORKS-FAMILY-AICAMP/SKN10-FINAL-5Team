"""
전체 평가 프로세스를 관리하는 메인 클래스
"""
import os
import pandas as pd
from typing import List, Dict, Any

from config.evaluation_config import evaluation_config
from evaluation.model_runner import ModelRunner
from evaluation.quality_evaluator import QualityEvaluator
from evaluation.results_collector import ResultsCollector
from utils.logging import setup_logging

logger = setup_logging()


class EvaluationManager:
    """전체 평가 프로세스를 관리하는 클래스"""
    
    def __init__(self):
        self.model_runner = ModelRunner()
        self.quality_evaluator = QualityEvaluator()
        self.results_collector = ResultsCollector()
        self.testset_path = evaluation_config.testset_path
    
    def load_testset(self) -> List[str]:
        """테스트셋 CSV 파일 로드"""
        try:
            if not os.path.exists(self.testset_path):
                # 상대 경로로 다시 시도
                alternative_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'testset.csv')
                if os.path.exists(alternative_path):
                    self.testset_path = alternative_path
                else:
                    raise FileNotFoundError(f"테스트셋 파일을 찾을 수 없습니다: {self.testset_path}")
            
            df = pd.read_csv(self.testset_path)
            
            # 'query' 컬럼에서 질문 추출
            if 'query' in df.columns:
                queries = df['query'].dropna().tolist()
            else:
                # 첫 번째 컬럼을 질문으로 간주
                queries = df.iloc[:, 0].dropna().tolist()
            
            # 빈 문자열이나 공백만 있는 질문 제거
            queries = [q.strip() for q in queries if q.strip()]
            
            logger.info(f"테스트셋 로드 완료: {len(queries)}개 질문")
            
            return queries
            
        except Exception as e:
            logger.error(f"테스트셋 로드 실패: {e}")
            # 기본 테스트 질문들 반환
            return [
                "25세 대학생을 위한 전세자금대출이 있나요?",
                "청년 전월세 보증금 지원 정책 알려줘",
                "청년 창업지원 사업에 대해 알려주세요"
            ]
    
    def run_single_query_evaluation(self, query_id: int, query: str) -> Dict[str, Any]:
        """단일 질문에 대한 전체 평가 프로세스 실행"""
        logger.info(f"Query {query_id} 평가 시작: {query[:50]}...")
        
        # 1. 모든 모델로 질문 실행
        model_results = self.model_runner.run_all_models(query)
        
        # 2. 각 모델의 응답에 대해 품질 평가
        responses_for_evaluation = {
            model: result[0]  # (응답, 시간, 정보) 중 응답만 추출
            for model, result in model_results.items()
        }
        
        evaluation_results = self.quality_evaluator.evaluate_multiple_responses(
            query, responses_for_evaluation
        )
        
        # 3. 결과 수집
        self.results_collector.add_result(
            query_id, query, model_results, evaluation_results
        )
        
        logger.info(f"Query {query_id} 평가 완료")
        
        return {
            'query_id': query_id,
            'query': query,
            'model_results': model_results,
            'evaluation_results': evaluation_results
        }
    
    def run_full_evaluation(self) -> Dict[str, str]:
        """전체 평가 프로세스 실행"""
        logger.info("=== 청년정책 RAG 시스템 전체 평가 시작 ===")
        
        try:
            # 1. 테스트셋 로드
            queries = self.load_testset()
            logger.info(f"총 {len(queries)}개 질문으로 평가 진행")
            
            # 2. 각 질문별 평가 실행
            for i, query in enumerate(queries, 1):
                try:
                    self.run_single_query_evaluation(i, query)
                except Exception as e:
                    logger.error(f"Query {i} 평가 실패: {e}")
                    continue
            
            # 3. 결과 저장
            logger.info("평가 결과 저장 중...")
            
            csv_path = self.results_collector.save_detailed_results()
            json_path = self.results_collector.save_summary_report()
            md_path = self.results_collector.save_markdown_summary()
            
            logger.info("=== 전체 평가 완료 ===")
            
            return {
                'detailed_results': csv_path,
                'summary_report': json_path,
                'markdown_summary': md_path,
                'total_queries': len(queries)
            }
            
        except Exception as e:
            logger.error(f"전체 평가 실행 실패: {e}")
            raise
    
    def run_quick_test(self, test_query: str = None) -> Dict[str, Any]:
        """빠른 테스트 실행 (단일 질문)"""
        if test_query is None:
            test_query = "25세 대학생을 위한 전세자금대출이 있나요?"
        
        logger.info(f"빠른 테스트 실행: {test_query}")
        
        result = self.run_single_query_evaluation(1, test_query)
        
        # 간단한 결과 출력
        print(f"\n=== 테스트 결과 ===")
        print(f"질문: {test_query}")
        print()
        
        for model_name, (response, response_time, _) in result['model_results'].items():
            score, reason, _ = result['evaluation_results'].get(model_name, (0, "평가 안됨", {}))
            
            print(f"[{model_name}]")
            print(f"응답 시간: {response_time:.2f}초")
            print(f"품질 점수: {score}/5")
            print(f"응답: {response[:100]}...")
            print(f"평가 이유: {reason}")
            print("-" * 50)
        
        return result
