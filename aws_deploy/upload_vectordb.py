#!/usr/bin/env python3
"""
Vector DB를 S3에 업로드하는 스크립트
"""

import os
import boto3
from botocore.exceptions import ClientError
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upload_directory_to_s3(local_directory, bucket_name, s3_prefix):
    """디렉토리 전체를 S3에 업로드"""
    s3_client = boto3.client('s3')
    
    for root, dirs, files in os.walk(local_directory):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_directory)
            s3_path = os.path.join(s3_prefix, relative_path).replace('\\', '/')
            
            try:
                logger.info(f"업로드 중: {local_path} -> s3://{bucket_name}/{s3_path}")
                s3_client.upload_file(local_path, bucket_name, s3_path)
                logger.info(f"업로드 완료: {s3_path}")
            except ClientError as e:
                logger.error(f"업로드 실패 {local_path}: {e}")
                return False
    
    return True

def main():
    # 설정
    VECTOR_DB_PATH = "../data/vector_db_openai_large_combined"
    BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'youth-policy-vectordb')
    S3_PREFIX = "vector_db_openai_large_combined"
    
    # Vector DB 디렉토리 확인
    if not os.path.exists(VECTOR_DB_PATH):
        logger.error(f"Vector DB 디렉토리를 찾을 수 없습니다: {VECTOR_DB_PATH}")
        return False
    
    # S3 클라이언트 생성
    try:
        s3_client = boto3.client('s3')
        # 버킷 존재 확인
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        logger.info(f"S3 버킷 확인됨: {BUCKET_NAME}")
    except ClientError as e:
        logger.error(f"S3 버킷 접근 실패 {BUCKET_NAME}: {e}")
        return False
    
    # Vector DB 업로드
    logger.info(f"Vector DB 업로드 시작: {VECTOR_DB_PATH} -> s3://{BUCKET_NAME}/{S3_PREFIX}")
    
    success = upload_directory_to_s3(VECTOR_DB_PATH, BUCKET_NAME, S3_PREFIX)
    
    if success:
        logger.info("Vector DB 업로드 완료!")
        return True
    else:
        logger.error("Vector DB 업로드 실패!")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 