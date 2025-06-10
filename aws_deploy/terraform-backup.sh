#!/bin/bash

# Terraform 백업 및 복원 스크립트
# 이 스크립트는 terraform.tfstate를 S3에 백업하고 복원하는 기능을 제공합니다.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$SCRIPT_DIR/terraform"
BACKUP_BUCKET="terraform-state-backup-$(date +%Y%m%d)"

# 색깔 출력을 위한 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 함수: 테라폼 상태 백업
backup_terraform_state() {
    print_status "테라폼 상태 백업을 시작합니다..."
    
    if [ ! -f "$TERRAFORM_DIR/terraform.tfstate" ]; then
        print_error "terraform.tfstate 파일이 존재하지 않습니다."
        exit 1
    fi
    
    # S3 버킷 생성 (이미 존재하면 무시)
    aws s3 mb s3://$BACKUP_BUCKET --region ap-northeast-2 2>/dev/null || true
    
    # 상태 파일 백업
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    aws s3 cp "$TERRAFORM_DIR/terraform.tfstate" "s3://$BACKUP_BUCKET/terraform.tfstate.$TIMESTAMP"
    aws s3 cp "$TERRAFORM_DIR/terraform.tfstate" "s3://$BACKUP_BUCKET/terraform.tfstate.latest"
    
    if [ -f "$TERRAFORM_DIR/terraform.tfstate.backup" ]; then
        aws s3 cp "$TERRAFORM_DIR/terraform.tfstate.backup" "s3://$BACKUP_BUCKET/terraform.tfstate.backup.$TIMESTAMP"
    fi
    
    print_status "백업 완료: s3://$BACKUP_BUCKET/"
    print_status "복원 명령: $0 restore"
}

# 함수: 테라폼 상태 복원
restore_terraform_state() {
    print_status "테라폼 상태 복원을 시작합니다..."
    
    # 최신 백업 파일 다운로드
    if aws s3 cp "s3://$BACKUP_BUCKET/terraform.tfstate.latest" "$TERRAFORM_DIR/terraform.tfstate"; then
        print_status "상태 파일 복원 완료"
        
        # Terraform 초기화
        cd "$TERRAFORM_DIR"
        terraform init
        
        # 상태 확인
        terraform show
        
        print_status "복원 완료. terraform plan을 실행하여 상태를 확인하세요."
    else
        print_error "백업 파일을 찾을 수 없습니다."
        print_warning "새로운 환경에서 시작하려면 다음을 실행하세요:"
        echo "  cd terraform && terraform init && terraform plan"
        exit 1
    fi
}

# 함수: 인프라 완전 재구성
rebuild_infrastructure() {
    print_warning "기존 인프라를 완전히 제거하고 재구성합니다."
    print_warning "이 작업은 되돌릴 수 없습니다. 계속하시겠습니까? (y/N)"
    
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        print_status "작업이 취소되었습니다."
        exit 0
    fi
    
    cd "$TERRAFORM_DIR"
    
    # 기존 인프라 제거
    print_status "기존 인프라 제거 중..."
    terraform destroy -auto-approve
    
    # 상태 파일 정리
    rm -f terraform.tfstate terraform.tfstate.backup
    rm -rf .terraform/
    
    # 새로운 인프라 구성
    print_status "새로운 인프라 구성 중..."
    terraform init
    terraform plan
    terraform apply -auto-approve
    
    print_status "인프라 재구성 완료"
}

# 함수: 원격 상태 저장소 설정
setup_remote_state() {
    print_status "원격 상태 저장소를 설정합니다..."
    
    # S3 버킷과 DynamoDB 테이블 생성
    STATE_BUCKET="terraform-state-$(openssl rand -hex 8)"
    
    cat > "$TERRAFORM_DIR/backend.tf" << EOF
terraform {
  backend "s3" {
    bucket         = "$STATE_BUCKET"
    key            = "terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
EOF
    
    # 백엔드 초기화
    cd "$TERRAFORM_DIR"
    terraform init -migrate-state
    
    print_status "원격 상태 저장소 설정 완료"
    print_status "이제 팀 멤버들과 안전하게 상태를 공유할 수 있습니다."
}

# 메인 스크립트
case "$1" in
    "backup")
        backup_terraform_state
        ;;
    "restore")
        restore_terraform_state
        ;;
    "rebuild")
        rebuild_infrastructure
        ;;
    "remote")
        setup_remote_state
        ;;
    *)
        echo "사용법: $0 {backup|restore|rebuild|remote}"
        echo ""
        echo "명령어:"
        echo "  backup  - 현재 terraform.tfstate를 S3에 백업"
        echo "  restore - S3에서 terraform.tfstate 복원"
        echo "  rebuild - 인프라 완전 재구성 (주의: 기존 데이터 삭제)"
        echo "  remote  - 원격 상태 저장소 설정 (팀 협업용)"
        echo ""
        echo "예시:"
        echo "  $0 backup   # 현재 상태 백업"
        echo "  $0 restore  # 백업에서 복원"
        exit 1
        ;;
esac 