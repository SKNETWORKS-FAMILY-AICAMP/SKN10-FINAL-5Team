# 🚀 AWS 배포 가이드

청년 정책 추천 시스템을 AWS에 배포하는 완전 자동화 가이드입니다.

## 📁 프로젝트 구조

```
aws_deploy/
├── app.py                    # FastAPI 메인 애플리케이션
├── langgraph_agents.py       # LangGraph 에이전트 (AWS용으로 수정)
├── Dockerfile               # Docker 컨테이너 설정
├── requirements.txt         # Python 패키지 목록
├── deploy.sh               # 배포 스크립트
├── upload_vectordb.py      # Vector DB S3 업로드 스크립트
├── env.example            # 환경변수 예시 파일
├── README.md              # 이 문서
└── terraform/             # AWS 인프라 설정 (Infrastructure as Code)
    ├── main.tf            # 메인 Terraform 설정
    ├── variables.tf       # 변수 정의
    └── outputs.tf         # 출력값 정의
```

### 📋 핵심 파일 역할

| 파일명 | 역할 | 주요 기능 |
|--------|------|----------|
| `app.py` | FastAPI 웹 서버 | REST API 엔드포인트 제공, 헬스체크, 정책 추천 |
| `langgraph_agents.py` | AI 에이전트 | LangGraph 기반 정책 추천 로직, Vector DB 검색 |
| `Dockerfile` | 컨테이너 이미지 | Python 애플리케이션 컨테이너화 |
| `requirements.txt` | 의존성 관리 | Python 패키지 버전 명시 |
| `terraform/main.tf` | 인프라 정의 | AWS 리소스 자동 생성 (ECS, RDS, ALB, S3 등) |

## 🛠️ 실제 배포 과정 (단계별 가이드)

### 1단계: 로컬 프로젝트 AWS 환경 적응

#### A. 핵심 파일 수정 작업

**🔧 langgraph_agents.py 생성**
- 기존 `LLM/langgraph_agents.py`를 AWS용으로 수정
- **주요 변경사항:**
  ```python
  # 기존: 로컬 파일 시스템 사용
  # 변경: AWS S3에서 Vector DB 로드
  def load_vector_db():
      if os.getenv('AWS_ENVIRONMENT') == 'true':
          # S3에서 Vector DB 로드
          vector_db_path = '/tmp/vector_db_openai_large_combined'
      else:
          # 로컬 환경
          vector_db_path = '../data/vector_db_openai_large_combined'
  ```

**🔧 app.py 수정**
```python
# 변경 전
from LLM.langgraph_agents import run_graph, db_manager

# 변경 후  
from langgraph_agents import run_graph, db_manager
```

**🔧 Dockerfile 최적화**
```dockerfile
# 추가된 시스템 패키지
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# AWS 환경변수 설정
ENV AWS_ENVIRONMENT=true
```

**🔧 requirements.txt 업그레이드**
```txt
# 주요 버전 업데이트
langchain==0.1.0        # 기존 0.0.x에서 업그레이드
langgraph==0.0.32       # 기존 0.0.x에서 업그레이드
langchain-openai==0.0.6
```

### 2단계: 필수 도구 설치 및 설정

#### A. Terraform 설치 (Windows)
```powershell
# winget으로 설치
winget install HashiCorp.Terraform

# PATH 문제 해결을 위한 PowerShell 별칭 생성
Set-Alias -Name terraform -Value "C:\Users\[사용자명]\AppData\Local\Microsoft\WinGet\Links\terraform.exe"
```

#### B. AWS 자격증명 설정
```bash
# AWS CLI 설정
aws configure
# AWS Access Key ID: [IAM에서 발급받은 키]
# AWS Secret Access Key: [IAM에서 발급받은 비밀키]  
# Default region: ap-northeast-2
# Default output format: json
```

