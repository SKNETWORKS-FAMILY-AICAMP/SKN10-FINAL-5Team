#!/bin/bash

# Youth Policy Data Processing Pipeline 배포 스크립트
# 4개의 Lambda 함수와 S3, Secrets Manager를 배포합니다.

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
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

# 필수 도구 확인
check_prerequisites() {
    log_info "필수 도구들을 확인합니다..."
    
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI가 설치되지 않았습니다."
        exit 1
    fi
    
    if ! command -v zip &> /dev/null; then
        log_error "zip 명령어가 설치되지 않았습니다."
        exit 1
    fi
    
    # AWS 자격 증명 확인
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS 자격 증명이 구성되지 않았습니다."
        exit 1
    fi
    
    log_success "모든 필수 도구가 확인되었습니다."
}

# 설정 로드
load_config() {
    log_info "배포 설정을 로드합니다..."
    
    # 기본값 설정
    STACK_NAME="youth-policy-pipeline"
    REGION="ap-northeast-2"
    BUCKET_NAME="youth-policy-data-bucket-$(date +%s)"
    SECRET_NAME="youth-policy-secrets"
    
    # 환경변수에서 오버라이드
    STACK_NAME=${STACK_NAME:-$1}
    REGION=${AWS_REGION:-$REGION}
    
    log_info "스택 이름: $STACK_NAME"
    log_info "리전: $REGION"
    log_info "S3 버킷: $BUCKET_NAME"
    log_info "시크릿 이름: $SECRET_NAME"
}

# Lambda 함수 패키징
package_lambda_functions() {
    log_info "Lambda 함수들을 패키징합니다..."
    
    # 패키지 디렉토리 생성
    mkdir -p packages
    
    # Lambda1: Raw Data Ingestion
    log_info "Lambda1 패키징 중..."
    cd lambda_functions/lambda1_raw_data_ingest
    zip -r ../../packages/lambda1.zip . -x "*.pyc" "__pycache__/*"
    cd ../..
    
    # Lambda2: Data Preprocessing  
    log_info "Lambda2 패키징 중..."
    cd lambda_functions/lambda2_data_preprocessing
    zip -r ../../packages/lambda2.zip . -x "*.pyc" "__pycache__/*"
    cd ../..
    
    # Lambda3: ML Classification
    log_info "Lambda3 패키징 중..."
    cd lambda_functions/lambda3_ml_classification
    zip -r ../../packages/lambda3.zip . -x "*.pyc" "__pycache__/*"
    cd ../..
    
    # Lambda4: RDS Storage
    log_info "Lambda4 패키징 중..."
    cd lambda_functions/lambda4_rds_storage
    zip -r ../../packages/lambda4.zip . -x "*.pyc" "__pycache__/*"
    cd ../..
    
    # Shared utilities 각 패키지에 추가
    log_info "공통 라이브러리를 각 패키지에 추가합니다..."
    for i in {1..4}; do
        cd packages
        mkdir -p temp_lambda$i
        cd temp_lambda$i
        unzip -q ../lambda$i.zip
        cp -r ../../lambda_functions/shared/* .
        zip -r ../lambda$i.zip . -x "*.pyc" "__pycache__/*"
        cd ..
        rm -rf temp_lambda$i
        cd ..
    done
    
    log_success "모든 Lambda 함수 패키징 완료"
}

# CloudFormation 스택 배포
deploy_infrastructure() {
    log_info "CloudFormation 스택을 배포합니다..."
    
    # 스택 존재 여부 확인
    if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION &> /dev/null; then
        log_info "기존 스택을 업데이트합니다..."
        OPERATION="update-stack"
    else
        log_info "새로운 스택을 생성합니다..."
        OPERATION="create-stack"
    fi
    
    # CloudFormation 배포
    aws cloudformation $OPERATION \
        --stack-name $STACK_NAME \
        --template-body file://cloudformation.yaml \
        --parameters \
            ParameterKey=SecretName,ParameterValue=$SECRET_NAME \
            ParameterKey=BucketName,ParameterValue=$BUCKET_NAME \
        --capabilities CAPABILITY_IAM \
        --region $REGION
    
    log_info "CloudFormation 스택 배포를 기다립니다..."
    aws cloudformation wait stack-${OPERATION/-*/}-complete \
        --stack-name $STACK_NAME \
        --region $REGION
    
    log_success "CloudFormation 스택 배포 완료"
}

