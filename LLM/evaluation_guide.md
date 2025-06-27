# 청년정책 RAG 시스템 평가 실행 가이드

## 개요

이 가이드는 청년정책 RAG 시스템의 성능을 다양한 LLM 모델로 평가하는 방법을 설명합니다.

## 환경 설정

### 1. 필요한 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. API 키 설정

`.env` 파일에 다음 API 키들이 설정되어 있는지 확인하세요:

```properties
OPENAI_API_KEY="your_openai_api_key"
GEMINI_API_KEY="your_gemini_api_key"
```

## 평가 실행 방법

### 1. 전체 평가 실행

```bash
cd LLM
python evaluation_runner.py
```

이 명령은 `testset.csv`의 모든 질문에 대해:
- GPT-4o, GPT-4-turbo, Gemini-1.5-flash 모델로 각각 답변 생성
- 응답 시간 측정
- GPT-4o를 활용한 5점 척도 품질 평가
- 결과를 CSV, JSON, Markdown 형태로 저장

### 2. 빠른 테스트

```bash
python evaluation_runner.py --test
```

기본 질문으로 빠른 테스트를 실행합니다.

### 3. 특정 질문으로 테스트

```bash
python evaluation_runner.py --query "25세 대학생을 위한 전세자금대출이 있나요?"
```

## 결과 파일

평가 완료 후 `evaluation_results/` 디렉토리에 다음 파일들이 생성됩니다:

### 1. 상세 결과 (CSV)
- 파일명: `evaluation_results_YYYYMMDD_HHMMSS.csv`
- 내용: 각 질문별, 모델별 상세 결과

```csv
query_id,query,model,response,response_time,quality_score,evaluation_reason
1,"25세 대학생을 위한 전세자금대출이 있나요?",gpt-4o,"...",2.34,4,"정확한 정책 정보 제공"
```

### 2. 요약 리포트 (JSON)
- 파일명: `model_comparison_report_YYYYMMDD_HHMMSS.json`
- 내용: 모델별 통계, 성능 비교

### 3. 마크다운 요약 (MD)
- 파일명: `evaluation_summary_YYYYMMDD_HHMMSS.md`
- 내용: 읽기 쉬운 형태의 평가 요약

## 평가 지표

### 1. 응답 시간 (Response Time)
- 단위: 초
- 각 질문에 대한 답변 생성 시간

### 2. 품질 점수 (Quality Score)
- 척도: 1-5점
- 평가 기준:
  - 5점: 매우 우수 - 질문에 완벽히 부합하는 정확하고 유용한 답변
  - 4점: 우수 - 질문에 잘 부합하며 대부분 정확한 답변
  - 3점: 보통 - 질문에 부분적으로 부합하는 답변
  - 2점: 미흡 - 질문과 관련성이 낮거나 부정확한 답변
  - 1점: 매우 미흡 - 질문과 무관하거나 잘못된 답변

## 평가 대상 모델

1. **GPT-4o** (OpenAI)
2. **GPT-4-turbo** (OpenAI)
3. **Gemini-1.5-flash** (Google)

## 테스트 데이터

- 파일: `data/testset.csv`
- 질문 수: 20개
- 질문 유형: 청년정책 관련 질문, 일반 질문 포함

## 문제 해결

### 1. 패키지 설치 오류

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. API 키 오류

- OpenAI API 키가 유효한지 확인
- Gemini API 키가 정확히 설정되었는지 확인

### 3. 메모리 부족

평가 중 메모리 부족이 발생하면:
- 브라우저 등 다른 프로그램 종료
- 테스트셋 크기를 줄여서 실행

### 4. 네트워크 연결 오류

- 인터넷 연결 상태 확인
- API 서비스 상태 확인

## 커스터마이징

### 1. 다른 모델 추가

`config/evaluation_config.py`에서 모델 추가:

```python
self.models['new-model'] = ChatOpenAI(
    api_key=self.openai_api_key,
    model="new-model-name",
    temperature=0
)
```

### 2. 평가 기준 수정

`evaluation/quality_evaluator.py`에서 평가 프롬프트 수정

### 3. 테스트 데이터 변경

`data/testset.csv` 파일을 수정하여 다른 질문들로 평가

## 주의사항

1. **API 비용**: 평가 실행 시 OpenAI 및 Google API 사용료가 발생합니다.
2. **실행 시간**: 전체 평가는 20-30분 정도 소요될 수 있습니다.
3. **네트워크**: 안정적인 인터넷 연결이 필요합니다.

## 지원

문제 발생 시 로그 파일(`debug.log`)을 확인하거나 개발팀에 문의하세요.
