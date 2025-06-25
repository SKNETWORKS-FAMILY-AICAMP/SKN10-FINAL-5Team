#!/usr/bin/env pwsh

# Youth Policy ML Pipeline - Complete Deployment Script
# This script deploys the complete ML pipeline with Lambda Layer to AWS

param(
    [string]$Region = "ap-northeast-2",
    [string]$StackName = "youth-policy-ml-pipeline",
    [string]$BucketName = "youth-policy-data-bucket-$(Get-Random)",
    [string]$SecretName = "youth-policy-secrets"
)

Write-Host "🚀 Starting Complete ML Pipeline Deployment..." -ForegroundColor Green
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host "Stack Name: $StackName" -ForegroundColor Cyan
Write-Host "Bucket Name: $BucketName" -ForegroundColor Cyan

# 1. Create S3 bucket first
Write-Host "📦 Creating S3 bucket..." -ForegroundColor Yellow
try {
    aws s3 mb s3://$BucketName --region $Region
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Bucket might already exist, continuing..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Bucket creation warning: $_" -ForegroundColor Yellow
}

# 2. Upload ML Layer
Write-Host "📤 Uploading ML Layer..." -ForegroundColor Yellow
aws s3 cp ml_complete_layer.zip s3://$BucketName/layers/ml_complete_layer.zip --region $Region
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to upload ML Layer" -ForegroundColor Red
    exit 1
}

# 3. Upload Lambda functions
Write-Host "📤 Uploading Lambda functions..." -ForegroundColor Yellow
aws s3 cp lambda-packages/lambda1_raw_data_ingest.zip s3://$BucketName/lambda-code/lambda1_raw_data_ingest.zip --region $Region
aws s3 cp lambda-packages/lambda2_data_preprocessing.zip s3://$BucketName/lambda-code/lambda2_data_preprocessing.zip --region $Region
aws s3 cp lambda-packages/lambda3_ml_classification.zip s3://$BucketName/lambda-code/lambda3_ml_classification.zip --region $Region
aws s3 cp lambda-packages/lambda4_rds_storage.zip s3://$BucketName/lambda-code/lambda4_rds_storage.zip --region $Region

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to upload Lambda functions" -ForegroundColor Red
    exit 1
}

# 4. Upload ML model
Write-Host "📤 Uploading ML model..." -ForegroundColor Yellow
if (Test-Path "../data/high_performance_model.pkl") {
    aws s3 cp ../data/high_performance_model.pkl s3://$BucketName/models/high_performance_model.pkl --region $Region
} else {
    Write-Host "⚠️  ML model not found, will need to be uploaded separately" -ForegroundColor Yellow
}

# 5. Deploy CloudFormation stack
Write-Host "☁️  Deploying CloudFormation stack..." -ForegroundColor Yellow
aws cloudformation deploy `
    --template-file cloudformation_simple.yaml `
    --stack-name $StackName `
    --region $Region `
    --capabilities CAPABILITY_IAM `
    --parameter-overrides `
        BucketName=$BucketName `
        SecretName=$SecretName

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ CloudFormation deployment failed" -ForegroundColor Red
    exit 1
}

# 6. Get stack outputs
Write-Host "📋 Getting stack outputs..." -ForegroundColor Yellow
$outputs = aws cloudformation describe-stacks --stack-name $StackName --region $Region --query 'Stacks[0].Outputs' --output json | ConvertFrom-Json

Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Stack Outputs:" -ForegroundColor Cyan
foreach ($output in $outputs) {
    Write-Host "  $($output.OutputKey): $($output.OutputValue)" -ForegroundColor White
}

# 7. Test the pipeline
Write-Host ""
Write-Host "🧪 Testing the pipeline..." -ForegroundColor Yellow

# Test Lambda1 (Raw Data Ingestion)
Write-Host "Testing Lambda1 (Raw Data Ingestion)..." -ForegroundColor Cyan
$lambda1Result = aws lambda invoke `
    --function-name youth-policy-lambda1-raw-data-ingest `
    --region $Region `
    --payload '{"test": true}' `
    --output json `
    lambda1_test_output.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Lambda1 test successful" -ForegroundColor Green
    $response = Get-Content lambda1_test_output.json | ConvertFrom-Json
    Write-Host "Response: $($response | ConvertTo-Json -Compress)" -ForegroundColor White
} else {
    Write-Host "❌ Lambda1 test failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 Complete ML Pipeline Deployment Summary:" -ForegroundColor Green
Write-Host "  ✅ S3 Bucket: $BucketName" -ForegroundColor White
Write-Host "  ✅ ML Layer: Uploaded (122MB with scikit-learn, pandas, numpy, scipy, psycopg2)" -ForegroundColor White
Write-Host "  ✅ Lambda Functions: 4 functions deployed" -ForegroundColor White
Write-Host "  ✅ CloudFormation Stack: $StackName" -ForegroundColor White
Write-Host "  ✅ Scheduled Execution: Weekly on Saturday 5:00 PM KST" -ForegroundColor White
Write-Host ""
Write-Host "🔗 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Configure Secrets Manager with database credentials" -ForegroundColor White
Write-Host "  2. Test individual Lambda functions" -ForegroundColor White
Write-Host "  3. Monitor CloudWatch logs" -ForegroundColor White
Write-Host "  4. Set up CloudWatch alarms" -ForegroundColor White 