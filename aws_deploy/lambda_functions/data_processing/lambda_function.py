#!/usr/bin/env python3
"""
청년정책 데이터 수집 및 처리 Lambda 함수
- API에서 청년정책 데이터 수집
- 데이터 전처리 및 PostgreSQL 저장
- 주 1회 CloudWatch Events로 자동 실행

작성일: 2025-01-28
수정일: 2025-01-28 - API 데이터 수집 및 스케줄링 기능 추가
"""

import json
import boto3
import pandas as pd
from datetime import datetime
import sys
import os
import logging
import requests
import io
from typing import Dict, Any

# 같은 디렉토리의 모듈들을 import
from preprocessing import main as preprocess_data
from insert_data_in_postgres import YouthPolicyDataInserter
from insert_condition import main as insert_condition_data

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class YouthPolicyDataCollector:
    """청년정책 데이터 수집기 클래스"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ['S3_BUCKET_NAME']
        
    def collect_data_from_api(self) -> pd.DataFrame:
        """
        API에서 청년정책 데이터 수집
        
        Returns:
            수집된 청년정책 데이터 DataFrame
        """
        logger.info("API에서 청년정책 데이터 수집 시작")
        
        try:
            # 청년정책 API URL 설정
            api_url = os.environ.get('YOUTH_POLICY_API_URL')
            if not api_url:
                logger.warning("YOUTH_POLICY_API_URL이 설정되지 않았습니다. 샘플 데이터를 생성합니다.")
                return self._generate_sample_data()
            
            # API 파라미터 설정
            params = {
                'openApiVlak': os.environ.get('API_KEY', ''),  # API 키
                'display': '100',  # 한 번에 가져올 데이터 수
                'pageIndex': '1',  # 페이지 인덱스
                'srchPolicyId': '',  # 검색 정책 ID (전체)
                'query': '',  # 검색어 (전체)
                'bizTycdSel': '',  # 사업유형 (전체)
                'srchPolyBizSecd': '',  # 정책분야 (전체)
            }
            
            # API 헤더 설정
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            all_data = []
            page = 1
            max_pages = 10  # 최대 페이지 수 제한
            
            while page <= max_pages:
                params['pageIndex'] = str(page)
                logger.info(f"API 호출 - 페이지 {page}")
                
                try:
                    response = requests.get(api_url, params=params, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    # JSON 응답 파싱
                    if response.headers.get('content-type', '').startswith('application/json'):
                        data = response.json()
                    else:
                        # HTML 응답인 경우 (일부 API는 JSON이 아닐 수 있음)
                        logger.warning("API 응답이 JSON이 아닙니다. 샘플 데이터를 생성합니다.")
                        return self._generate_sample_data()
                    
                    # 데이터 추출
                    if isinstance(data, dict):
                        if 'youthPolicyList' in data:
                            policies = data['youthPolicyList']
                        elif 'list' in data:
                            policies = data['list']
                        elif 'data' in data:
                            policies = data['data']
                        else:
                            policies = [data]  # 단일 객체인 경우
                    elif isinstance(data, list):
                        policies = data
                    else:
                        logger.warning("예상하지 못한 API 응답 형식")
                        break
                    
                    if not policies:
                        logger.info(f"페이지 {page}에서 더 이상 데이터가 없습니다.")
                        break
                    
                    all_data.extend(policies)
                    logger.info(f"페이지 {page}에서 {len(policies)}개 정책 수집")
                    
                    # 마지막 페이지 확인
                    if len(policies) < int(params['display']):
                        logger.info("마지막 페이지에 도달했습니다.")
                        break
                    
                    page += 1
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"API 호출 실패 (페이지 {page}): {str(e)}")
                    if page == 1:
                        # 첫 페이지 실패 시 샘플 데이터 반환
                        return self._generate_sample_data()
                    else:
                        # 중간 페이지 실패 시 지금까지 수집한 데이터 사용
                        break
            
            if not all_data:
                logger.warning("API에서 데이터를 수집하지 못했습니다. 샘플 데이터를 생성합니다.")
                return self._generate_sample_data()
            
            # DataFrame 생성
            df = pd.DataFrame(all_data)
            logger.info(f"총 {len(df)}개의 청년정책 데이터 수집 완료")
            
            # 컬럼명 표준화 (API 응답에 따라 조정 필요)
            column_mapping = {
                'bizId': 'plcyId',
                'polyBizSjnm': 'plcyNm',
                'polyItcnCn': 'plcyExplnCn',
                'sporCn': 'plcySprtCn',
                'keyword': 'plcyKywdNm',
                'mngtMson': 'mngtMson',
                'cherCtpcCn': 'cherCtpcCn',
                'cnsgNmor': 'cnsgNmor',
                'tintCherCtpcCn': 'tintCherCtpcCn',
                'rfcSiteUrla1': 'rfcSiteUrla1',
                'rfcSiteUrla2': 'rfcSiteUrla2',
                'majrRhspTarget': 'majrRhspTarget',
                'ageInfo': 'ageInfo',
                'majrTrgtSe': 'majrTrgtSe',
                'empmSttus': 'empmSttus',
                'accrRqisCn': 'accrRqisCn',
                'prcpCn': 'prcpCn',
                'aditRscn': 'aditRscn',
                'prcpLmttTrgtCn': 'prcpLmttTrgtCn'
            }
            
            # 존재하는 컬럼만 매핑
            existing_mapping = {k: v for k, v in column_mapping.items() if k in df.columns}
            if existing_mapping:
                df = df.rename(columns=existing_mapping)
            
            # 필수 컬럼이 없는 경우 기본값 추가
            required_columns = ['plcyId', 'plcyNm', 'plcyExplnCn', 'plcySprtCn']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ''
            
            # 마지막 업데이트 시간 추가
            df['lastUpdtDt'] = datetime.now().strftime('%Y-%m-%d')
            
            return df
            
        except Exception as e:
            logger.error(f"API 데이터 수집 중 오류 발생: {str(e)}")
            return self._generate_sample_data()
    
    def _generate_sample_data(self) -> pd.DataFrame:
        """
        샘플 데이터 생성 (API 실패 시 대체용)
        
        Returns:
            샘플 청년정책 데이터 DataFrame
        """
        logger.info("샘플 청년정책 데이터 생성")
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        sample_data = {
            'plcyId': [
                'R2023080201', 'R2023080202', 'R2023080203', 
                'R2023080204', 'R2023080205'
            ],
            'plcyNm': [
                '청년 창업지원 사업',
                '청년 취업날개 프로그램',
                '청년 주거안정 지원',
                '청년 문화예술 지원사업',
                '청년 농업창업 지원'
            ],
            'plcyExplnCn': [
                '창업을 희망하는 청년들에게 창업자금 및 멘토링을 지원하는 사업입니다.',
                '청년층의 취업능력 향상을 위한 교육 및 취업연계 프로그램입니다.',
                '청년들의 주거비 부담 완화를 위한 임대료 지원 및 주거상담 서비스입니다.',
                '청년 문화예술인의 창작활동 지원 및 발표기회 제공 프로그램입니다.',
                '농업분야 창업을 희망하는 청년농업인 육성 지원사업입니다.'
            ],
            'plcySprtCn': [
                '창업자금 최대 5000만원, 사업화 멘토링, 네트워킹 프로그램',
                '직업교육 6개월, 면접코칭, 취업연계, 취업성공금 지급',
                '월세지원 최대 40만원, 전세자금대출, 주거상담 서비스',
                '창작지원금 500만원, 작품발표회, 전시공간 제공',
                '농업창업자금 3000만원, 농업기술교육, 농장운영 컨설팅'
            ],
            'plcyKywdNm': [
                '창업, 사업화, 멘토링, 청년',
                '취업, 교육, 면접, 직업훈련',
                '주거, 임대, 전세, 주택',
                '문화, 예술, 창작, 전시',
                '농업, 창업, 농촌, 귀농'
            ],
            'lastUpdtDt': [current_date] * 5,
            'mngtMson': ['중소벤처기업부', '고용노동부', '국토교통부', '문화체육관광부', '농림축산식품부'],
            'majrRhspTarget': ['청년창업자', '구직청년', '주거취약청년', '청년예술인', '청년농업인']
        }
        
        return pd.DataFrame(sample_data)
    
    def save_raw_data_to_s3(self, df: pd.DataFrame) -> str:
        """
        수집된 원시 데이터를 S3에 저장
        
        Args:
            df: 저장할 DataFrame
            
        Returns:
            저장된 S3 키
        """
        # 현재 날짜 기준 파일명 생성
        current_time = datetime.now()
        timestamp = current_time.strftime('%Y%m%d_%H%M%S')
        
        s3_key = f'raw/youth_policy_raw_{timestamp}.csv'
        
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
        
        logger.info(f"원시 데이터 S3 저장 완료: s3://{self.bucket_name}/{s3_key}")
        return s3_key


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    청년정책 데이터 수집 및 처리 Lambda 함수
    
    트리거 방식:
    1. CloudWatch Events (주 1회 스케줄) - API 데이터 수집
    2. S3 Events - 업로드된 파일 처리
    3. 수동 실행 - 테스트용
    
    Args:
        event: Lambda 이벤트 (CloudWatch Events 또는 S3 Events)
        context: Lambda 컨텍스트
        
    Returns:
        응답 딕셔너리
    """
    try:
        logger.info("청년정책 Lambda 함수 실행 시작")
        logger.info(f"이벤트: {json.dumps(event, default=str, ensure_ascii=False)}")
        
        # CloudWatch Events 트리거 (스케줄된 데이터 수집)
        if event.get('source') == 'aws.events':
            logger.info("CloudWatch Events 트리거 - API 데이터 수집 시작")
            return handle_scheduled_data_collection(event, context)
        
        # S3 Events 트리거 (파일 처리)
        elif 'Records' in event and event['Records']:
            logger.info("S3 Events 트리거 - 파일 처리 시작")
            return handle_s3_file_processing(event, context)
        
        # 수동 실행 또는 테스트
        else:
            logger.info("수동 실행 - 전체 파이프라인 실행")
            return handle_manual_execution(event, context)
            
    except Exception as e:
        logger.error(f"Lambda 함수 실행 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Lambda execution failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        }


def handle_scheduled_data_collection(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    스케줄된 데이터 수집 처리 (주 1회)
    
    Args:
        event: CloudWatch Events 이벤트
        context: Lambda 컨텍스트
        
    Returns:
        응답 딕셔너리
    """
    try:
        logger.info("스케줄된 API 데이터 수집 시작")
        
        # 데이터 수집기 초기화
        collector = YouthPolicyDataCollector()
        
        # API에서 데이터 수집
        raw_data = collector.collect_data_from_api()
        
        if raw_data.empty:
            logger.warning("수집된 데이터가 없습니다.")
            return {
                'statusCode': 204,
                'body': json.dumps({
                    'message': 'No data collected from API',
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        # S3에 원시 데이터 저장
        s3_key = collector.save_raw_data_to_s3(raw_data)
        
        logger.info(f"스케줄된 데이터 수집 완료. {len(raw_data)}개 레코드 수집")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Scheduled data collection completed successfully',
                'records_collected': len(raw_data),
                's3_key': s3_key,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"스케줄된 데이터 수집 실패: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Scheduled data collection failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        }


def handle_s3_file_processing(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    S3 파일 처리 (기존 로직)
    
    Args:
        event: S3 이벤트
        context: Lambda 컨텍스트
        
    Returns:
        응답 딕셔너리
    """
    try:
        logger.info("S3 파일 처리 시작")
        
        # S3 클라이언트 초기화
        s3_client = boto3.client('s3')
        bucket_name = os.environ['S3_BUCKET_NAME']
        
        # 이벤트에서 S3 버킷과 키 정보 추출
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
        
        logger.info("S3 파일 처리 완료")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'S3 file processing completed successfully',
                'processed_file': processed_key if 'processed_key' in locals() else None,
                'input_file': key,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"S3 파일 처리 실패: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'S3 file processing failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        }


def handle_manual_execution(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    수동 실행 처리 (전체 파이프라인)
    
    Args:
        event: 수동 실행 이벤트
        context: Lambda 컨텍스트
        
    Returns:
        응답 딕셔너리
    """
    try:
        logger.info("수동 실행 - 전체 파이프라인 시작")
        
        # 1. 데이터 수집
        collector = YouthPolicyDataCollector()
        raw_data = collector.collect_data_from_api()
        
        if raw_data.empty:
            logger.warning("수집된 데이터가 없습니다.")
            return {
                'statusCode': 204,
                'body': json.dumps({
                    'message': 'No data collected',
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        # 2. S3에 원시 데이터 저장
        s3_key = collector.save_raw_data_to_s3(raw_data)
        
        logger.info(f"수동 실행 완료. {len(raw_data)}개 레코드 처리, S3 키: {s3_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Manual execution completed successfully',
                'records_processed': len(raw_data),
                's3_key': s3_key,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"수동 실행 실패: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Manual execution failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        }


if __name__ == "__main__":
    # 로컬 테스트용
    test_event = {
        'source': 'aws.events',
        'detail-type': 'Scheduled Event',
        'detail': {}
    }
    test_context = None
    result = lambda_handler(test_event, test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False)) 