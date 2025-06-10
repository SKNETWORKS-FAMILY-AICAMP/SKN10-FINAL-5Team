#!/bin/bash

# AWS 배포 자동화 스크립트
set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 설정 변수
PROJECT_NAME="youth-policy-api"
AWS_REGION="ap-northeast-2"
DOCKER_IMAGE_TAG="latest"

# 필수 도구 확인
check_prerequisites() {
    log_info "필수 도구 확인 중..."
    
    command -v aws >/dev/null 2>&1 || { log_error "AWS CLI가 설치되지 않았습니다."; exit 1; }
    command -v docker >/dev/null 2>&1 || { log_error "Docker가 설치되지 않았습니다."; exit 1; }
    command -v terraform >/dev/null 2>&1 || { log_error "Terraform이 설치되지 않았습니다."; exit 1; }
    
    log_success "모든 필수 도구가 설치되어 있습니다."
}

# AWS 자격 증명 확인
check_aws_credentials() {
    log_info "AWS 자격 증명 확인 중..."
    
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        log_error "AWS 자격 증명이 설정되지 않았습니다."
        log_info "다음 명령어로 설정하세요: aws configure"
        exit 1
    fi
    
    log_success "AWS 자격 증명이 확인되었습니다."
}

# Terraform 초기화
init_terraform() {
    log_info "Terraform 초기화 중..."
    
    cd terraform
    terraform init
    
    log_success "Terraform 초기화 완료"
}

# 인프라 배포
deploy_infrastructure() {
    log_info "AWS 인프라 배포 중..."
    
    # Terraform plan 실행
    terraform plan -var="aws_region=${AWS_REGION}" -var="project_name=${PROJECT_NAME}"
    
    # 사용자 확인
    read -p "위 계획을 실행하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "배포가 취소되었습니다."
        exit 0
    fi
    
    # Terraform apply 실행
    terraform apply -var="aws_region=${AWS_REGION}" -var="project_name=${PROJECT_NAME}" -auto-approve
    
    # 출력값 저장
    terraform output -json > ../terraform-outputs.json
    
    log_success "인프라 배포 완료"
    cd ..
}

# ECR 로그인
ecr_login() {
    log_info "ECR 로그인 중..."
    
    ECR_REPOSITORY_URL=$(cat terraform-outputs.json | jq -r '.ecr_repository_url.value')
    AWS_ACCOUNT_ID=$(echo $ECR_REPOSITORY_URL | cut -d'.' -f1)
    
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URL
    
    log_success "ECR 로그인 완료"
}

# Docker 이미지 빌드 및 푸시
build_and_push_docker() {
    log_info "Docker 이미지 빌드 중..."
    
    # 프로젝트 루트에서 빌드
    cd ..
    
    # Dockerfile과 필요한 파일들을 aws_deploy로 복사
    cp -r LLM aws_deploy/
    cp -r data aws_deploy/ 2>/dev/null || log_warning "data 디렉토리가 없습니다. Vector DB를 S3에 별도 업로드해야 합니다."
    
    cd aws_deploy
    
    ECR_REPOSITORY_URL=$(cat terraform-outputs.json | jq -r '.ecr_repository_url.value')
    
    # Docker 이미지 빌드
    docker build -t $PROJECT_NAME:$DOCKER_IMAGE_TAG .
    
    # 태그 지정
    docker tag $PROJECT_NAME:$DOCKER_IMAGE_TAG $ECR_REPOSITORY_URL:$DOCKER_IMAGE_TAG
    
    # ECR에 푸시
    docker push $ECR_REPOSITORY_URL:$DOCKER_IMAGE_TAG
    
    log_success "Docker 이미지 빌드 및 푸시 완료"
}

