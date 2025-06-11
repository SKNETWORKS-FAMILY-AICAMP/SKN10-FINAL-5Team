# AWS 배포 청년 정책 추천 API 사용 가이드

## 🚀 API 기본 정보

- **베이스 URL**: `http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com`
- **프로토콜**: HTTP
- **포트**: 80 (기본)
- **인프라**: AWS ECS + ALB + RDS PostgreSQL

## 📋 사용 가능한 엔드포인트

### 1. 헬스 체크 & 시스템 정보

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| GET | `/` | API 기본 정보 |
| GET | `/health` | 헬스 체크 (DB 연결 상태 포함) |
| GET | `/stats` | 시스템 통계 정보 |

### 2. 정책 추천 서비스

| 메서드 | 엔드포인트 | 설명 |
|--------|------------|------|
| POST | `/recommend` | 일반 정책 추천 |
| POST | `/search/housing` | 주거 정책 전용 검색 |
| POST | `/search/job` | 취업 정책 전용 검색 |

## 🔧 사용 방법

### 1. Python으로 호출

```bash
# 의존성 설치
pip install requests

# 실행
python api_client_example.py
```

### 2. cURL로 호출

```bash
# 실행 권한 부여
chmod +x api_test_commands.sh

# 테스트 실행
./api_test_commands.sh
```

### 3. Node.js로 호출

```bash
# 의존성 설치
npm install axios

# 실행
node api_client_example.js
```

## 📝 요청/응답 형식

### 사용자 프로필 형식 (UserProfile)

```json
{
  "age": 25,                    // 나이 (필수)
  "income_code": "middle",      // 소득 수준 (선택)
  "region": "서울",             // 지역 (선택)
  "marital_status": "미혼",     // 결혼 상태 (선택)
  "job_code": "unemployed",     // 직업 상태 (선택)
  "edu_code": "university",     // 교육 수준 (선택)
  "special_code": null          // 특수 조건 (선택)
}
```

### 정책 추천 요청 형식 (PolicyRequest)

```json
{
  "message": "청년을 위한 주거 정책을 추천해주세요",
  "user_profile": {
    "age": 25,
    "income_code": "middle",
    "region": "서울",
    "marital_status": "미혼",
    "job_code": "unemployed",
    "edu_code": "university",
    "special_code": null
  }
}
```

### 정책 추천 응답 형식 (PolicyResponse)

```json
{
  "response": "추천 정책 내용...",
  "timestamp": "2024-01-15T10:30:00",
  "user_profile": { ... }
}
```

## 🔍 빠른 테스트

### 헬스 체크

```bash
curl http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com/health
```

### 간단한 정책 추천

```bash
curl -X POST http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "message": "청년 지원 정책",
    "user_profile": {
      "age": 25,
      "region": "서울"
    }
  }'
```

## ⚡ 성능 & 제한사항

- **타임아웃**: 30초
- **동시 연결**: ALB 및 ECS 설정에 따라 제한
- **요청 크기**: 일반적인 JSON 페이로드 크기 제한
- **응답 시간**: LangGraph 처리 시간에 따라 5-30초

## 🛠️ 문제 해결

### 1. 연결 실패 시

```bash
# 헬스 체크로 서비스 상태 확인
curl http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com/health

# 네트워크 연결 확인
ping youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com
```

### 2. 서비스 상태 확인

```bash
# AWS CLI로 ECS 서비스 상태 확인 (권한 필요)
aws ecs describe-services --cluster youth-policy-api-cluster --services youth-policy-api-service
```

### 3. 로그 확인

```bash
# CloudWatch 로그 확인 (권한 필요)
aws logs tail /ecs/youth-policy-api --follow
```

## 📚 추가 리소스

- **Swagger UI**: 현재 미구성 (추후 추가 예정)
- **API 문서**: 이 가이드
- **인프라 관리**: `terraform/` 디렉토리 참고
- **백업 관리**: `terraform-backup.sh` 스크립트 사용

## 🔒 보안 참고사항

- 현재 HTTP 프로토콜 사용 (개발 환경)
- 프로덕션 환경에서는 HTTPS 설정 필요
- API 키나 인증 토큰 없이 공개 접근 가능
- CORS 설정으로 모든 Origin 허용 중

---

**문의사항이나 이슈가 있으시면 개발팀에 연락해주세요.** 