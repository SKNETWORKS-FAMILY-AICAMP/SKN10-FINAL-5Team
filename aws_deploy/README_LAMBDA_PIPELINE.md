# 청년정책 데이터 파이프라인 - 4개 Lambda 함수 구조

## 개요
청년정책 데이터를 처리하는 완전 자동화된 파이프라인을 4개의 독립적인 Lambda 함수로 분할하여 구현했습니다. 각 함수는 단일 책임 원칙을 따르며, S3 이벤트 트리거를 통해 연결됩니다.

## 아키텍처

```
[Lambda1] → S3/raw/ → [Lambda2] → S3/preprocessed/ → [Lambda3] → S3/policy_reclassified/ → [Lambda4] → RDS
    ↓                     ↓                           ↓                            ↓
원시 데이터 수집        데이터 정제 및 전처리         ML 기반 정책 분류           최종 RDS 저장
```

## Lambda 함수별 상세 설명

### Lambda1: Raw Data Ingestion
- **목적**: 외부 소스에서 원시 데이터 수집 및 S3 저장
- **트리거**: CloudWatch Events (24시간마다 자동 실행)
- **입력**: 외부 API 또는 기존 파일
- **출력**: `s3://bucket/raw/year=2025/month=06/week=03/data_YYYYMMDD_HHMMSS.csv`
- **주요 기능**:
  - API 호출 또는 파일 기반 데이터 수집
  - 날짜별 파티션 구조로 S3 저장
  - 실패 시 샘플 데이터 생성

### Lambda2: Data Preprocessing  
- **목적**: 원시 데이터 정제 및 전처리
- **트리거**: S3 이벤트 (`raw/` 디렉터리에 파일 생성 시)
- **입력**: `s3://bucket/raw/.../data.csv`
- **출력**: `s3://bucket/preprocessed/year=2025/month=06/week=03/data_YYYYMMDD_HHMMSS.csv`
- **주요 기능**:
  - 중복 제거
  - 결측값 처리
  - 텍스트 정제 (HTML 태그, 특수문자 제거)
  - 데이터 타입 표준화
  - 데이터 검증

### Lambda3: ML Classification
- **목적**: ML 모델을 사용한 정책 대분류 자동 분류
- **트리거**: S3 이벤트 (`preprocessed/` 디렉터리에 파일 생성 시)
- **입력**: `s3://bucket/preprocessed/.../data.csv`
- **출력**: `s3://bucket/policy_reclassified/year=2025/month=06/week=03/data_YYYYMMDD_HHMMSS.csv`
- **주요 기능**:
  - S3에서 훈련된 ML 모델 로드
  - TF-IDF + RandomForest 기반 분류
  - 모델 없는 경우 룰 기반 분류 대체
  - 분류 신뢰도 계산

### Lambda4: RDS Storage
- **목적**: 분류된 데이터를 최종적으로 PostgreSQL RDS에 저장
- **트리거**: S3 이벤트 (`policy_reclassified/` 디렉터리에 파일 생성 시)
- **입력**: `s3://bucket/policy_reclassified/.../data.csv`
- **출력**: PostgreSQL RDS 테이블
- **주요 기능**:
  - 조건부 업데이트 (변경된 데이터만 처리)
  - 데이터 무결성 검증
  - 트랜잭션 기반 안전한 저장

## S3 디렉터리 구조

```
youth-policy-data-bucket/
├── raw/
│   └── year=2025/month=06/week=03/
│       └── data_20250128_120000.csv
├── preprocessed/
│   └── year=2025/month=06/week=03/
│       └── data_20250128_120500.csv
├── policy_reclassified/
│   └── year=2025/month=06/week=03/
│       └── data_20250128_121000.csv
└── models/
    └── policy_classifier.pkl
```

## 데이터베이스 테이블 구조