**🔑 AWS IAM 설정 가이드:**
1. AWS 콘솔 로그인
2. IAM → 사용자 → 액세스 키 생성
3. 프로그래밍 액세스 권한 부여
4. 필요한 정책: `AmazonECS_FullAccess`, `AmazonRDS_FullAccess`, `AmazonS3_FullAccess`

### 3단계: Terraform으로 AWS 인프라 자동 구축

```bash
cd aws_deploy/terraform

# 1. Terraform 초기화
terraform init

# 2. 배포 계획 미리보기
terraform plan

# 3. 실제 인프라 생성 (중요: PostgreSQL 버전 이슈 해결)
terraform apply
```

**⚠️ 발생했던 이슈와 해결:**
- **문제**: PostgreSQL 15.4 버전 지원 종료
- **해결**: `terraform/main.tf`에서 `engine_version = "15.8"`로 변경

#### 생성되는 AWS 리소스들:
```
🏗️ 인프라 구성 요소:
├── 🖥️ ECS Fargate Cluster           # 컨테이너 실행 환경
├── 📡 Application Load Balancer     # 외부 트래픽 분산
├── 🗄️ RDS PostgreSQL 15.8          # 정책 데이터베이스  
├── 🗃️ S3 Bucket                    # Vector DB 저장소
├── 📦 ECR Repository                # Docker 이미지 저장소
├── 🔐 Secrets Manager               # API 키 보안 저장
├── 🌐 VPC, 서브넷, 보안그룹          # 네트워크 인프라
└── 📊 CloudWatch                    # 로깅 및 모니터링
```

#### 배포 완료 후 출력 정보:
```bash
# 실제 생성된 리소스 정보
ALB DNS: youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com
ECR URL: 285951302252.dkr.ecr.ap-northeast-2.amazonaws.com/youth-policy-api  
S3 Bucket: youth-policy-api-vectordb-7ayahmcj
RDS Endpoint: youth-policy-api-postgres.czoqimai8z0n.ap-northeast-2.rds.amazonaws.com:5432
```

### 4단계: 시스템 가동 확인

#### A. 헬스체크 테스트
```bash
# API 상태 확인
curl http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com/health

# 정상 응답 예시
{
  "status": "healthy",
  "timestamp": "2025-06-10T05:08:37.009383",
  "database_status": "connected", 
  "vector_db_status": "loaded"
}
```

#### B. API 문서 접속
- **Swagger UI**: `http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com/docs`
- **ReDoc**: `http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com/redoc`

## 🎯 사용 가능한 API 엔드포인트

### 📋 기본 정보 엔드포인트
- `GET /` - API 기본 정보
- `GET /health` - 시스템 상태 확인
- `GET /stats` - 정책 통계 정보

### 🤖 AI 정책 추천 엔드포인트
- `POST /recommend` - 일반 정책 추천
- `POST /search/housing` - 주거 정책 전용 검색
- `POST /search/job` - 취업 정책 전용 검색

### 📝 API 테스트 예시

**정책 추천 요청:**
```json
{
  "message": "25살 대학생인데 주거 지원 정책 알려주세요",
  "user_profile": {
    "age": 25,
    "income_code": "낮음",
    "region": "서울",
    "marital_status": "미혼", 
    "job_code": "학생",
    "edu_code": "대학교",
    "special_code": null
  }
}
```

## 💡 시스템 작동 원리

### 🔄 요청 처리 플로우
```
🌐 사용자 요청 
    ↓
📡 Application Load Balancer
    ↓  
🐳 ECS Fargate Container
    ├── 🤖 LangGraph Agent (질문 분석)
    ├── 🔍 Vector Search (유사 정책 검색)
    └── 🧠 OpenAI GPT (답변 생성)
    ↓
🗄️ PostgreSQL (정책 데이터 조회)
🗃️ S3 Vector DB (임베딩 벡터 검색)
    ↓
📤 맞춤형 정책 추천 응답
```

