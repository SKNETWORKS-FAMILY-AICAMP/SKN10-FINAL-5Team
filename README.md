# Multi-Model RAG System for Youth Policy

이 프로젝트는 다양한 LLM 모델을 사용하여 청년 정책에 대한 RAG(Retrieval-Augmented Generation) 시스템을 구현하고 비교합니다.

## 지원 모델
- ChatGPT 4.5
- ChatGPT o4-mini
- Claude 3.7 Sonnet
- Gemini 1.5 Pro
- Claude 3.5 Sonnet
- Claude 3 Opus
- ChatGPT 4o
- ChatGPT o3-mini
- Gemini 2.0
- clova x

## 환경 설정

1. 필요한 API 키 설정
   - `.env` 파일을 생성하고 다음 API 키들을 설정하세요:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   GOOGLE_API_KEY=your_google_api_key
   NAVER_CLIENT_ID=your_naver_client_id
   NAVER_CLIENT_SECRET=your_naver_client_secret
   ```

2. 가상환경 설정
   ```bash
   # Windows
   setup_env.bat
   
   # Linux/Mac
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## 실행 방법

1. 가상환경 활성화
   ```bash
   # Windows
   venv\Scripts\activate.bat
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. RAG 시스템 실행
   ```bash
   python LLM/multi_model_rag.py
   ```

## 결과

실행이 완료되면 `models_answer_collection_YYMMDD.csv` 파일이 생성됩니다. 이 파일에는 다음 정보가 포함됩니다:
- 모델 이름
- 모델의 답변
- 응답 시간 (초)

## 주의사항

1. 각 모델의 API 키가 올바르게 설정되어 있어야 합니다.
2. 인터넷 연결이 필요합니다.
3. 일부 모델은 API 호출 제한이 있을 수 있으니 주의하세요.
4. 벡터 DB 경로가 올바르게 설정되어 있어야 합니다.