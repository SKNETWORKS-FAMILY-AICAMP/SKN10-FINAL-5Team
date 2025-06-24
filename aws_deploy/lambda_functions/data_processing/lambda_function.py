import json
import boto3
import pandas as pd
from datetime import datetime
import sys
import os
import logging

# 같은 디렉토리의 모듈들을 import
from preprocessing import main as preprocess_data
from insert_data_in_postgres import YouthPolicyDataInserter
from insert_condition import main as insert_condition_data

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    S3에 저장된 청년정책 데이터를 전처리하고 PostgreSQL에 저장하는 Lambda 함수
    - 수정일시 비교를 통한 조건부 업데이트 지원
    - 새로운 데이터는 추가, 수정된 데이터는 업데이트, 변경 없는 데이터는 스킵
    """
    try:
        logger.info("Lambda 함수 실행 시작")
        
        # S3 클라이언트 초기화
        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_BUCKET_NAME']
        
        # 이벤트에서 S3 버킷과 키 정보 추출
        if 'Records' not in event or not event['Records']:
            logger.error("S3 이벤트 레코드가 없습니다.")
            return {
                'statusCode': 400,
                'body': json.dumps('잘못된 이벤트 형식입니다.')
            }
        
        key = event['Records'][0]['s3']['object']['key']
        logger.info(f"처리할 S3 파일: s3://{bucket_name}/{key}")
        
        # S3에서 파일 다운로드
        local_file = '/tmp/raw_data.csv'
        try:
            s3_client.download_file(bucket_name, key, local_file)
            logger.info(f"S3 파일 다운로드 완료: {local_file}")
        except Exception as e:
            logger.error(f"S3 파일 다운로드 실패: {str(e)}")
            raise
        
        # 데이터 전처리
        try:
            logger.info("데이터 전처리 시작")
            preprocess_data()
            logger.info("데이터 전처리 완료")
        except Exception as e:
            logger.error(f"데이터 전처리 실패: {str(e)}")
            raise
        
        # 전처리된 데이터 파일 경로
        today_str = datetime.now().strftime('%Y-%m-%d')
        processed_file = f'/tmp/청년정책목록_전처리완료_{today_str}.csv'
        
        # 전처리된 파일 존재 확인
        if not os.path.exists(processed_file):
            logger.error(f"전처리된 파일이 존재하지 않습니다: {processed_file}")
            raise FileNotFoundError(f"전처리된 파일을 찾을 수 없습니다: {processed_file}")
        
        # PostgreSQL 연결 설정
        db_config = {
            'host': os.environ['DB_HOST'],
            'port': os.environ['DB_PORT'],
            'database': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD']
        }
        
        logger.info("PostgreSQL에 데이터 삽입/업데이트 시작")
        
        # OpenAI API 키 설정 (임베딩 생성용)
        openai_api_key = os.environ.get('OPENAI_API_KEY')
        if not openai_api_key:
            logger.warning("OpenAI API 키가 설정되지 않았습니다. 임베딩 생성이 건너뛰어집니다.")
        
        # 데이터 삽입/업데이트 (조건부 업데이트 로직 사용)
        try:
            inserter = YouthPolicyDataInserter(db_config, openai_api_key)
            inserter.insert_all_data(processed_file, include_embeddings=bool(openai_api_key))
            logger.info("정책 데이터 처리 완료")
        except Exception as e:
            logger.error(f"정책 데이터 처리 실패: {str(e)}")
            raise
        
        # 조건 데이터 삽입 (기존 로직 유지)
        try:
            logger.info("조건 데이터 삽입 시작")
            insert_condition_data()
            logger.info("조건 데이터 삽입 완료")
        except Exception as condition_error:
            logger.warning(f"조건 데이터 삽입 중 오류 (계속 진행): {str(condition_error)}")
        
        # 처리된 파일을 S3의 processed/ 디렉토리에 업로드
        try:
            processed_key = f'processed/youth_policy_{today_str}.csv'
            s3_client.upload_file(processed_file, bucket_name, processed_key)
            logger.info(f"처리된 파일 S3 업로드 완료: s3://{bucket_name}/{processed_key}")
        except Exception as e:
            logger.warning(f"S3 업로드 실패 (처리는 완료): {str(e)}")
        
        # 임시 파일 정리
        try:
            if os.path.exists(local_file):
                os.remove(local_file)
            if os.path.exists(processed_file):
                os.remove(processed_file)
            logger.info("임시 파일 정리 완료")
        except Exception as e:
            logger.warning(f"임시 파일 정리 실패: {str(e)}")
        
        logger.info("Lambda 함수 실행 완료")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data processing completed successfully',
                'processed_file': processed_key if 'processed_key' in locals() else None,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda 함수 실행 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Error: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        } 