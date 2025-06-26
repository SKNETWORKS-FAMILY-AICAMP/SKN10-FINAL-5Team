"""
RAG 시스템 설정 관리 모듈
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


class YouthPolicyRAGConfig:
    """RAG 시스템 설정 클래스"""
    
    def __init__(self):
        load_dotenv()
        self._load_database_config()
        self._load_openai_config()
        self._load_rag_config()
        self._initialize_llm_models()
    
    def _load_database_config(self):
        """데이터베이스 설정 로드"""
        self.db_config = {
            'host': os.getenv("DB_HOST", 'localhost'),
            'database': os.getenv("DB_NAME", 'youth_policy'),
            'user': os.getenv("DB_USER", 'postgres'),
            'password': os.getenv("DB_PASSWORD", 'your_password'),
            'port': os.getenv("DB_PORT", 5432)
        }
    
    def _load_openai_config(self):
        """OpenAI 설정 로드"""
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
    
    def _load_rag_config(self):
        """RAG 관련 설정 로드"""
        self.top_k = int(os.getenv('TOP_K', 10))
        self.confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', 0.5))
    
    def _initialize_llm_models(self):
        """LLM 모델 초기화"""
        self.chat_llm = ChatOpenAI(
            api_key=self.openai_api_key,
            temperature=0,
            verbose=True,
            model="gpt-4o",
        )
        
        self.thinking_model = ChatOpenAI(
            api_key=self.openai_api_key,
            model="gpt-4o",
        )
