# Youth Policy Data Processing Pipeline Deployment Script (PowerShell)
# Deploy 4 Lambda functions, S3, and Secrets Manager

param(
    [string]$StackName = "youth-policy-pipeline",
    [string]$Region = "ap-northeast-2",
    [string]$SecretName = "youth-policy-api-db-password"
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
        aws sts get-caller-identity | Out-Null
        Write-Success "AWS credentials are configured."
    }
    catch {
        Write-Error "AWS credentials are not configured."
        exit 1
    }
}

# Package Lambda functions
function New-LambdaPackages {
    Write-Info "Packaging Lambda functions..."
    
    # Create packages directory
    if (Test-Path "packages") {
        Remove-Item "packages" -Recurse -Force
    }
    New-Item -ItemType Directory -Path "packages" | Out-Null
    
    # Package Lambda functions
    $lambdaFunctions = @(
        "lambda1_raw_data_ingest",
        "lambda2_data_preprocessing", 
        "lambda3_ml_classification",
        "lambda4_rds_storage"
    )
    
    for ($i = 0; $i -lt $lambdaFunctions.Length; $i++) {
        $funcDir = $lambdaFunctions[$i]
        $zipFile = "packages\lambda$($i+1).zip"
        
        Write-Info "Packaging Lambda$($i+1)..."
        
        # Create temp directory
        $tempDir = "temp_lambda$($i+1)"
        if (Test-Path $tempDir) {
            Remove-Item $tempDir -Recurse -Force
        }
        New-Item -ItemType Directory -Path $tempDir | Out-Null
        
        # Copy function files
        Copy-Item "lambda_functions\$funcDir\*" $tempDir -Recurse
        
        # Copy shared libraries
        Copy-Item "lambda_functions\shared\*" $tempDir -Recurse
        
        # Create ZIP file
        Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force
        
        # Remove temp directory
        Remove-Item $tempDir -Recurse -Force
    }
    
    Write-Success "All Lambda functions packaged successfully"
}

# Deploy CloudFormation stack
function Deploy-Infrastructure {
    Write-Info "Deploying CloudFormation stack..."
    
    $bucketName = "youth-policy-data-bucket-$(Get-Date -Format 'yyyyMMddHHmmss')"
    
    # Check if stack exists
    try {
        $stackInfo = aws cloudformation describe-stacks --stack-name $StackName --region $Region 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Updating existing stack..."
            $operation = "update-stack"
        }
        else {
            Write-Info "Creating new stack..."
            $operation = "create-stack"
        }
    }
    catch {
        Write-Info "Creating new stack..."
        $operation = "create-stack"
    }
    
    # Deploy CloudFormation
    Write-Info "Executing CloudFormation $operation..."
    aws cloudformation $operation `
        --stack-name $StackName `
        --template-body "file://cloudformation.yaml" `
        --parameters "ParameterKey=SecretName,ParameterValue=$SecretName" "ParameterKey=BucketName,ParameterValue=$bucketName" `
        --capabilities CAPABILITY_IAM `
        --region $Region
    
    # Wait for deployment completion
    Write-Info "Waiting for CloudFormation stack deployment..."
    $waitCommand = if ($operation -eq "create-stack") { "stack-create-complete" } else { "stack-update-complete" }
    aws cloudformation wait $waitCommand --stack-name $StackName --region $Region
    
    Write-Success "CloudFormation stack deployment completed"
    
    # Return S3 bucket name
    return $bucketName
}

# Update Lambda function code
function Update-LambdaFunctions {
    Write-Info "Updating Lambda function code..."
    
    $lambdaFunctionNames = @(
        "youth-policy-lambda1-raw-data-ingest",
        "youth-policy-lambda2-data-preprocessing",
        "youth-policy-lambda3-ml-classification",
        "youth-policy-lambda4-rds-storage"
    )
    
    for ($i = 0; $i -lt $lambdaFunctionNames.Length; $i++) {
        $functionName = $lambdaFunctionNames[$i]
        $packageFile = "packages\lambda$($i+1).zip"
        
        Write-Info "Updating $functionName..."
        
        aws lambda update-function-code `
            --function-name $functionName `
            --zip-file "fileb://$packageFile" `
            --region $Region
        
        # Wait for function update completion
        aws lambda wait function-updated `
            --function-name $functionName `
            --region $Region
    }
    
    Write-Success "All Lambda function code updates completed"
}

# Check existing Secrets Manager secrets
function Update-Secrets {
    Write-Info "Checking existing Secrets Manager secrets..."
    
    try {
        # Check if secret exists and can be accessed
        $secretValue = aws secretsmanager get-secret-value `
            --secret-id $SecretName `
            --region $Region `
            --query 'SecretString' `
            --output text
        
        if ($secretValue) {
            Write-Success "Existing secret '$SecretName' found and accessible"
            Write-Info "Using existing secret configuration for Lambda functions"
        }
    }
    catch {
        Write-Warning "Could not access existing secret '$SecretName'"
        Write-Info "Lambda functions will attempt to use the existing secret anyway"
    }
    
    Write-Success "Secrets Manager check completed"
}

