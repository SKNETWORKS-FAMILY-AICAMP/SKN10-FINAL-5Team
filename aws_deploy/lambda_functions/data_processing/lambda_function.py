import json
import boto3
import pandas as pd
from datetime import datetime
import sys
import os

# 같은 디렉토리의 모듈들을 import
from preprocessing import main as preprocess_data
from insert_data_in_postgres import YouthPolicyDataInserter
from insert_condition import main as insert_condition_data

def lambda_handler(event, context):
    """
    S3에 저장된 청년정책 데이터를 전처리하고 PostgreSQL에 저장하는 Lambda 함수
    """
    try:
        # S3 클라이언트 초기화
        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_BUCKET_NAME']
        
        # 이벤트에서 S3 버킷과 키 정보 추출
        key = event['Records'][0]['s3']['object']['key']
        
        # S3에서 파일 다운로드
        local_file = '/tmp/raw_data.csv'
        s3_client.download_file(bucket_name, key, local_file)
        
        # 데이터 전처리
        preprocess_data()
        
        # 전처리된 데이터 파일 경로
        today_str = datetime.now().strftime('%Y-%m-%d')
        processed_file = f'/tmp/청년정책목록_전처리완료_{today_str}.csv'
        
        # PostgreSQL 연결 설정
        db_config = {
            'host': os.environ['DB_HOST'],
            'port': os.environ['DB_PORT'],
            'database': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD']
        }
        
        # 데이터 삽입
        inserter = YouthPolicyDataInserter(db_config)
        inserter.insert_all_data(processed_file)
        
        # 조건 데이터 삽입
        try:
            insert_condition_data()
            print("조건 데이터 삽입 완료")
        except Exception as condition_error:
            print(f"조건 데이터 삽입 중 오류 (계속 진행): {str(condition_error)}")
        
        # 처리된 파일을 S3의 processed/ 디렉토리에 업로드
        processed_key = f'processed/youth_policy_{today_str}.csv'
        s3_client.upload_file(processed_file, bucket_name, processed_key)
        
        return {
            'statusCode': 200,
            'body': json.dumps('Data processing completed successfully')
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        } 