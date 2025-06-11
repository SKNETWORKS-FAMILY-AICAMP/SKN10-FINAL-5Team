# Docker PostgreSQL → AWS RDS 마이그레이션 가이드

이 가이드는 현재 Docker 컨테이너에서 실행 중인 PostgreSQL 데이터베이스를 AWS RDS로 마이그레이션하는 과정을 설명합니다.

## 사전 준비사항

### 1. AWS 자격 증명 설정
```bash
# AWS CLI 설치 및 설정
aws configure
# 또는 환경변수로 설정
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=ap-northeast-2
```

### 2. 필요한 권한
- EC2 (보안 그룹, VPC, 서브넷 관리)
- RDS (인스턴스 생성, 관리)

### 3. 필요한 도구 설치
```bash
# Python 패키지 설치
pip install -r scripts/requirements_rds.txt

# PostgreSQL 클라이언트 도구 (Windows)
# https://www.postgresql.org/download/windows/
# pg_dump, psql 명령어가 PATH에 있어야 함
```

## 마이그레이션 단계

### 1단계: AWS RDS 인스턴스 생성
```bash
cd scripts
python create_rds_instance.py
```

**이 단계에서 수행되는 작업:**
- 퍼블릭 접근 가능한 보안 그룹 생성 (포트 5432 개방)
- DB 서브넷 그룹 생성
- PostgreSQL RDS 인스턴스 생성 (db.t3.micro, 프리 티어)
- `rds_config.env` 파일 자동 생성

**예상 소요 시간:** 5-10분

### 2단계: 데이터 마이그레이션
```bash
cd scripts
python dump_migrate_data.py
```

**이 단계에서 수행되는 작업:**
- Docker PostgreSQL 연결 테스트
- AWS RDS 연결 테스트
- 데이터 덤프 (pg_dump)
- RDS로 데이터 복원 (psql)
- 마이그레이션 결과 검증

**예상 소요 시간:** 5-15분 (데이터 크기에 따라)

### 3단계: 애플리케이션 설정 업데이트

#### 환경 변수 업데이트
생성된 `scripts/rds_config.env` 파일의 내용을 확인하고 애플리케이션에 적용:

```bash
# 생성된 RDS 설정 확인
cat scripts/rds_config.env
```

#### FastAPI 애플리케이션 업데이트
`aws_deploy/app.py`에서 환경 변수를 RDS 설정으로 변경:

```python
# 기존 Docker 설정 대신 RDS 설정 사용
os.environ['DB_HOST'] = 'your-rds-endpoint.ap-northeast-2.rds.amazonaws.com'
os.environ['DB_PORT'] = '5432'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'YouthPolicy2024!'
os.environ['DB_NAME'] = 'youth_policy'
os.environ['AWS_ENVIRONMENT'] = 'true'
```

### 4단계: 연결 테스트

#### DBeaver로 RDS 연결 테스트
1. DBeaver 열기
2. 새 연결 생성 (PostgreSQL)
3. RDS 엔드포인트 정보 입력:
   - **Host**: `your-rds-endpoint.ap-northeast-2.rds.amazonaws.com`
   - **Port**: `5432`
   - **Database**: `youth_policy`
   - **Username**: `postgres`
   - **Password**: `YouthPolicy2024!`

#### 애플리케이션 테스트
```bash
# 로컬에서 애플리케이션 실행
cd aws_deploy
python -m uvicorn app:app --reload

# 헬스 체크
curl http://localhost:8000/health

# 정책 검색 테스트
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "message": "주거 지원 정책",
    "user_profile": {
      "age": 25,
      "region": "서울",
      "income_code": "저소득"
    }
  }'
```

## 보안 고려사항

### 1. 퍼블릭 접근 제한
현재 설정은 모든 IP에서 접근 가능합니다. 운영 환경에서는 특정 IP만 허용하도록 보안 그룹을 수정하세요:

```python
# 특정 IP만 허용하는 경우
'IpRanges': [{'CidrIp': 'YOUR_IP/32', 'Description': 'My IP only'}]
```

### 2. 비밀번호 보안
- 강력한 비밀번호 사용
- AWS Secrets Manager 사용 고려
- 환경 변수로 민감 정보 관리

### 3. SSL/TLS 연결
RDS는 기본적으로 SSL 연결을 지원합니다. 애플리케이션에서 SSL 연결 사용:

```python
# SSL 연결 사용
conn = psycopg2.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    database=database,
    sslmode='require'
)
```

## 비용 최적화

### 프리 티어 사용량
- **인스턴스**: db.t3.micro (월 750시간 무료)
- **스토리지**: 20GB (월 20GB 무료)
- **백업**: 20GB (백업 스토리지 무료)

### 비용 모니터링
- AWS Cost Explorer로 비용 추적
- CloudWatch로 리소스 사용량 모니터링
- 불필요한 시간에는 인스턴스 중지 고려

## 트러블슈팅

### 연결 오류
1. **보안 그룹 확인**: 포트 5432가 열려있는지 확인
2. **RDS 상태 확인**: 인스턴스가 'available' 상태인지 확인
3. **네트워크 확인**: ping으로 엔드포인트 접근성 확인

### 권한 오류
```bash
# AWS 자격 증명 확인
aws sts get-caller-identity

# RDS 권한 확인
aws rds describe-db-instances
```

### 마이그레이션 오류
- pg_dump/psql 도구가 PATH에 있는지 확인
- Docker PostgreSQL이 실행 중인지 확인
- 충분한 디스크 공간이 있는지 확인

## 정리 작업

### Docker PostgreSQL 중지 (선택사항)
마이그레이션이 완료되고 RDS 연결이 확인되면 Docker PostgreSQL을 중지할 수 있습니다:

```bash
# Docker 컨테이너 확인
docker ps

# PostgreSQL 컨테이너 중지
docker stop <postgres_container_id>
```

### 백업 권장사항
- RDS 자동 백업 활성화 (7일 보관)
- 중요한 변경 전 수동 스냅샷 생성
- 정기적인 데이터 내보내기

## 다음 단계

1. **모니터링 설정**: CloudWatch로 RDS 성능 모니터링
2. **자동화**: Infrastructure as Code (Terraform, CloudFormation)
3. **CI/CD 통합**: 배포 파이프라인에 RDS 설정 포함
4. **보안 강화**: VPC 내 프라이빗 서브넷 사용 고려

이제 AWS RDS를 사용하여 확장 가능하고 관리하기 쉬운 데이터베이스 환경을 구축했습니다! 