### 🔧 핵심 기술 스택
- **Backend**: FastAPI (Python)
- **AI**: LangGraph + OpenAI GPT
- **Vector Search**: FAISS + OpenAI Embeddings
- **Database**: PostgreSQL (정책 데이터)
- **Container**: Docker + ECS Fargate
- **Infrastructure**: Terraform (IaC)

## 🎯 포함된 AWS 서비스

- **🐳 ECS Fargate**: 컨테이너 실행 환경
- **📡 Application Load Balancer**: 로드 밸런싱 및 외부 접근
- **🗄️ RDS PostgreSQL**: 정책 데이터베이스
- **🗃️ S3**: Vector DB 저장소
- **🔐 Secrets Manager**: API 키 및 DB 비밀번호 관리
- **📝 CloudWatch**: 로깅 및 모니터링
- **🏗️ ECR**: Docker 이미지 저장소

## 🛠️ 사전 준비

### 1. 필수 도구 설치

```bash
# AWS CLI 설치 (Windows)
winget install Amazon.AWSCLI

# Docker Desktop 설치
winget install Docker.DockerDesktop

# Terraform 설치
winget install Hashicorp.Terraform

# jq 설치 (JSON 파싱용)
winget install jqlang.jq
```

### 2. AWS 자격 증명 설정

```bash
aws configure
# AWS Access Key ID: [발급받은 Access Key]
# AWS Secret Access Key: [발급받은 Secret Key]
# Default region name: ap-northeast-2
# Default output format: json
```

### 3. OpenAI API 키 준비

OpenAI 플랫폼에서 API 키를 발급받아 준비하세요.

## 🚀 자동 배포 실행

### 단일 명령어로 전체 배포

```bash
cd aws_deploy
chmod +x deploy.sh
./deploy.sh
```

### 단계별 수동 배포

#### 1단계: 인프라 배포

```bash
cd terraform
terraform init
terraform plan -var="project_name=youth-policy-api"
terraform apply -var="project_name=youth-policy-api"
```

#### 2단계: Vector DB 업로드

```bash
# S3 버킷 이름 확인
S3_BUCKET=$(terraform output -raw s3_bucket_name)

# Vector DB 업로드
aws s3 sync ../data/vector_db_openai_large_combined s3://$S3_BUCKET/vector_db_openai_large_combined/
```

#### 3단계: Docker 이미지 빌드 및 배포

```bash
# ECR 로그인
ECR_URL=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin $ECR_URL

# 이미지 빌드 및 푸시
cd ..
docker build -t youth-policy-api .
docker tag youth-policy-api:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

#### 4단계: OpenAI API 키 설정

```bash
aws secretsmanager put-secret-value \
    --secret-id "youth-policy-api-openai-api-key" \
    --secret-string "YOUR_OPENAI_API_KEY"
```

#### 5단계: 데이터베이스 초기화

```bash
# RDS 엔드포인트 확인
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)

# 데이터베이스 접속 후 테이블 생성 및 데이터 임포트
# (별도 가이드 참조)
```

## 📊 배포 후 확인

### API 엔드포인트 테스트

```bash
# ALB DNS 확인
ALB_DNS=$(terraform output -raw alb_dns_name)

# 헬스 체크
curl http://$ALB_DNS/health

# API 문서 확인
curl http://$ALB_DNS/docs

# 통계 확인
curl http://$ALB_DNS/stats
```

### 정책 추천 테스트

```bash
curl -X POST http://$ALB_DNS/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "message": "서울 청년 주거 지원 정책을 알려주세요",
    "user_profile": {
      "age": 25,
      "region": "서울특별시",
      "income_code": "저소득"
    }
  }'