# Vector DB를 S3에 업로드
upload_vector_db() {
    log_info "Vector DB를 S3에 업로드 중..."
    
    S3_BUCKET_NAME=$(cat terraform-outputs.json | jq -r '.s3_bucket_name.value')
    
    if [ -d "../data/vector_db_openai_large_combined" ]; then
        log_info "Vector DB 디렉토리 발견. S3에 업로드 중..."
        aws s3 sync ../data/vector_db_openai_large_combined s3://$S3_BUCKET_NAME/vector_db_openai_large_combined/ --delete
        log_success "Vector DB 업로드 완료"
    else
        log_warning "Vector DB 디렉토리를 찾을 수 없습니다."
        log_info "Python 스크립트를 사용하여 업로드를 시도합니다..."
        
        # Python 스크립트를 사용하여 업로드
        export S3_BUCKET_NAME=$S3_BUCKET_NAME
        python3 upload_vectordb.py
        
        if [ $? -eq 0 ]; then
            log_success "Vector DB 업로드 완료 (Python 스크립트 사용)"
        else
            log_error "Vector DB 업로드 실패"
            exit 1
        fi
    fi
}

# 데이터베이스 초기화
init_database() {
    log_info "데이터베이스 초기화 중..."
    
    RDS_ENDPOINT=$(cat terraform-outputs.json | jq -r '.rds_endpoint.value')
    
    log_info "RDS 엔드포인트: $RDS_ENDPOINT"
    log_warning "데이터베이스 초기화는 수동으로 진행해야 합니다:"
    log_info "1. RDS에 연결하여 테이블 생성"
    log_info "2. CSV 데이터 임포트"
    log_info "3. 인덱스 생성"
}

# OpenAI API 키 설정
set_openai_api_key() {
    log_info "OpenAI API 키 설정 중..."
    
    if [ -z "$OPENAI_API_KEY" ]; then
        read -p "OpenAI API 키를 입력하세요: " -s OPENAI_API_KEY
        echo
    fi
    
    aws secretsmanager put-secret-value \
        --secret-id "${PROJECT_NAME}-openai-api-key" \
        --secret-string "$OPENAI_API_KEY" \
        --region $AWS_REGION
    
    log_success "OpenAI API 키 설정 완료"
}

# ECS 서비스 업데이트
update_ecs_service() {
    log_info "ECS 서비스 업데이트 중..."
    
    aws ecs update-service \
        --cluster "${PROJECT_NAME}-cluster" \
        --service "${PROJECT_NAME}-service" \
        --force-new-deployment \
        --region $AWS_REGION
    
    log_success "ECS 서비스 업데이트 완료"
}

# 배포 상태 확인
check_deployment() {
    log_info "배포 상태 확인 중..."
    
    ALB_DNS_NAME=$(cat terraform-outputs.json | jq -r '.alb_dns_name.value')
    
    log_info "Application Load Balancer DNS: http://$ALB_DNS_NAME"
    log_info "헬스 체크 URL: http://$ALB_DNS_NAME/health"
    
    # 헬스 체크 대기
    log_info "서비스가 시작될 때까지 대기 중..."
    for i in {1..30}; do
        if curl -s -f "http://$ALB_DNS_NAME/health" >/dev/null 2>&1; then
            log_success "서비스가 정상적으로 시작되었습니다!"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_warning "서비스 시작 확인에 실패했습니다. 수동으로 확인해주세요."
        else
            echo -n "."
            sleep 10
        fi
    done
}

# 메인 함수
main() {
    log_info "=== AWS 배포 시작 ==="
    
    # 1. 사전 확인
    check_prerequisites
    check_aws_credentials
    
    # 2. 인프라 배포
    init_terraform
    deploy_infrastructure
    
    # 3. 애플리케이션 배포
    ecr_login
    build_and_push_docker
    
    # 4. 데이터 업로드
    upload_vector_db
    
    # 5. 설정
    set_openai_api_key
    update_ecs_service
    
    # 6. 배포 확인
    check_deployment
    
    log_success "=== 배포 완료 ==="
    
    # 접속 정보 출력
    ALB_DNS_NAME=$(cat terraform-outputs.json | jq -r '.alb_dns_name.value')
    echo
    echo "🚀 배포된 API 정보:"
    echo "   📡 API URL: http://$ALB_DNS_NAME"
    echo "   💚 헬스체크: http://$ALB_DNS_NAME/health"
    echo "   📚 API 문서: http://$ALB_DNS_NAME/docs"
    echo "   📊 통계: http://$ALB_DNS_NAME/stats"
}

# 스크립트 실행
main "$@" 