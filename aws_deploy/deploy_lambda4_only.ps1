# Lambda4 RDS Storage 개별 배포 스크립트 (PowerShell)
# 수정된 중복/삭제 관리 로직을 포함한 Lambda4만 업데이트

param(
    [string]$Region = "ap-northeast-2",
    [string]$FunctionName = "youth-policy-lambda4-rds-storage"
)

# Stop on error
$ErrorActionPreference = "Stop"

# Color functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking required tools..."
    
    # Check AWS CLI
    try {
        aws --version | Out-Null
        Write-Success "AWS CLI is installed."
    }
    catch {
        Write-Error "AWS CLI is not installed."
        exit 1
    }
    
    # Check AWS credentials
    try {
        aws sts get-caller-identity --no-cli-pager | Out-Null
        Write-Success "AWS credentials are configured."
    }
    catch {
        Write-Error "AWS credentials are not configured."
        exit 1
    }
    
    # Check if Lambda function exists
    try {
        aws lambda get-function --function-name $FunctionName --region $Region --no-cli-pager | Out-Null
        Write-Success "Lambda function found: $FunctionName"
    }
    catch {
        Write-Error "Lambda function not found: $FunctionName. Please deploy the full stack first."
        exit 1
    }
}

# Package Lambda4 function
function New-Lambda4Package {
    Write-Info "Packaging Lambda4 RDS Storage function..."
    
    # Create packages directory
    if (Test-Path "packages") {
        Remove-Item "packages" -Recurse -Force
    }
    New-Item -ItemType Directory -Path "packages" | Out-Null
    
    $zipFile = "packages\lambda4.zip"
    
    # Create temp directory
    $tempDir = "temp_lambda4"
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    
    # Copy Lambda4 function files
    Copy-Item "lambda_functions\lambda4_rds_storage\*" $tempDir -Recurse
    
    # Copy shared libraries if they exist
    if (Test-Path "lambda_functions\shared") {
        Copy-Item "lambda_functions\shared\*" $tempDir -Recurse
    }
    
    # Create ZIP file
    Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force
    
    # Remove temp directory
    Remove-Item $tempDir -Recurse -Force
    
    Write-Success "Lambda4 function packaged successfully: $zipFile"
    return $zipFile
}

# Update Lambda4 function code
function Update-Lambda4Function {
    param([string]$PackageFile)
    
    Write-Info "Updating Lambda4 function code..."
    
    # Update function code
    aws lambda update-function-code `
        --function-name $FunctionName `
        --zip-file "fileb://$PackageFile" `
        --region $Region `
        --no-cli-pager
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to update Lambda function code"
        exit 1
    }
    
    Write-Info "Waiting for function update to complete..."
    
    # Wait for function update completion
    aws lambda wait function-updated `
        --function-name $FunctionName `
        --region $Region
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Function update wait failed"
        exit 1
    }
    
    Write-Success "Lambda4 function code updated successfully"
}

# Check function status
function Test-Lambda4Status {
    Write-Info "Checking Lambda4 function status..."
    
    try {
        $functionInfo = aws lambda get-function `
            --function-name $FunctionName `
            --region $Region `
            --no-cli-pager | ConvertFrom-Json
        
        Write-Info "Function Name: $($functionInfo.Configuration.FunctionName)"
        Write-Info "Function State: $($functionInfo.Configuration.State)"
        Write-Info "Last Modified: $($functionInfo.Configuration.LastModified)"
        Write-Info "Runtime: $($functionInfo.Configuration.Runtime)"
        Write-Info "Memory Size: $($functionInfo.Configuration.MemorySize) MB"
        Write-Info "Timeout: $($functionInfo.Configuration.Timeout) seconds"
        
        if ($functionInfo.Configuration.State -eq "Active") {
            Write-Success "Lambda4 function is active and ready"
        }
        else {
            Write-Warning "Lambda4 function state: $($functionInfo.Configuration.State)"
        }
    }
    catch {
        Write-Error "Failed to get function status"
    }
}

# Main function
function Main {
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Lambda4 RDS Storage 개별 배포 스크립트" -ForegroundColor Cyan
    Write-Host "중복/삭제 관리 로직 업데이트" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Change to script directory
    Set-Location $PSScriptRoot
    
    Write-Info "Function Name: $FunctionName"
    Write-Info "Region: $Region"
    Write-Host ""
    
    # User confirmation
    Write-Warning "Lambda4 RDS Storage 함수를 업데이트하시겠습니까?"
    Write-Info "업데이트 내용:"
    Write-Info "- 중복 데이터 해시 기반 감지"
    Write-Info "- 삭제된 정책 자동 비활성화"
    Write-Info "- 데이터 변경 추적 개선"
    Write-Host ""
    
    $confirmation = Read-Host "배포를 계속하시겠습니까? (y/N)"
    
    if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
        Write-Info "배포가 취소되었습니다."
        return
    }
    
    try {
        # Execute deployment steps
        Test-Prerequisites
        $packageFile = New-Lambda4Package
        Update-Lambda4Function -PackageFile $packageFile
        Test-Lambda4Status
        
        Write-Host ""
        Write-Success "======================================"
        Write-Success "Lambda4 배포가 완료되었습니다!"
        Write-Success "======================================"
        
        Write-Host ""
        Write-Host "업데이트된 기능:" -ForegroundColor Yellow
        Write-Host "✅ 데이터 해시 기반 중복 감지" -ForegroundColor Green
        Write-Host "✅ 삭제된 정책 자동 비활성화" -ForegroundColor Green
        Write-Host "✅ 변경 추적 및 타임스탬프 관리" -ForegroundColor Green
        Write-Host "✅ 효율적인 배치 처리" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "실시간 로그 모니터링:" -ForegroundColor Yellow
        Write-Host "aws logs tail /aws/lambda/$FunctionName --follow --region $Region" -ForegroundColor White
    }
    catch {
        Write-Error "배포 중 오류 발생: $($_.Exception.Message)"
        throw
    }
    finally {
        # Cleanup
        if (Test-Path "packages") {
            Remove-Item "packages" -Recurse -Force
        }
    }
}

# Execute script
Main 