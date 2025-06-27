"""
청년정책 RAG 시스템 평가용 설정 모듈
다양한 LLM 모델들을 지원하는 확장된 설정
"""
import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


class EvaluationConfig:
    """평가 시스템 설정 클래스"""
    
    def __init__(self):
        load_dotenv()
        self._load_api_keys()
        self._initialize_models()
        self._load_evaluation_config()
    
    def _load_api_keys(self):
        """API 키들 로드"""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.openai_api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
        if not self.gemini_api_key:
            raise ValueError("Gemini API 키가 설정되지 않았습니다.")
    
    def _initialize_models(self):
        """평가에 사용할 모든 LLM 모델들 초기화"""
        self.models = {
            'gpt-4o': ChatOpenAI(
                api_key=self.openai_api_key,
                model="gpt-4o",
                temperature=0,
                verbose=False
            ),
            'gpt-4o-mini': ChatOpenAI(
                api_key=self.openai_api_key,
                model="gpt-4o-mini",
                temperature=0,
                verbose=False
            ),
            'gpt-4.1': ChatOpenAI(
                api_key=self.openai_api_key,
                model="gpt-4.1",
                temperature=0,
                verbose=False
            ),
            'gemini-2.5-flash': ChatGoogleGenerativeAI(
                google_api_key=self.gemini_api_key,
                model="gemini-2.5-flash",
                temperature=0,
                verbose=False
            )
        }
        
        # 평가용 모델 (O1-mini 대신 GPT-4o 사용)
        self.evaluation_model = ChatOpenAI(
            api_key=self.openai_api_key,
            model="o3-mini",
            verbose=False
        )
    
    def _load_evaluation_config(self):
        """평가 관련 설정 로드"""
        self.testset_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'testset.csv')
        self.results_dir = os.path.join(os.path.dirname(__file__), '..', 'evaluation_results')
        
        # 결과 디렉토리 생성
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 평가 척도
        self.quality_scale = {
            5: "매우 우수 - 질문에 완벽히 부합하는 정확하고 유용한 답변",
            4: "우수 - 질문에 잘 부합하며 대부분 정확한 답변", 
            3: "보통 - 질문에 부분적으로 부합하는 답변",
            2: "미흡 - 질문과 관련성이 낮거나 부정확한 답변",
            1: "매우 미흡 - 질문과 무관하거나 잘못된 답변"
        }
    
    def get_model_names(self) -> List[str]:
        """사용 가능한 모델 이름 목록 반환"""
        return list(self.models.keys())
    
    def get_model(self, model_name: str):
        """특정 모델 인스턴스 반환"""
        if model_name not in self.models:
            raise ValueError(f"지원하지 않는 모델: {model_name}")
        return self.models[model_name]


# 전역 설정 인스턴스
evaluation_config = EvaluationConfig()
