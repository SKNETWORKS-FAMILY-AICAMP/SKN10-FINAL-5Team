"""
O3-mini 모델을 활용한 답변 품질 평가 모듈
"""
import re
from typing import Dict, Any, Tuple
from langchain_core.messages import HumanMessage, SystemMessage

from config.evaluation_config import evaluation_config
from utils.logging import setup_logging

logger = setup_logging()


class QualityEvaluator:
    """답변 품질을 평가하는 클래스"""
    
    def __init__(self):
        self.evaluation_model = evaluation_config.evaluation_model
        self.quality_scale = evaluation_config.quality_scale
    
    def _create_evaluation_prompt(self, query: str, response: str) -> str:
        """평가를 위한 프롬프트 생성"""
        prompt = f"""
다음은 청년정책 RAG 시스템에 대한 사용자 질문과 AI의 답변입니다.
답변이 질문에 얼마나 잘 부합하는지 5점 척도로 평가해주세요.

**평가 기준:**
- 5점: 매우 우수 - 질문에 완벽히 부합하는 정확하고 유용한 답변
- 4점: 우수 - 질문에 잘 부합하며 대부분 정확한 답변
- 3점: 보통 - 질문에 부분적으로 부합하는 답변  
- 2점: 미흡 - 질문과 관련성이 낮거나 부정확한 답변
- 1점: 매우 미흡 - 질문과 무관하거나 잘못된 답변

**사용자 질문:**
{query}

**AI 답변:**
{response}

**평가 요청:**
위 답변을 5점 척도로 평가하고, 다음 형식으로 답변해주세요:

점수: [1-5점 중 하나]
이유: [평가 이유를 2-3문장으로 설명]

평가할 때 다음 사항을 고려해주세요:
1. 질문의 의도를 정확히 파악했는가?
2. 제공된 정보가 정확하고 유용한가?
3. 답변이 명확하고 이해하기 쉬운가?
4. 청년정책과 관련 없는 질문에 대해 적절히 거부했는가?
"""
        return prompt
    
    def evaluate_response(self, query: str, response: str, model_name: str = None) -> Tuple[int, str, Dict[str, Any]]:
        """
        답변 품질을 평가
        
        Args:
            query: 원본 질문
            response: 평가할 답변  
            model_name: 답변을 생성한 모델명 (옵션)
        
        Returns:
            Tuple[점수(1-5), 평가이유, 추가정보]
        """
        try:
            # 평가 프롬프트 생성
            evaluation_prompt = self._create_evaluation_prompt(query, response)
            
            # 시스템 메시지와 사용자 메시지 구성
            messages = [
                SystemMessage(content="당신은 AI 답변의 품질을 평가하는 전문가입니다. 공정하고 객관적으로 평가해주세요."),
                HumanMessage(content=evaluation_prompt)
            ]
            
            # 평가 모델 실행
            evaluation_result = self.evaluation_model.invoke(messages)
            evaluation_text = evaluation_result.content
            
            # 점수와 이유 추출
            score, reason = self._parse_evaluation_result(evaluation_text)
            
            # 추가 정보
            additional_info = {
                "evaluated_model": model_name,
                "evaluation_model": "gpt-4o",  # 실제로는 O3-mini 사용 예정
                "raw_evaluation": evaluation_text,
                "success": True
            }
            
            logger.info(f"평가 완료 - 모델: {model_name}, 점수: {score}, 질문: {query[:30]}...")
            
            return score, reason, additional_info
            
        except Exception as e:
            logger.error(f"평가 실행 오류: {e}")
            
            return 0, f"평가 실패: {str(e)}", {
                "evaluated_model": model_name,
                "success": False,
                "error": str(e)
            }
    
    def _parse_evaluation_result(self, evaluation_text: str) -> Tuple[int, str]:
        """
        평가 결과 텍스트에서 점수와 이유를 추출
        
        Args:
            evaluation_text: 평가 모델의 응답 텍스트
        
        Returns:
            Tuple[점수, 이유]
        """
        try:
            # 점수 추출 (정규식 사용)
            score_match = re.search(r'점수:\s*([1-5])', evaluation_text)
            if score_match:
                score = int(score_match.group(1))
            else:
                # 대체 패턴 시도
                score_match = re.search(r'([1-5])점', evaluation_text)
                score = int(score_match.group(1)) if score_match else 3
            
            # 이유 추출
            reason_match = re.search(r'이유:\s*(.+?)(?:\n|$)', evaluation_text, re.DOTALL)
            if reason_match:
                reason = reason_match.group(1).strip()
            else:
                # 이유를 찾지 못한 경우 전체 텍스트 사용
                reason = evaluation_text.strip()
            
            # 점수 범위 검증
            if score < 1 or score > 5:
                score = 3  # 기본값
            
            return score, reason
            
        except Exception as e:
            logger.error(f"평가 결과 파싱 오류: {e}")
            return 3, f"파싱 실패: {evaluation_text[:100]}..."
    
    def evaluate_multiple_responses(self, query: str, responses: Dict[str, str]) -> Dict[str, Tuple[int, str, Dict[str, Any]]]:
        """
        여러 모델의 답변을 일괄 평가
        
        Args:
            query: 원본 질문
            responses: {모델명: 답변} 딕셔너리
        
        Returns:
            Dict[모델명, (점수, 이유, 추가정보)]
        """
        evaluation_results = {}
        
        for model_name, response in responses.items():
            logger.info(f"{model_name} 답변 평가 중...")
            
            score, reason, additional_info = self.evaluate_response(
                query, response, model_name
            )
            
            evaluation_results[model_name] = (score, reason, additional_info)
        
        return evaluation_results
