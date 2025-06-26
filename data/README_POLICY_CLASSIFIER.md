# 🤖 청년정책 자동 분류 시스템

**RandomForest + TF-IDF 기반 정책 대분류 자동 분류 도구**

청년정책을 **기타**, **일자리**, **주거** 3개 대분류로 자동 분류하는 머신러닝 시스템입니다.

## 📋 **주요 특징**

✅ **높은 정확도**: 94.8% 분류 정확도 달성  
✅ **유연한 입력**: 단일 텍스트, 텍스트 리스트, CSV 파일 지원  
✅ **확률 정보**: 각 클래스별 예측 확률 제공  
✅ **모델 저장/로드**: 훈련된 모델 재사용 가능  
✅ **배치 처리**: 대용량 데이터 일괄 처리  
✅ **명령줄 인터페이스**: 스크립트 및 CLI 지원  

## 🔧 **설치 및 요구사항**

### 필수 패키지
```bash
pip install pandas numpy scikit-learn
```

### 데이터 요구사항
훈련 데이터는 다음 컬럼을 포함해야 합니다:
- `정책설명내용` (또는 `plcyExplnCn`)
- `정책지원내용` (또는 `plcySprtCn`)  
- `정책키워드명` (또는 `plcyKywdNm`)
- `정책대분류명` (또는 `lclsfNm`) - 타겟 컬럼

## 🚀 **사용법**

### 1. **명령줄 인터페이스 (CLI)**

#### **모델 훈련**
```bash
python policy_classifier.py train \
    --data 청년정책목록_전체.csv \
    --model policy_classifier_model.pkl \
    --validate 청년정책목록_전처리완료_2025-06-09.csv
```

#### **파일 배치 예측**
```bash
python policy_classifier.py predict \
    --model policy_classifier_model.pkl \
    --input 새로운_정책데이터.csv \
    --output 예측_결과.csv \
    --probabilities
```

#### **단일 텍스트 예측**
```bash
python policy_classifier.py single \
    --model policy_classifier_model.pkl \
    --text "청년 취업 지원 프로그램으로 면접 기술과 이력서 작성을 도와드립니다"
```

#### **모델 성능 검증**
```bash
python policy_classifier.py validate \
    --model policy_classifier_model.pkl \
    --data 검증_데이터.csv
```

### 2. **Python 코드에서 사용**

#### **기본 사용법**
```python
from policy_classifier import PolicyClassifier

# 모델 로드
classifier = PolicyClassifier("policy_classifier_model.pkl")

# 단일 텍스트 예측
text = "청년 창업 지원금 및 사업 아이디어 개발 프로그램"
result = classifier.predict(text, return_probabilities=True)[0]

print(f"예측 분류: {result['predicted_class']}")
print(f"신뢰도: {result['confidence']:.4f}")
```

#### **DataFrame 예측**
```python
import pandas as pd

# 데이터 준비
df = pd.read_csv("정책_데이터.csv")

# 예측 수행
predictions = classifier.predict(df)
df['예측_대분류명'] = predictions

# 결과 저장
df.to_csv("예측_결과.csv", index=False)
```

#### **여러 텍스트 동시 예측**
```python
texts = [
    "청년 창업 지원금 프로그램",
    "저소득 청년 임대주택 지원",
    "청년 문화 활동 지원사업"
]

results = classifier.predict(texts, return_probabilities=True)
for text, result in zip(texts, results):
    print(f"{text} → {result['predicted_class']}")
```

## 📊 **성능 지표**

현재 모델의 성능 (검증 데이터 기준):

| 지표 | 값 |
|------|-----|
| **정확도 (Accuracy)** | 94.8% |
| **정밀도 (Precision)** | 97.0% |
| **재현율 (Recall)** | 95.9% |
| **F1-Score** | 96.4% |

### 클래스별 성능
| 클래스 | 정밀도 | 재현율 | F1-Score | 지원 수 |
|--------|--------|--------|----------|---------|
| **기타** | 99% | 87% | 93% | 124 |
| **일자리** | 91% | 99% | 95% | 173 |
| **주거** | 100% | 100% | 100% | 30 |

## 🔍 **모델 상세 정보**

