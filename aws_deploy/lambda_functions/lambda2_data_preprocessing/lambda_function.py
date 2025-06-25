#!/usr/bin/env python3
"""
Lambda2: Data Preprocessing
S3의 원시 데이터를 전처리하여 preprocessed/ 디렉터리에 저장하는 Lambda 함수

기능:
- S3 raw/ 디렉터리에서 데이터 읽기
- 데이터 정제 및 전처리
- preprocessed/ 디렉터리에 날짜별로 파티션 저장
- preprocessed/year=2025/month=06/week=03/data.csv

작성일: 2025-01-28
"""

import json
import boto3
import pandas as pd
from datetime import datetime
import os
import logging
from typing import Dict, Any, List
import io
import re
from urllib.parse import unquote

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataPreprocessor:
    """데이터 전처리 클래스"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ['S3_BUCKET_NAME']
        
    def _get_partition_path(self) -> str:
        """
        현재 날짜 기준으로 파티션 경로 생성
        
        Returns:
            파티션 경로 (예: preprocessed/year=2025/month=06/week=03/)
        """
        now = datetime.now()
        year = now.year
        month = now.month
        week_of_month = ((now.day - 1) // 7) + 1
        
        return f"preprocessed/year={year}/month={month:02d}/week={week_of_month:02d}/"
    
    def load_raw_data_from_s3(self, s3_key: str) -> pd.DataFrame:
        """
        S3에서 원시 데이터 로드
        
        Args:
            s3_key: S3 객체 키
            
        Returns:
            로드된 DataFrame
        """
        logger.info(f"S3에서 원시 데이터 로드: s3://{self.bucket_name}/{s3_key}")
        
        try:
            # S3에서 객체 가져오기
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            
            # CSV 데이터 읽기
            csv_content = response['Body'].read().decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
            
            logger.info(f"원시 데이터 로드 완료: {len(df)}개 레코드")
            return df
            
        except Exception as e:
            logger.error(f"S3 데이터 로드 실패: {str(e)}")
            raise
    
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 전처리 수행
        
        Args:
            df: 원시 데이터 DataFrame
            
        Returns:
            전처리된 DataFrame
        """
        logger.info("데이터 전처리 시작")
        
        # 원본 DataFrame 복사
        processed_df = df.copy()
        
        # 1. 중복 제거
        initial_count = len(processed_df)
        processed_df = processed_df.drop_duplicates()
        logger.info(f"중복 제거: {initial_count} -> {len(processed_df)}개 레코드")
        
        # 2. 결측값 처리
        processed_df = self._handle_missing_values(processed_df)
        
        # 3. 텍스트 정제
        processed_df = self._clean_text_fields(processed_df)
        
        # 4. 데이터 타입 표준화
        processed_df = self._standardize_data_types(processed_df)
        
        # 5. 불필요한 컬럼 제거
        processed_df = self._remove_unnecessary_columns(processed_df)
        
        # 6. 데이터 검증
        processed_df = self._validate_data(processed_df)
        
        logger.info(f"데이터 전처리 완료: {len(processed_df)}개 레코드")
        
        return processed_df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        결측값 처리
        
        Args:
            df: 입력 DataFrame
            
        Returns:
            결측값이 처리된 DataFrame
        """
        logger.info("결측값 처리 중...")
        
        # 텍스트 컬럼들의 결측값을 빈 문자열로 대체
        text_columns = ['plcyNm', 'plcyExplnCn', 'plcySprtCn', 'plcyKywdNm']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].fillna('')
        
        # 필수 컬럼이 모두 비어있는 행 제거
        required_columns = ['plcyNm', 'plcyExplnCn']
        mask = df[required_columns].apply(lambda x: x.str.strip() == '', axis=1).all(axis=1)
        df = df[~mask]
        
        return df
    
    def _clean_text_fields(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        텍스트 필드 정제
        
        Args:
            df: 입력 DataFrame
            
        Returns:
            텍스트가 정제된 DataFrame
        """
        logger.info("텍스트 필드 정제 중...")
        
        text_columns = ['plcyNm', 'plcyExplnCn', 'plcySprtCn', 'plcyKywdNm']
        
        for col in text_columns:
            if col in df.columns:
                # HTML 태그 제거
                df[col] = df[col].astype(str).apply(self._remove_html_tags)
                
                # 특수 문자 정제
                df[col] = df[col].apply(self._clean_special_characters)
                
                # 연속된 공백 제거
                df[col] = df[col].apply(lambda x: re.sub(r'\s+', ' ', x).strip())
        
        return df
    
    def _remove_html_tags(self, text: str) -> str:
        """
        HTML 태그 제거
        
        Args:
            text: 입력 텍스트
            
        Returns:
            HTML 태그가 제거된 텍스트
        """
        if pd.isna(text) or text == '':
            return ''
        
        # HTML 태그 제거
        clean_text = re.sub(r'<[^>]+>', '', str(text))
        
        # HTML 엔티티 변환
        html_entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&nbsp;': ' '
        }
        
        for entity, char in html_entities.items():
            clean_text = clean_text.replace(entity, char)
        
        return clean_text
    
    def _clean_special_characters(self, text: str) -> str:
        """
        특수 문자 정제
        
        Args:
            text: 입력 텍스트
            
        Returns:
            특수 문자가 정제된 텍스트
        """
        if pd.isna(text) or text == '':
            return ''
        
        # 불필요한 특수 문자 제거 (한글, 영문, 숫자, 기본 구두점만 유지)
        clean_text = re.sub(r'[^\w\s\.,\-\(\)\[\]\/]', '', str(text))
        
        return clean_text
    
    def _standardize_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 타입 표준화
        
        Args:
            df: 입력 DataFrame
            
        Returns:
            데이터 타입이 표준화된 DataFrame
        """
        logger.info("데이터 타입 표준화 중...")
        
        # 날짜 컬럼 처리
        if 'lastUpdtDt' in df.columns:
            df['lastUpdtDt'] = pd.to_datetime(df['lastUpdtDt'], errors='coerce')
            df['lastUpdtDt'] = df['lastUpdtDt'].dt.strftime('%Y-%m-%d')
        
        # 문자열 컬럼들을 명시적으로 string 타입으로 변환
        string_columns = ['plcyId', 'plcyNm', 'plcyExplnCn', 'plcySprtCn', 'plcyKywdNm']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        return df
    
    def _remove_unnecessary_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        불필요한 컬럼 제거
        
        Args:
            df: 입력 DataFrame
            
        Returns:
            불필요한 컬럼이 제거된 DataFrame
        """
        # 필수 컬럼 정의
        required_columns = [
            'plcyId', 'plcyNm', 'plcyExplnCn', 'plcySprtCn', 'plcyKywdNm'
        ]
        
        # 옵션 컬럼들 (있으면 유지)
        optional_columns = ['lastUpdtDt', 'lclsfNm']
        
        # 유지할 컬럼들 결정
        columns_to_keep = []
        for col in required_columns:
            if col in df.columns:
                columns_to_keep.append(col)
        
        for col in optional_columns:
            if col in df.columns:
                columns_to_keep.append(col)
        
        # 컬럼 필터링
        df_filtered = df[columns_to_keep]
        
        logger.info(f"컬럼 필터링 완료: {len(columns_to_keep)}개 컬럼 유지")
        
        return df_filtered
    
    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 검증
        
        Args:
            df: 입력 DataFrame
            
        Returns:
            검증된 DataFrame
        """
        logger.info("데이터 검증 중...")
        
        # 필수 컬럼 존재 확인
        required_columns = ['plcyNm', 'plcyExplnCn']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"필수 컬럼이 누락되었습니다: {missing_columns}")
        
        # 빈 레코드 제거
        mask = df[required_columns].apply(lambda x: x.str.strip() != '', axis=1).any(axis=1)
        df = df[mask]
        
        # 최소 길이 검증 (정책명은 최소 2글자 이상)
        df = df[df['plcyNm'].str.len() >= 2]
        
        logger.info(f"데이터 검증 완료: {len(df)}개 유효한 레코드")
        
        return df
    
    def save_to_s3(self, df: pd.DataFrame) -> str:
        """
        전처리된 데이터를 S3에 저장
        
        Args:
            df: 저장할 DataFrame
            
        Returns:
            저장된 S3 키
        """
        partition_path = self._get_partition_path()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f"{partition_path}data_{timestamp}.csv"
        
        # DataFrame을 CSV로 변환
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        
        # S3에 업로드
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=csv_buffer.getvalue(),
            ContentType='text/csv'
        )
        
        logger.info(f"전처리된 데이터 S3 저장 완료: s3://{self.bucket_name}/{s3_key}")
        return s3_key


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 메인 핸들러 (S3 이벤트 트리거)
    
    Args:
        event: S3 이벤트
        context: Lambda 컨텍스트
        
    Returns:
        응답 딕셔너리
    """
    try:
        logger.info("Lambda2 (Data Preprocessing) 실행 시작")
        
        # S3 이벤트에서 버킷과 키 정보 추출
        if 'Records' not in event or not event['Records']:
            logger.error("S3 이벤트 레코드가 없습니다.")
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid S3 event format')
            }
        
        record = event['Records'][0]
        bucket_name = record['s3']['bucket']['name']
        s3_key = unquote(record['s3']['object']['key'])
        
        # raw/ 디렉터리의 파일만 처리
        if not s3_key.startswith('raw/'):
            logger.info(f"raw/ 디렉터리가 아닌 파일 건너뛰기: {s3_key}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'File not in raw directory, skipped',
                    'file': s3_key
                })
            }
        
        logger.info(f"처리할 S3 파일: s3://{bucket_name}/{s3_key}")
        
        # 데이터 전처리기 초기화
        preprocessor = DataPreprocessor()
        
        # 원시 데이터 로드
        raw_data = preprocessor.load_raw_data_from_s3(s3_key)
        
        if raw_data.empty:
            logger.warning("로드된 데이터가 없습니다.")
            return {
                'statusCode': 204,
                'body': json.dumps({
                    'message': 'No data to process',
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        # 데이터 전처리
        processed_data = preprocessor.preprocess_data(raw_data)
        
        if processed_data.empty:
            logger.warning("전처리 후 데이터가 없습니다.")
            return {
                'statusCode': 204,
                'body': json.dumps({
                    'message': 'No data after preprocessing',
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        # S3에 저장
        output_s3_key = preprocessor.save_to_s3(processed_data)
        
        logger.info(f"Lambda2 실행 완료. {len(processed_data)}개 레코드 처리")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Data preprocessing completed successfully',
                'input_records': len(raw_data),
                'output_records': len(processed_data),
                'input_s3_key': s3_key,
                'output_s3_key': output_s3_key,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda2 실행 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Data preprocessing failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        }


if __name__ == "__main__":
    # 로컬 테스트용
    test_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': 'raw/year=2025/month=01/week=04/data_20250128_120000.csv'}
            }
        }]
    }
    test_context = None
    result = lambda_handler(test_event, test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False)) 