# 📊 정책 DB 관리 파이프라인

청년정책 데이터베이스의 생명주기 관리, 데이터 품질 보장, 성능 최적화를 위한 자동화된 파이프라인입니다.

## 🎯 주요 기능

### 1. **정책 생명주기 관리**
- **만료된 정책 아카이브**: 신청 마감일이 지난 정책을 자동으로 아카이브 테이블로 이동
- **만료 예정 알림**: 7일 내 만료 예정인 정책에 대한 사전 알림
- **유예 기간 관리**: 30~60일의 유예 기간을 두고 단계적 처리
- **관련 데이터 정리**: 아카이브된 정책의 임베딩 데이터도 함께 정리

### 2. **데이터 품질 관리**
- **고아 임베딩 정리**: 정책은 삭제되었지만 임베딩이 남아있는 경우 자동 정리
- **중복 데이터 탐지**: 동일한 정책명의 중복 데이터 식별 (향후 확장 예정)
- **데이터 정합성 검증**: 필수 필드 누락, 잘못된 날짜 범위 등 검증 (향후 확장 예정)

### 3. **자동화된 스케줄링**
- **일일 점검** (매일 새벽 2시 UTC): 만료 예정 정책 알림
- **주간 정리** (매주 일요일 새벽 3시 UTC): 만료된 정책 아카이브 + 고아 임베딩 정리
- **월간 유지보수** (매월 1일 새벽 4시 UTC): 전체 유지보수 (60일 유예기간)

### 4. **모니터링 및 알림**
- **SNS 알림**: 유지보수 작업 결과를 이메일로 전송
- **상세한 로깅**: CloudWatch Logs를 통한 모든 작업 기록
- **통계 정보**: 전체/활성/만료 정책 수 등 실시간 통계

## 🏗️ 아키텍처

```
EventBridge Rules
    ↓
Lambda Function (DB Maintenance)
    ↓
PostgreSQL Database
    ↓
SNS Topic → Email Notifications
```

### 주요 구성 요소

1. **PolicyDBManager** (`policy_db_manager.py`)
   - 핵심 DB 관리 로직
   - 정책 통계 수집
   - 만료된 정책 처리
   - 고아 임베딩 정리

2. **DB Maintenance Lambda** (`db_maintenance_lambda.py`)
   - EventBridge 스케줄러에 의해 트리거
   - 작업 유형별 다른 유지보수 실행
   - 결과 알림 발송

3. **CloudFormation Resources**
   - Lambda 함수 및 실행 역할
   - EventBridge 스케줄 규칙
   - SNS 토픽 및 구독

## 📋 스케줄 상세

### 일일 점검 (Daily)
```json
{
  "maintenance_type": "daily",
  "operations": [
    "만료 예정 정책 알림"
  ],
  "schedule": "cron(0 2 * * ? *)"
}
```

### 주간 정리 (Weekly)
```json
{
  "maintenance_type": "weekly", 
  "operations": [
    "만료된 정책 아카이브 (30일 유예)",
    "고아 임베딩 정리",
    "만료 예정 정책 알림"
  ],
  "schedule": "cron(0 3 ? * SUN *)"
}
```

### 월간 유지보수 (Monthly)
```json
{
  "maintenance_type": "monthly",
  "operations": [
    "만료된 정책 아카이브 (60일 유예)",
    "고아 임베딩 정리", 
    "만료 예정 정책 알림"
  ],
  "schedule": "cron(0 4 1 * ? *)"
}
```

## 🚀 배포 및 설정

### 1. CloudFormation 배포
```bash
aws cloudformation deploy \
  --template-file cloudformation.yaml \
  --stack-name youth-policy-stack \
  --parameter-overrides \
    NotificationEmail=your-email@example.com \
    ProjectName=youth-policy \
  --capabilities CAPABILITY_IAM
```

### 2. 환경 변수 설정
Lambda 함수는 다음 환경 변수들을 사용합니다:

- `DB_HOST`: PostgreSQL 호스트
- `DB_PORT`: PostgreSQL 포트 (기본: 5432)
- `DB_NAME`: 데이터베이스 이름
- `DB_USER`: 데이터베이스 사용자
- `DB_PASSWORD`: 데이터베이스 비밀번호
- `SNS_TOPIC_ARN`: 알림용 SNS 토픽 ARN

### 3. 알림 설정
SNS 토픽에 이메일 구독을 추가하여 유지보수 결과를 받아볼 수 있습니다:

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:region:account:youth-policy-policy-notifications \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## 📊 모니터링

### CloudWatch Logs
모든 유지보수 작업은 CloudWatch Logs에 상세히 기록됩니다:
- `/aws/lambda/youth-policy-policy-db-maintenance`

### 주요 메트릭
- 아카이브된 정책 수
- 정리된 고아 임베딩 수
- 발생한 오류 수
- 실행 시간

### 알림 메시지 예시
```
정책 DB 유지보수 완료
전체: 1,234, 활성: 1,100, 만료: 134
아카이브: 15개, 정리된 임베딩: 3개
```

## 🔧 수동 실행

필요시 Lambda 함수를 수동으로 실행할 수 있습니다:

```bash
# 일일 점검 실행
aws lambda invoke \
  --function-name youth-policy-policy-db-maintenance \
  --payload '{"maintenance_type": "daily"}' \
  response.json

# 주간 정리 실행
aws lambda invoke \
  --function-name youth-policy-policy-db-maintenance \
  --payload '{"maintenance_type": "weekly"}' \
  response.json
```

## 🛠️ 향후 확장 계획

### Phase 2: 고급 데이터 품질 관리
- **중복 정책 자동 병합**: 동일 정책의 여러 버전 자동 통합
- **데이터 정합성 자동 수정**: 잘못된 날짜, 연령 범위 등 자동 보정
- **URL 유효성 검증**: 정책 신청 URL의 접근 가능성 주기적 확인

### Phase 3: 성능 최적화
- **인덱스 자동 최적화**: 쿼리 패턴 분석 후 인덱스 재구성
- **파티션 관리**: 날짜별 파티션 자동 생성 및 관리
- **통계 정보 자동 업데이트**: 쿼리 플래너 최적화

### Phase 4: 고급 모니터링
- **이상 패턴 탐지**: 정책 수 급변, 오류율 증가 등 자동 감지
- **성능 지표 대시보드**: CloudWatch 대시보드를 통한 실시간 모니터링
- **비용 최적화**: OpenAI API 호출 비용 추적 및 최적화

### Phase 5: 백업 및 복구
- **자동 백업**: 정기적인 데이터베이스 스냅샷 생성
- **Point-in-Time Recovery**: 특정 시점으로의 복구 기능
- **재해 복구**: 다중 AZ 백업 및 복구 자동화

## ⚠️ 주의사항

1. **타임존**: 모든 스케줄은 UTC 기준입니다. 한국 시간(KST)으로는 +9시간입니다.
2. **유예기간**: 만료된 정책도 즉시 삭제되지 않고 유예 기간을 둡니다.
3. **아카이브**: 삭제 대신 아카이브를 기본으로 하여 데이터 복구 가능성을 보장합니다.
4. **알림**: 중요한 작업 결과는 항상 SNS를 통해 알림이 발송됩니다.

## 📞 문의

정책 DB 관리 파이프라인에 대한 문의사항이나 개선 제안이 있으시면 개발팀에 연락해 주세요. 