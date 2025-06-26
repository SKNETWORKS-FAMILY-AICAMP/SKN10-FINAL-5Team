#!/usr/bin/env python3
"""
공통 S3 및 Secrets Manager 유틸리티
모든 Lambda 함수에서 공통으로 사용하는 기능들

작성일: 2025-01-28
수정일: 2025-01-28 - Secrets Manager 지원 추가
"""

import boto3
import pandas as pd
import io
from datetime import datetime
from typing import Optional, Dict, Any
import logging
import json
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SecretsManager:
    """Secrets Manager 접근 클래스"""
    
    def __init__(self, region_name: str = 'ap-northeast-2'):
        self.client = boto3.client('secretsmanager', region_name=region_name)
        self._cache = {}
    
    def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Secrets Manager에서 시크릿을 가져옵니다.
        
        Args:
            secret_name: 시크릿 이름
            
        Returns:
            시크릿 딕셔너리
        """
        if secret_name in self._cache:
            return self._cache[secret_name]
        
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_string = response['SecretString']
            secret_dict = json.loads(secret_string)
            
            # 캐시에 저장
            self._cache[secret_name] = secret_dict
            
            logger.info(f"Successfully retrieved secret: {secret_name}")
            return secret_dict
            
        except ClientError as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secret JSON {secret_name}: {str(e)}")
            raise


class S3Utils:
    """S3 유틸리티 클래스"""
    
    def __init__(self, bucket_name: str):
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name
    
    def get_partition_path(self, prefix: str) -> str:
        """
        현재 날짜 기준으로 파티션 경로 생성
        
        Args:
            prefix: 디렉터리 접두사 (예: 'raw', 'preprocessed')
            
        Returns:
            파티션 경로 (예: raw/year=2025/month=06/week=03/)
        """
        now = datetime.now()
        year = now.year
        month = now.month
        week_of_month = ((now.day - 1) // 7) + 1
        
        return f"{prefix}/year={year}/month={month:02d}/week={week_of_month:02d}/"
    
    def upload_dataframe_to_s3(self, 
                             df: pd.DataFrame, 
                             s3_key: str, 
                             bucket_name: Optional[str] = None) -> None:
        """
        DataFrame을 CSV로 S3에 업로드
        
        Args:
            df: 업로드할 DataFrame
            s3_key: S3 객체 키
            bucket_name: S3 버킷명 (기본값: self.bucket_name)
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("버킷명이 지정되지 않았습니다.")
        
        # DataFrame을 CSV로 변환
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        
        # S3에 업로드
        self.s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        
        logger.info(f"S3 업로드 완료: s3://{bucket}/{s3_key}")
    
    def download_dataframe_from_s3(self, 
                                 s3_key: str, 
                                 bucket_name: Optional[str] = None) -> pd.DataFrame:
        """
        S3에서 CSV를 DataFrame으로 다운로드
        
        Args:
            s3_key: S3 객체 키
            bucket_name: S3 버킷명 (기본값: self.bucket_name)
            
        Returns:
            로드된 DataFrame
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("버킷명이 지정되지 않았습니다.")
        
        # S3에서 객체 가져오기
        response = self.s3_client.get_object(Bucket=bucket, Key=s3_key)
        
        # CSV 데이터 읽기
        csv_content = response['Body'].read().decode('utf-8')
        df = pd.read_csv(io.StringIO(csv_content))
        
        logger.info(f"S3 다운로드 완료: s3://{bucket}/{s3_key}, {len(df)}개 레코드")
        return df
    
    def create_timestamped_key(self, partition_path: str, filename_prefix: str = 'data') -> str:
        """
        타임스탬프가 포함된 S3 키 생성
        
        Args:
            partition_path: 파티션 경로
            filename_prefix: 파일명 접두사
            
        Returns:
            타임스탬프가 포함된 S3 키
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{partition_path}{filename_prefix}_{timestamp}.csv"


def get_environment_variables(secret_name: Optional[str] = None) -> Dict[str, str]:
    """
    환경변수를 Secrets Manager 또는 Lambda 환경변수에서 가져옵니다.
    
    Args:
        secret_name: Secrets Manager 시크릿 이름 (None이면 Lambda 환경변수만 사용)
        
    Returns:
        환경변수 딕셔너리
    """
    import os
    
    env_vars = {}
    
    # Lambda 환경변수에서 기본값 가져오기
    lambda_env_vars = [
        'S3_BUCKET_NAME', 'SECRET_NAME', 'DATA_SOURCE', 'SOURCE_FILE_KEY',
        'MODEL_S3_KEY', 'POLICIES_TABLE', 'CLASSIFICATIONS_TABLE'
    ]
    
    for var in lambda_env_vars:
        value = os.environ.get(var)
        if value:
            env_vars[var] = value
    
    # Secrets Manager에서 민감한 정보 가져오기
    if secret_name:
        try:
            secrets_manager = SecretsManager()
            secrets = secrets_manager.get_secret(secret_name)
            
            # Secrets Manager의 값들을 환경변수에 추가
            env_vars.update(secrets)
            
            logger.info(f"Successfully loaded {len(secrets)} secrets from {secret_name}")
            
        except Exception as e:
            logger.warning(f"Failed to load secrets from {secret_name}: {str(e)}")
            logger.warning("Proceeding with Lambda environment variables only")
    
    return env_vars


def get_partition_path(date_format: str = 'week') -> str:
    """
    날짜 기반 파티션 경로 생성
    
    Args:
        date_format: 파티션 형식 ('week', 'month', 'day')
        
    Returns:
        파티션 경로
    """
    from datetime import datetime
    
    now = datetime.now()
    year = now.year
    month = now.month
    
    if date_format == 'week':
        # 월의 주차 계산
        week_of_month = ((now.day - 1) // 7) + 1
        return f"year={year}/month={month:02d}/week={week_of_month:02d}/"
    elif date_format == 'month':
        return f"year={year}/month={month:02d}/"
    elif date_format == 'day':
        day = now.day
        return f"year={year}/month={month:02d}/day={day:02d}/"
    else:
        raise ValueError(f"Unsupported date format: {date_format}")


# 편의 함수들
def create_s3_utils(bucket_name: str) -> S3Utils:
    """S3Utils 인스턴스 생성"""
    return S3Utils(bucket_name)


def create_secrets_manager(region_name: str = 'ap-northeast-2') -> SecretsManager:
    """SecretsManager 인스턴스 생성"""
    return SecretsManager(region_name) 