### **알고리즘**
- **분류기**: Random Forest Classifier
- **특성 추출**: TF-IDF Vectorizer (최대 3,000개 특성)
- **텍스트 전처리**: 정책설명 + 지원내용 + 키워드 결합

### **하이퍼파라미터**
```python
RandomForestClassifier(
    random_state=42,
    n_estimators=100,    # 기본값
    max_depth=None       # 기본값
)

TfidfVectorizer(
    max_features=3000,
    ngram_range=(1, 1)   # 기본값
)
```

## 📁 **파일 구조**

```
data/
├── policy_classifier.py              # 메인 분류기 클래스
├── policy_classifier_example.py      # 사용 예제
├── README_POLICY_CLASSIFIER.md       # 이 문서
├── randomforest.ipynb               # 원본 개발 노트북
└── policy_classifier_model.pkl      # 훈련된 모델 (생성 후)
```

## 🔄 **데이터 플로우**

```mermaid
graph LR
    A[정책 텍스트] --> B[텍스트 결합]
    B --> C[TF-IDF 벡터화]
    C --> D[RandomForest 분류]
    D --> E[예측 결과]
    E --> F[확률 정보]
```

## 📝 **예제 시나리오**

### **시나리오 1: 새로운 정책 자동 분류**
```python
# 새로 등록된 정책의 분류 자동화
new_policy = {
    '정책명': '청년 디지털 역량 강화 프로그램',
    '정책설명내용': '청년들의 디지털 기술 향상을 위한 교육과 취업 연계',
    '정책지원내용': '프로그래밍 교육, 자격증 취득 지원, 취업 알선',
    '정책키워드명': '디지털, 교육, 취업, 프로그래밍'
}

df = pd.DataFrame([new_policy])
prediction = classifier.predict(df)[0]
# 결과: "일자리"
```

### **시나리오 2: 대용량 정책 데이터 일괄 분류**
```python
# 1,000개 정책 데이터 일괄 처리
classifier.predict_file(
    input_file_path="정책목록_1000개.csv",
    output_file_path="분류결과_1000개.csv",
    include_probabilities=True
)
```

### **시나리오 3: 분류 성능 모니터링**
```python
# 새로운 검증 데이터로 성능 확인
metrics = classifier.validate("새로운_검증데이터.csv")
if metrics['accuracy'] < 0.9:
    print("⚠️  모델 재훈련이 필요합니다!")
```

## 🚨 **주의사항**

### **데이터 품질**
- 텍스트 데이터가 비어있거나 너무 짧으면 분류 성능이 저하될 수 있습니다
- 훈련 데이터와 유사한 도메인의 정책에서 최고 성능을 발휘합니다

### **모델 한계**
- 현재 3개 클래스(기타, 일자리, 주거)만 지원합니다
- 새로운 정책 영역이 추가되면 모델 재훈련이 필요합니다

### **성능 최적화**
- 대용량 데이터 처리 시 메모리 사용량에 주의하세요
- GPU 가속은 지원하지 않습니다 (scikit-learn 기반)

## 🛠️ **확장 가능성**

### **향후 개선 계획**
1. **다중 레이블 분류**: 정책이 여러 카테고리에 속할 수 있도록
2. **세부 분류**: 대분류 → 중분류 → 소분류 계층적 분류
3. **딥러닝 모델**: BERT 기반 Transformer 모델 도입
4. **실시간 API**: Flask/FastAPI 기반 웹 서비스
5. **자동 재훈련**: 새로운 데이터로 정기적 모델 업데이트

### **커스터마이징**
```python
# 하이퍼파라미터 조정
classifier = PolicyClassifier()
classifier.model = RandomForestClassifier(
    n_estimators=200,      # 트리 수 증가
    max_depth=10,          # 최대 깊이 제한
    min_samples_split=5    # 분할 최소 샘플 수
)
classifier.vectorizer = TfidfVectorizer(
    max_features=5000,     # 특성 수 증가
    ngram_range=(1, 2)     # 바이그램 포함
)
```

## 📞 **문의 및 지원**

- **이슈 리포트**: GitHub Issues 활용
- **기능 요청**: Pull Request 환영
- **기술 문의**: 개발팀 연락

---

**📅 최종 업데이트**: 2025-01-28  
**🔄 버전**: v1.0.0  
**👥 개발팀**: SKN10-FINAL-5Team 