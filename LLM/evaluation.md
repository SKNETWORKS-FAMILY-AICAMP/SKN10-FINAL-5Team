# 청년정책 RAG 시스템 핵심 성능 평가 기획서

## 1. 평가 개요

### 1.1 평가 목표
- 시스템의 핵심 기능 4개 영역에 대한 정량적 성능 측정
- 빠른 피드백을 통한 시스템 개선점 도출

### 1.2 평가 범위
1. **질의 분류 정확도**: 사용자 질문의 카테고리 분류 성능
2. **조건 추출 정확도**: 사용자 개인정보 및 조건 추출 성능  
3. **검색 정확도**: 관련 정책 검색 및 순위 성능
4. **응답 시간**: 전체 처리 시간 성능

## 2. 평가 항목별 상세 계획

### 2.1 질의 분류 정확도 평가

#### 평가 지표
```python
주요 지표:
- 전체 분류 정확도 (Overall Accuracy)
- 카테고리별 정밀도 (Precision per Category)
- 카테고리별 재현율 (Recall per Category)  
- F1-Score (Macro & Weighted)

분류 카테고리:
- '주거': 주거 관련 정책 질문
- '일자리': 취업/창업 관련 정책 질문
- '일반': 정책 일반 문의
- '그 외 정책': 기타 정책 질문
- '기타': 정책 외 질문 (거부 대상)
```

#### 평가 방법
```python
def evaluate_classification_accuracy():
    """질의 분류 정확도 평가"""
    test_cases = [
        {"query": "25세 대학생을 위한 전세자금대출이 있나요?", "expected": "주거"},
        {"query": "청년 창업지원 사업에 대해 알려주세요", "expected": "일자리"},
        {"query": "청년정책에는 어떤 것들이 있나요?", "expected": "일반"},
        {"query": "오늘 날씨는 어때요?", "expected": "기타"}
    ]
    
    # 분류 결과 수집 및 정확도 계산
    predictions = []
    actuals = []
    
    for case in test_cases:
        result = system.analyze_query(case["query"])
        predictions.append(result.lclsf_nm)
        actuals.append(case["expected"])
    
    # 성능 지표 계산
    accuracy = accuracy_score(actuals, predictions)
    precision = precision_score(actuals, predictions, average='weighted')
    recall = recall_score(actuals, predictions, average='weighted')
    f1 = f1_score(actuals, predictions, average='weighted')
    
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    }
```

### 2.2 조건 추출 정확도 평가

#### 평가 지표
```python
추출 대상 조건:
- age: 나이 (정수)
- mrg_stts_cd: 결혼상태 ('기혼', '미혼')
- plcy_major_cd: 전공계열 (8개 계열)
- job_cd: 취업상태 (6개 상태)
- school_cd: 학력 (8개 수준)
- zip_cd: 거주지 (지역명)
- earn_etc_cn: 소득조건 (문자열)
- additional_requirement: 추가요건 (문자열)

평가 지표:
- 필드별 추출 정확도 (Field-wise Accuracy)
- 완전 일치율 (Exact Match Rate)
- 부분 일치율 (Partial Match Rate)
- 누락률 (Missing Rate)
```

#### 평가 방법
```python
def evaluate_extraction_accuracy():
    """조건 추출 정확도 평가"""
    test_cases = [
        {
            "query": "28세 미혼 컴퓨터공학과 대학원생이고 서울에 살고 있습니다. 월 소득은 150만원 정도입니다.",
            "expected": {
                "age": 28,
                "mrg_stts_cd": "미혼", 
                "plcy_major_cd": "공학계열",
                "school_cd": "석·박사",
                "zip_cd": "서울특별시",
                "earn_etc_cn": "월소득 150만원"
            }
        }
    ]
    
    field_accuracies = {}
    exact_matches = 0
    total_cases = len(test_cases)
    
    for case in test_cases:
        result = system.analyze_query(case["query"])
        expected = case["expected"]
        
        # 필드별 정확도 계산
        for field, expected_value in expected.items():
            if field not in field_accuracies:
                field_accuracies[field] = {"correct": 0, "total": 0}
            
            extracted_value = getattr(result.query_analysis, field)
            field_accuracies[field]["total"] += 1
            
            if extracted_value == expected_value:
                field_accuracies[field]["correct"] += 1
        
        # 완전 일치 확인
        if all(getattr(result.query_analysis, field) == expected_value 
               for field, expected_value in expected.items()):
            exact_matches += 1
    
    # 결과 계산
    field_scores = {
        field: data["correct"] / data["total"] 
        for field, data in field_accuracies.items()
    }
    
    return {
        "field_accuracies": field_scores,
        "exact_match_rate": exact_matches / total_cases,
        "average_field_accuracy": sum(field_scores.values()) / len(field_scores)
    }
```