### youth_policies 테이블
```sql
CREATE TABLE youth_policies (
    plcy_id VARCHAR(100) PRIMARY KEY,
    plcy_nm VARCHAR(500) NOT NULL,
    plcy_expln_cn TEXT,
    plcy_sprt_cn TEXT,
    plcy_kywd_nm TEXT,
    lclsf_nm VARCHAR(100),
    last_updt_dt DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 환경 변수 설정

### 공통 환경 변수
- `S3_BUCKET_NAME`: S3 버킷명

### Lambda1 전용
- `DATA_SOURCE`: 데이터 소스 ('api' 또는 'file')
- `SOURCE_FILE_KEY`: 소스 파일 S3 키 (file 모드시)
- `YOUTH_POLICY_API_URL`: 청년정책 API URL (api 모드시)
- `API_KEY`: API 인증 키 (필요시)

### Lambda3 전용
- `MODEL_S3_KEY`: ML 모델 파일 S3 키 (기본값: 'models/policy_classifier.pkl')

### Lambda4 전용
- `DB_HOST`: PostgreSQL 호스트
- `DB_PORT`: PostgreSQL 포트
- `DB_NAME`: 데이터베이스명
- `DB_USER`: 데이터베이스 사용자
- `DB_PASSWORD`: 데이터베이스 패스워드
- `POLICIES_TABLE`: 정책 테이블명 (기본값: 'youth_policies')
- `CLASSIFICATIONS_TABLE`: 분류 테이블명 (기본값: 'policy_classifications')

## 배포 방법

### 1. CloudFormation 스택 생성
```bash
aws cloudformation create-stack \
  --stack-name youth-policy-pipeline \
  --template-body file://cloudformation.yaml \
  --parameters file://parameters.json \
  --capabilities CAPABILITY_IAM
```

### 2. Lambda 함수 코드 배포
각 Lambda 함수 디렉터리에서:

```bash
# Lambda1 배포
cd lambda_functions/lambda1_raw_data_ingest
zip -r lambda1.zip . -x "*.pyc" "__pycache__/*"
aws lambda update-function-code \
  --function-name youth-policy-lambda1-raw-data-ingest \
  --zip-file fileb://lambda1.zip

# Lambda2 배포
cd ../lambda2_data_preprocessing
zip -r lambda2.zip . -x "*.pyc" "__pycache__/*"
aws lambda update-function-code \
  --function-name youth-policy-lambda2-data-preprocessing \
  --zip-file fileb://lambda2.zip

# Lambda3 배포
cd ../lambda3_ml_classification
zip -r lambda3.zip . -x "*.pyc" "__pycache__/*"
aws lambda update-function-code \
  --function-name youth-policy-lambda3-ml-classification \
  --zip-file fileb://lambda3.zip

# Lambda4 배포
cd ../lambda4_rds_storage
zip -r lambda4.zip . -x "*.pyc" "__pycache__/*"
aws lambda update-function-code \
  --function-name youth-policy-lambda4-rds-storage \
  --zip-file fileb://lambda4.zip
```

### 3. ML 모델 업로드 (Lambda3용)
```bash
# 훈련된 모델을 S3에 업로드
aws s3 cp policy_classifier.pkl s3://youth-policy-data-bucket/models/
```

## 모니터링 및 로그

### CloudWatch 로그 그룹
- `/aws/lambda/youth-policy-lambda1-raw-data-ingest`
- `/aws/lambda/youth-policy-lambda2-data-preprocessing`
- `/aws/lambda/youth-policy-lambda3-ml-classification`
- `/aws/lambda/youth-policy-lambda4-rds-storage`

### 주요 메트릭
- 함수별 실행 시간
- 함수별 성공/실패 횟수
- S3 이벤트 처리량
- 데이터 처리량 (레코드 수)

## 장애 처리

### 재시도 메커니즘
- S3 이벤트 트리거는 자동 재시도 지원
- Lambda 함수 내부에서 상세한 오류 로깅
- 실패한 레코드는 별도 처리 가능

### 데이터 일관성
- 각 단계에서 원본 데이터 보존
- 트랜잭션 기반 RDS 저장
- 파티션 기반 데이터 관리로 장애 격리

## 성능 최적화

### Lambda 설정
- **Lambda1**: 512MB, 5분 (데이터 수집)
- **Lambda2**: 1024MB, 10분 (전처리)
- **Lambda3**: 2048MB, 15분 (ML 분류)
- **Lambda4**: 1024MB, 10분 (RDS 저장)

### 비용 최적화
- 각 함수가 필요한 시점에만 실행
- 최소 필요 메모리 및 시간 할당
- S3 Intelligent Tiering 적용 가능

## 확장성

### 수평 확장
- 각 Lambda 함수는 독립적으로 확장
- S3 파티션을 통한 병렬 처리 지원
- 필요시 추가 Lambda 함수 체인 연결 가능

### 기능 확장
- 새로운 전처리 로직 추가 (Lambda2)
- 다양한 ML 모델 지원 (Lambda3)
- 다중 데이터베이스 저장 (Lambda4)
- 알림 및 모니터링 Lambda 추가 