```

## 🔧 주요 설정

### 환경 변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `AWS_ENVIRONMENT` | AWS 환경 여부 | `true` |
| `S3_BUCKET_NAME` | Vector DB 저장 버킷 | `youth-policy-vectordb-xxx` |
| `POSTGRES_HOST` | RDS 엔드포인트 | `xxx.rds.amazonaws.com` |
| `OPENAI_API_KEY` | OpenAI API 키 | `sk-xxx` |

### 보안 설정

- **RDS**: Private 서브넷, 보안 그룹으로 ECS에서만 접근
- **Secrets Manager**: API 키 및 DB 비밀번호 암호화 저장
- **S3**: 서버 사이드 암호화 활성화
- **ECS**: 최소 권한 IAM 역할 적용

## 💰 비용 최적화

### 예상 월 비용 (서울 리전)

- **ECS Fargate**: ~$20 (1 vCPU, 3GB RAM)
- **RDS t3.micro**: ~$15 (20GB 스토리지)
- **ALB**: ~$20
- **S3**: ~$1 (Vector DB 저장)
- **기타**: ~$5

**총 예상 비용**: ~$60/월

### 비용 절약 팁

1. **개발/테스트 환경**: 사용하지 않을 때 ECS 서비스 중단
2. **RDS**: 개발용으로는 `db.t3.micro`의 버스터블 성능 활용
3. **S3**: Intelligent Tiering 활성화
4. **CloudWatch**: 불필요한 로그 그룹 삭제

## 🔍 모니터링 및 로깅

### CloudWatch 대시보드

- **ECS 메트릭**: CPU, 메모리 사용률
- **ALB 메트릭**: 요청 수, 응답 시간, 오류율
- **RDS 메트릭**: 연결 수, 쿼리 성능

### 로그 확인

```bash
# ECS 태스크 로그 확인
aws logs tail /ecs/youth-policy-api --follow
```

## 🚨 문제 해결

### 일반적인 문제들

#### 1. ECS 태스크가 시작되지 않는 경우

```bash
# 태스크 상태 확인
aws ecs describe-tasks --cluster youth-policy-api-cluster --tasks [TASK_ARN]

# 로그 확인
aws logs get-log-events --log-group-name /ecs/youth-policy-api --log-stream-name [STREAM_NAME]
```

#### 2. RDS 연결 오류

- 보안 그룹 설정 확인
- 서브넷 그룹 설정 확인
- Secrets Manager에서 비밀번호 확인

#### 3. Vector DB 로드 실패

- S3 버킷 권한 확인
- Vector DB 파일 업로드 상태 확인
- ECS 태스크 역할의 S3 권한 확인

### 디버깅 명령어

```bash
# ECS 서비스 이벤트 확인
aws ecs describe-services --cluster youth-policy-api-cluster --services youth-policy-api-service

# 태스크 정의 확인
aws ecs describe-task-definition --task-definition youth-policy-api-app

# S3 버킷 내용 확인
aws s3 ls s3://BUCKET_NAME/vector_db_openai_large_combined/ --recursive
```

## 🔄 업데이트 및 배포

### 코드 업데이트

```bash
# 새 이미지 빌드 및 푸시
docker build -t youth-policy-api:latest .
docker tag youth-policy-api:latest $ECR_URL:latest
docker push $ECR_URL:latest

# ECS 서비스 업데이트 (새 배포)
aws ecs update-service \
    --cluster youth-policy-api-cluster \
    --service youth-policy-api-service \
    --force-new-deployment
```

### 인프라 변경

```bash
cd terraform
terraform plan
terraform apply
```

## 🗑️ 리소스 정리

### 전체 삭제

```bash
cd terraform
terraform destroy
```

### 개별 리소스 삭제

주요 비용 발생 리소스만 선별적으로 정리할 수 있습니다:

- ECS 서비스 중단
- RDS 인스턴스 삭제
- ALB 삭제

---

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. **CloudWatch 로그**: 상세한 오류 메시지
2. **AWS 상태 페이지**: 서비스 장애 여부
3. **Terraform 상태**: 인프라 상태 일관성

더 자세한 도움이 필요하면 프로젝트 이슈를 생성해주세요. 