# Lambda 함수 코드 업데이트
update_lambda_functions() {
    log_info "Lambda 함수 코드를 업데이트합니다..."
    
    # Lambda 함수 이름들
    LAMBDA_FUNCTIONS=(
        "youth-policy-lambda1-raw-data-ingest"
        "youth-policy-lambda2-data-preprocessing" 
        "youth-policy-lambda3-ml-classification"
        "youth-policy-lambda4-rds-storage"
    )
    
    # 각 Lambda 함수 업데이트
    for i in "${!LAMBDA_FUNCTIONS[@]}"; do
        FUNCTION_NAME="${LAMBDA_FUNCTIONS[$i]}"
        PACKAGE_FILE="packages/lambda$((i+1)).zip"
        
        log_info "Updating $FUNCTION_NAME..."
        
        aws lambda update-function-code \
            --function-name $FUNCTION_NAME \
            --zip-file fileb://$PACKAGE_FILE \
            --region $REGION
        
        # 함수 업데이트 완료 대기
        aws lambda wait function-updated \
            --function-name $FUNCTION_NAME \
            --region $REGION
    done
    
    log_success "모든 Lambda 함수 코드 업데이트 완료"
}

# Secrets Manager 시크릿 업데이트
update_secrets() {
    log_info "Secrets Manager 시크릿을 업데이트합니다..."
    
    # 시크릿 값 입력 받기
    echo "데이터베이스 및 API 설정을 입력하세요:"
    
    read -p "RDS Endpoint: " DB_HOST
    read -p "Database Name [youth_policy_db]: " DB_NAME
    DB_NAME=${DB_NAME:-youth_policy_db}
    
    read -p "Database User [postgres]: " DB_USER
    DB_USER=${DB_USER:-postgres}
    
    read -s -p "Database Password: " DB_PASSWORD
    echo
    
    read -p "OpenAI API Key (선택사항): " OPENAI_API_KEY
    read -p "Youth Policy API URL (선택사항): " YOUTH_POLICY_API_URL
    read -p "API Key (선택사항): " API_KEY
    
    # JSON 생성
    SECRET_JSON=$(cat <<EOF
{
  "DB_HOST": "$DB_HOST",
  "DB_PORT": "5432",
  "DB_NAME": "$DB_NAME",
  "DB_USER": "$DB_USER",
  "DB_PASSWORD": "$DB_PASSWORD",
  "OPENAI_API_KEY": "$OPENAI_API_KEY",
  "YOUTH_POLICY_API_URL": "$YOUTH_POLICY_API_URL",
  "API_KEY": "$API_KEY"
}
EOF
    )
    
    # 시크릿 업데이트
    aws secretsmanager update-secret \
        --secret-id $SECRET_NAME \
        --secret-string "$SECRET_JSON" \
        --region $REGION
    
    log_success "Secrets Manager 시크릿 업데이트 완료"
}

# 모델 파일 업로드
upload_models() {
    log_info "ML 모델 파일을 S3에 업로드합니다..."
    
    # 모델 파일들 확인
    MODEL_FILES=(
        "../data/simple_model.pkl"
        "../data/high_performance_model.pkl"
        "../data/test_model.pkl"
    )
    
    for MODEL_FILE in "${MODEL_FILES[@]}"; do
        if [ -f "$MODEL_FILE" ]; then
            BASENAME=$(basename "$MODEL_FILE")
            log_info "Uploading $BASENAME..."
            
            aws s3 cp "$MODEL_FILE" "s3://$BUCKET_NAME/models/$BASENAME" \
                --region $REGION
        else
            log_warning "Model file not found: $MODEL_FILE"
        fi
    done
    
    log_success "모델 파일 업로드 완료"
}