# Upload model files
function Update-Models {
    param([string]$BucketName)
    
    Write-Info "Uploading ML model files to S3..."
    
    $modelFiles = @(
        "..\data\simple_model.pkl",
        "..\data\high_performance_model.pkl",
        "..\data\test_model.pkl"
    )
    
    foreach ($modelFile in $modelFiles) {
        if (Test-Path $modelFile) {
            $fileName = Split-Path $modelFile -Leaf
            Write-Info "Uploading $fileName..."
            
            aws s3 cp $modelFile "s3://$BucketName/models/$fileName" --region $Region
        }
        else {
            Write-Warning "Model file not found: $modelFile"
        }
    }
    
    Write-Success "Model file upload completed"
}

# Run tests
function Invoke-Tests {
    Write-Info "Running pipeline tests..."
    
    # Manual Lambda1 execution
    Write-Info "Running Lambda1 test..."
    $payload = '{"test": true}'
    aws lambda invoke `
        --function-name "youth-policy-lambda1-raw-data-ingest" `
        --payload $payload `
        --region $Region `
        lambda1_output.json
    
    Write-Info "Lambda1 response:"
    Get-Content lambda1_output.json
    
    Write-Success "Tests completed"
}

# Check deployment status
function Test-Deployment {
    Write-Info "Checking deployment status..."
    
    # CloudFormation stack status
    $stackStatus = aws cloudformation describe-stacks `
        --stack-name $StackName `
        --region $Region `
        --query 'Stacks[0].StackStatus' `
        --output text
    
    Write-Info "CloudFormation stack status: $stackStatus"
    
    # Lambda function statuses
    $lambdaFunctions = @(
        "youth-policy-lambda1-raw-data-ingest",
        "youth-policy-lambda2-data-preprocessing",
        "youth-policy-lambda3-ml-classification",
        "youth-policy-lambda4-rds-storage"
    )
    
    foreach ($functionName in $lambdaFunctions) {
        try {
            $functionStatus = aws lambda get-function `
                --function-name $functionName `
                --region $Region `
                --query 'Configuration.State' `
                --output text
            
            Write-Info "$functionName status: $functionStatus"
        }
        catch {
            Write-Warning "Failed to check status for $functionName"
        }
    }
    
    Write-Success "Deployment status check completed"
}

# Main function
function Main {
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host "Youth Policy Pipeline Deployment Script" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Change to script directory
    Set-Location $PSScriptRoot
    
    Write-Info "Stack Name: $StackName"
    Write-Info "Region: $Region"
    Write-Info "Secret Name: $SecretName"
    Write-Host ""
    
    # User confirmation
    Write-Warning "Do you want to proceed with deployment using the above settings?"
    $confirmation = Read-Host "Continue deployment? (y/N)"
    
    if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
        Write-Info "Deployment cancelled."
        return
    }
    
    try {
        # Execute deployment steps
        Test-Prerequisites
        New-LambdaPackages
        $bucketName = Deploy-Infrastructure
        Update-LambdaFunctions
        
        # Check if secrets should be updated
        Write-Host ""
        $updateSecrets = Read-Host "Do you want to update Secrets Manager secrets? (y/N)"
        if ($updateSecrets -eq 'y' -or $updateSecrets -eq 'Y') {
            Update-Secrets
        }
        
        # Check if models should be uploaded
        Write-Host ""
        $uploadModels = Read-Host "Do you want to upload ML model files? (y/N)"
        if ($uploadModels -eq 'y' -or $uploadModels -eq 'Y') {
            Update-Models -BucketName $bucketName
        }
        
        # Check if tests should be run
        Write-Host ""
        $runTests = Read-Host "Do you want to run tests? (y/N)"
        if ($runTests -eq 'y' -or $runTests -eq 'Y') {
            Invoke-Tests
        }
        
        Test-Deployment
        
        Write-Host ""
        Write-Success "======================================"
        Write-Success "Deployment completed successfully!"
        Write-Success "======================================"
        
        Write-Host ""
        Write-Host "You can check CloudWatch logs with the following command:" -ForegroundColor Yellow
        Write-Host "aws logs tail /aws/lambda/youth-policy-lambda1-raw-data-ingest --follow --region $Region" -ForegroundColor White
        
        Write-Host ""
        Write-Host "CloudWatch Events schedule has been configured:" -ForegroundColor Yellow
        Write-Host "- Lambda1 will run automatically every Sunday at 2 AM (KST)." -ForegroundColor White
    }
    catch {
        Write-Error "Error occurred during deployment: $($_.Exception.Message)"
        throw
    }
    finally {
        # Cleanup
        if (Test-Path "packages") {
            Remove-Item "packages" -Recurse -Force
        }
        if (Test-Path "lambda1_output.json") {
            Remove-Item "lambda1_output.json" -Force
        }
    }
}

# Execute script
Main 