"""
모델별 실행 및 성능 측정 모듈
"""
import time
import traceback
from typing import Dict, Any, Tuple
from langchain_core.messages import HumanMessage

from config.evaluation_config import evaluation_config
from graph.workflow import YouthPolicyRAGWorkflow
from utils.logging import setup_logging

logger = setup_logging()


class ModelRunner:
    """각 모델별 실행 및 시간 측정을 담당하는 클래스"""
    
    def __init__(self):
        self.workflows = {}
        self._initialize_workflows()
    
    def _initialize_workflows(self):
        """각 모델별로 워크플로우 인스턴스 생성"""
        for model_name in evaluation_config.get_model_names():
            try:
                # 기본 워크플로우 생성
                workflow = YouthPolicyRAGWorkflow()
                
                # 각 모델별로 별도의 워크플로우 인스턴스 저장
                # 실제 모델 교체는 노드 레벨에서 처리
                self.workflows[model_name] = workflow
                logger.info(f"{model_name} 워크플로우 초기화 완료")
                
            except Exception as e:
                logger.error(f"{model_name} 워크플로우 초기화 실패: {e}")
                self.workflows[model_name] = None
    
    def run_query(self, model_name: str, query: str, timestamp: str = None) -> Tuple[str, float, Dict[str, Any]]:
        """
        특정 모델로 쿼리 실행 및 시간 측정
        
        Args:
            model_name: 사용할 모델 이름
            query: 입력 질문
            timestamp: 타임스탬프 (옵션)
        
        Returns:
            Tuple[응답, 응답시간(초), 추가정보]
        """
        if model_name not in self.workflows or self.workflows[model_name] is None:
            return f"모델 {model_name} 사용 불가", 0.0, {"error": "모델 초기화 실패"}
        
        workflow = self.workflows[model_name]
        
        # 입력 데이터 구성
        input_data = {
            "messages": [HumanMessage(content=query)],
            "timestamp": timestamp or "2025-06-27"
        }
        
        # 시간 측정 시작
        start_time = time.time()
        
        try:
            # 워크플로우 실행
            result = workflow.invoke(input_data)
            
            # 시간 측정 종료
            end_time = time.time()
            response_time = end_time - start_time
            
            # 응답 추출
            response = result.get('final_response', '응답 생성 실패')
            
            # 추가 정보
            additional_info = {
                "selected_policies_count": len(result.get('selected_policies', [])),
                "model_used": model_name,
                "success": True
            }
            
            logger.info(f"{model_name} - Query: {query[:50]}... - Time: {response_time:.2f}s")
            
            return response, response_time, additional_info
            
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            
            error_msg = f"오류 발생: {str(e)}"
            additional_info = {
                "model_used": model_name,
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            
            logger.error(f"{model_name} 실행 오류: {e}")
            
            return error_msg, response_time, additional_info
    
    def run_all_models(self, query: str, timestamp: str = None) -> Dict[str, Tuple[str, float, Dict[str, Any]]]:
        """
        모든 모델로 동일한 쿼리 실행
        
        Args:
            query: 입력 질문
            timestamp: 타임스탬프 (옵션)
        
        Returns:
            Dict[모델명, (응답, 응답시간, 추가정보)]
        """
        results = {}
        
        for model_name in evaluation_config.get_model_names():
            logger.info(f"{model_name}로 쿼리 실행 중: {query[:50]}...")
            
            response, response_time, additional_info = self.run_query(
                model_name, query, timestamp
            )
            
            results[model_name] = (response, response_time, additional_info)
        
        return results