### 2.3 검색 정확도 평가

#### 평가 지표
```python
검색 성능 지표:
- Precision@K (K=5, 10): 상위 K개 결과 중 관련 정책 비율
- Recall@K (K=5, 10): 전체 관련 정책 중 상위 K개에 포함된 비율
- NDCG@K (K=5, 10): 순위를 고려한 검색 품질
- MRR (Mean Reciprocal Rank): 첫 번째 관련 결과의 평균 역순위
```

#### 평가 방법
```python
def evaluate_search_performance():
    """검색 정확도 평가"""
    test_cases = [
        {
            "query": "25세 미혼 대학생 서울 거주 전세자금대출",
            "relevant_policies": ["plcy_no01", "plcy_no02", "plcy_no03"],  # 전문가 라벨링
            "highly_relevant": ["plcy_no01"]  # 높은 관련성
        }
    ]
    
    precision_at_5 = []
    precision_at_10 = []
    recall_at_5 = []
    recall_at_10 = []
    ndcg_at_5 = []
    ndcg_at_10 = []
    
    for case in test_cases:
        # 시스템에서 검색 결과 가져오기
        search_results = system.search_policies(case["query"])
        retrieved_ids = [policy["plcy_no"] for policy in search_results]
        
        relevant_set = set(case["relevant_policies"])
        
        # Precision@K 계산
        precision_at_5.append(
            len(set(retrieved_ids[:5]) & relevant_set) / min(5, len(retrieved_ids))
        )
        precision_at_10.append(
            len(set(retrieved_ids[:10]) & relevant_set) / min(10, len(retrieved_ids))
        )
        
        # Recall@K 계산  
        recall_at_5.append(
            len(set(retrieved_ids[:5]) & relevant_set) / len(relevant_set)
        )
        recall_at_10.append(
            len(set(retrieved_ids[:10]) & relevant_set) / len(relevant_set)
        )
        
        # NDCG@K 계산
        ndcg_at_5.append(calculate_ndcg(retrieved_ids[:5], case, 5))
        ndcg_at_10.append(calculate_ndcg(retrieved_ids[:10], case, 10))
    
    return {
        "precision_at_5": sum(precision_at_5) / len(precision_at_5),
        "precision_at_10": sum(precision_at_10) / len(precision_at_10),
        "recall_at_5": sum(recall_at_5) / len(recall_at_5),
        "recall_at_10": sum(recall_at_10) / len(recall_at_10),
        "ndcg_at_5": sum(ndcg_at_5) / len(ndcg_at_5),
        "ndcg_at_10": sum(ndcg_at_10) / len(ndcg_at_10)
    }
```

### 2.4 응답 시간 평가

#### 평가 지표
```python
시간 성능 지표:
- 전체 응답 시간 (End-to-End Response Time)
- 단계별 처리 시간:
  * 질의 분석 시간
  * SQL 쿼리 생성 시간  
  * 데이터베이스 검색 시간
  * 응답 생성 시간
- 응답 시간 분포 (P50, P95, P99)
- 동시 처리 성능 (Concurrent Request Handling)
```

#### 평가 방법
```python
import time
import threading
from concurrent.futures import ThreadPoolExecutor

def evaluate_response_time():
    """응답 시간 성능 평가"""
    test_queries = [
        "25세 미혼 대학생을 위한 주거 지원 정책을 알려주세요",
        "청년 창업지원 프로그램에 대해 문의드립니다",
        "서울 거주 취업준비생을 위한 일자리 정책이 있나요?"
    ]
    
    # 단일 요청 응답 시간 측정
    single_request_times = []
    stage_times = {}
    
    for query in test_queries:
        start_time = time.time()
        
        # 단계별 시간 측정
        stage_start = time.time()
        analysis_result = system.analyze_query_node({"messages": [{"content": query}]})
        stage_times.setdefault("analysis", []).append(time.time() - stage_start)
        
        stage_start = time.time()
        sql_result = system.generate_sql_query_node(analysis_result)
        stage_times.setdefault("sql_generation", []).append(time.time() - stage_start)
        
        stage_start = time.time()
        response_result = system.generate_response_node(sql_result)
        stage_times.setdefault("response_generation", []).append(time.time() - stage_start)
        
        total_time = time.time() - start_time
        single_request_times.append(total_time)
    
    # 동시 요청 처리 성능 측정
    concurrent_times = []
    
    def process_request(query):
        start_time = time.time()
        system.process_query(query)
        return time.time() - start_time
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_request, query) 
                  for query in test_queries * 10]  # 각 쿼리를 10번씩 동시 실행
        concurrent_times = [future.result() for future in futures]
    
    # 통계 계산
    import numpy as np
    
    return {
        "average_response_time": np.mean(single_request_times),
        "p50_response_time": np.percentile(single_request_times, 50),
        "p95_response_time": np.percentile(single_request_times, 95),
        "p99_response_time": np.percentile(single_request_times, 99),
        "stage_times": {
            stage: {
                "average": np.mean(times),
                "max": np.max(times)
            } for stage, times in stage_times.items()
        },
        "concurrent_performance": {
            "average": np.mean(concurrent_times),
            "p95": np.percentile(concurrent_times, 95),
            "throughput": len(concurrent_times) / max(concurrent_times)  # requests/second
        }
    }
```