# 테스트 실행
run_tests() {
    log_info "파이프라인 테스트를 실행합니다..."
    
    # Lambda1 수동 실행 (테스트)
    log_info "Lambda1 테스트 실행..."
    aws lambda invoke \
        --function-name youth-policy-lambda1-raw-data-ingest \
        --payload '{"test": true}' \
        --region $REGION \
        /tmp/lambda1_output.json
    
    log_info "Lambda1 응답:"
    cat /tmp/lambda1_output.json
    echo
    
    log_success "테스트 완료"
}

# 배포 상태 확인
check_deployment() {
    log_info "배포 상태를 확인합니다..."
    
    # CloudFormation 스택 상태
    STACK_STATUS=$(aws cloudformation describe-stacks \
        --stack-name $STACK_NAME \
        --region $REGION \
        --query 'Stacks[0].StackStatus' \
        --output text)
    
    log_info "CloudFormation 스택 상태: $STACK_STATUS"
    
    # Lambda 함수들 상태
    LAMBDA_FUNCTIONS=(
        "youth-policy-lambda1-raw-data-ingest"
        "youth-policy-lambda2-data-preprocessing"
        "youth-policy-lambda3-ml-classification"
        "youth-policy-lambda4-rds-storage"
    )
    
    for FUNCTION_NAME in "${LAMBDA_FUNCTIONS[@]}"; do
        FUNCTION_STATUS=$(aws lambda get-function \
            --function-name $FUNCTION_NAME \
            --region $REGION \
            --query 'Configuration.State' \
            --output text)
        
        log_info "$FUNCTION_NAME 상태: $FUNCTION_STATUS"
    done
    
    # S3 버킷 확인
    if aws s3 ls "s3://$BUCKET_NAME" --region $REGION &> /dev/null; then
        log_success "S3 버킷이 정상적으로 생성되었습니다."
    else
        log_error "S3 버킷에 접근할 수 없습니다."
    fi
}

# 메인 함수
main() {
    echo "======================================"
    echo "Youth Policy Pipeline 배포 스크립트"
    echo "======================================"
    
    # 스크립트 디렉토리로 이동
    cd "$(dirname "$0")"
    
    load_config "$1"
    check_prerequisites
    
    # 사용자 확인
    echo
    log_warning "다음 설정으로 배포를 진행합니다:"
    echo "  - 스택 이름: $STACK_NAME"
    echo "  - 리전: $REGION"
    echo "  - S3 버킷: $BUCKET_NAME"
    echo
    read -p "계속 진행하시겠습니까? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "배포가 취소되었습니다."
        exit 0
    fi
    
    # 배포 단계별 실행
    package_lambda_functions
    deploy_infrastructure
    update_lambda_functions
    
    # 시크릿 업데이트 여부 확인
    echo
    read -p "Secrets Manager 시크릿을 업데이트하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        update_secrets
    fi
    
    # 모델 업로드 여부 확인
    echo
    read -p "ML 모델 파일을 업로드하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        upload_models
    fi
    
    # 테스트 실행 여부 확인
    echo
    read -p "테스트를 실행하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        run_tests
    fi
    
    check_deployment
    
    echo
    log_success "======================================"
    log_success "배포가 성공적으로 완료되었습니다!"
    log_success "======================================"
    
    echo
    echo "다음 명령어로 CloudWatch 로그를 확인할 수 있습니다:"
    echo "aws logs tail /aws/lambda/youth-policy-lambda1-raw-data-ingest --follow --region $REGION"
    
    echo
    echo "CloudWatch Events 스케줄이 설정되었습니다:"
    echo "- Lambda1은 매주 일요일 오전 2시 (KST)에 자동 실행됩니다."
    
    # 정리
    rm -rf packages
}

# 스크립트 실행
main "$@" 