## 3. 테스트 데이터셋

### 3.1 데이터 구성
```python
테스트 데이터 규모:
- 질의 분류 테스트: 20개
  * 주거: 5개
  * 일자리: 5개  
  * 일반: 5개
  * 그 외 정책: 3개
  * 기타: 2개

- 조건 추출 테스트: 20개
  * 단일 조건: 10개
  * 복합 조건: 10개

- 검색 성능 테스트: 30개
  * 명확한 조건: 15개
  * 모호한 조건: 15개

- 응답 시간 테스트: 10개
  * 다양한 복잡도의 쿼리
```

## 4. 통합 평가 프레임워크

```python
// filepath: c:\dev\SKN10-FINAL-5Team\LLM\core_evaluator.py
class CoreRAGEvaluator:
    def __init__(self, rag_system):
        self.system = rag_system
        self.test_data = self.load_test_data()
    
    def run_full_evaluation(self):
        """4개 핵심 평가 모두 실행"""
        results = {}
        
        print("1. 질의 분류 정확도 평가 중...")
        results["classification"] = self.evaluate_classification_accuracy()
        
        print("2. 조건 추출 정확도 평가 중...")
        results["extraction"] = self.evaluate_extraction_accuracy()
        
        print("3. 검색 정확도 평가 중...")
        results["search"] = self.evaluate_search_performance()
        
        print("4. 응답 시간 평가 중...")
        results["response_time"] = self.evaluate_response_time()
        
        return self.generate_summary_report(results)
    
    def generate_summary_report(self, results):
        """평가 결과 요약 보고서 생성"""
        report = f"""
        # 청년정책 RAG 시스템 핵심 성능 평가 결과
        
        ## 1. 질의 분류 정확도
        - 전체 정확도: {results['classification']['accuracy']:.3f}
        - F1-Score: {results['classification']['f1_score']:.3f}
        
        ## 2. 조건 추출 정확도  
        - 완전 일치율: {results['extraction']['exact_match_rate']:.3f}
        - 평균 필드 정확도: {results['extraction']['average_field_accuracy']:.3f}
        
        ## 3. 검색 정확도
        - Precision@10: {results['search']['precision_at_10']:.3f}
        - NDCG@10: {results['search']['ndcg_at_10']:.3f}
        
        ## 4. 응답 시간
        - 평균 응답시간: {results['response_time']['average_response_time']:.2f}초
        - P95 응답시간: {results['response_time']['p95_response_time']:.2f}초
        """
        
        return report
```

## 5. 성공 기준

```python
최소 성능 기준:
- 질의 분류 정확도: 90% 이상
- 조건 추출 정확도 (완전일치): 80% 이상  
- 검색 정확도 (P@10): 75% 이상
- 평균 응답 시간: 8초 이내
- P95 응답 시간: 15초 이내
```

## 6. 실행 계획

### 6.1 평가 일정
- **1일차**: 테스트 데이터 준비 및 평가 환경 구축
- **2일차**: 평가 스크립트 구현 및 테스트
- **3일차**: 전체 평가 실행 및 결과 분석
- **4일차**: 개선 방안 도출 및 재평가

### 6.2 실행 명령어
```bash
# 전체 평가 실행
python core_evaluator.py --full-evaluation

# 개별 평가 실행
python core_evaluator.py --classification-only
python core_evaluator.py --extraction-only  
python core_evaluator.py --search-only
python core_evaluator.py --timing-only
```

이 간소화된 평가 계획으로 핵심 성능 지표에 집중하여 빠르고 효과적인 시스템 평가를 수행할 수 있습니다.