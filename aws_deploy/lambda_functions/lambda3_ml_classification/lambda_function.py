#!/usr/bin/env python3
"""
Lambda3: ML Policy Classification
전처리된 데이터에 ML 기반 정책 대/중분류를 수행하여 policy_reclassified/ 디렉터리에 저장하는 Lambda 함수

기능:
- S3 preprocessed/ 디렉터리에서 데이터 읽기
- 정책 분류기를 사용한 대분류 자동 분류
- policy_reclassified/ 디렉터리에 날짜별로 파티션 저장
- policy_reclassified/year=2025/month=06/week=03/data.csv

작성일: 2025-01-28
"""

import json
import boto3
import pandas as pd
import numpy as np
import pickle
from datetime import datetime
import os
import logging
from typing import Dict, Any, List, Optional
import io
from urllib.parse import unquote

# ML 모델 관련 imports
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PolicyMLClassifier:
    """정책 ML 분류기 클래스"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ['S3_BUCKET_NAME']
        self.model_s3_key = os.environ.get('MODEL_S3_KEY', 'models/policy_classifier.pkl')
        
        # 분류기 구성 요소
        self.vectorizer = None
        self.label_encoder = None
        self.model = None
        self.is_loaded = False
        
    def _get_partition_path(self) -> str:
        """
        현재 날짜 기준으로 파티션 경로 생성
        
        Returns:
            파티션 경로 (예: policy_reclassified/year=2025/month=06/week=03/)
        """
        now = datetime.now()
        year = now.year
        month = now.month
        week_of_month = ((now.day - 1) // 7) + 1
        
        return f"policy_reclassified/year={year}/month={month:02d}/week={week_of_month:02d}/"
    
    def load_model_from_s3(self) -> None:
        """
        S3에서 훈련된 모델 로드
        """
        logger.info(f"S3에서 모델 로드 시작: s3://{self.bucket_name}/{self.model_s3_key}")
        
        try:
            # S3에서 모델 파일 다운로드
            local_model_path = '/tmp/policy_classifier.pkl'
            self.s3_client.download_file(
                self.bucket_name, 
                self.model_s3_key, 
                local_model_path
            )
            
            # 모델 로드
            with open(local_model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            # 모델 구성 요소 추출
            self.vectorizer = model_data['vectorizer']
            self.label_encoder = model_data['label_encoder']
            self.model = model_data['model']
            
            self.is_loaded = True
            logger.info("모델 로드 완료")
            
            # 임시 파일 정리
            if os.path.exists(local_model_path):
                os.remove(local_model_path)
                
        except Exception as e:
            logger.error(f"모델 로드 실패: {str(e)}")
            # 모델이 없으면 기본 분류기 생성
            self._create_default_classifier()
    
    def _create_default_classifier(self) -> None:
        """
        기본 분류기 생성 (모델 파일이 없는 경우)
        """
        logger.info("기본 분류기 생성")
        
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.label_encoder = LabelEncoder()
        self.model = RandomForestClassifier(random_state=42)
        
        # 기본 분류 클래스 정의
        default_classes = ['일자리', '주거', '교육·역량개발', '복지·문화', '참여·권리']
        self.label_encoder.fit(default_classes)
        
        # 간단한 룰 베이스 분류를 위한 키워드 매핑
        self.keyword_mapping = {
            '일자리': ['취업', '채용', '면접', '일자리', '직업', '구직', '고용', '창업'],
            '주거': ['주거', '임대', '전세', '월세', '주택', '거주', '임대료'],
            '교육·역량개발': ['교육', '학습', '연수', '과정', '교육과정', '역량', '기술'],
            '복지·문화': ['복지', '문화', '지원', '혜택', '여가', '예술', '체육'],
            '참여·권리': ['참여', '권리', '정치', '시민', '자원봉사', '사회활동']
        }
        
        self.is_loaded = True
    
    def load_preprocessed_data_from_s3(self, s3_key: str) -> pd.DataFrame:
        """
        S3에서 전처리된 데이터 로드
        
        Args:
            s3_key: S3 객체 키
            
        Returns:
            로드된 DataFrame
        """
        logger.info(f"S3에서 전처리된 데이터 로드: s3://{self.bucket_name}/{s3_key}")
        
        try:
            # S3에서 객체 가져오기
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            
            # CSV 데이터 읽기
            csv_content = response['Body'].read().decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
            
            logger.info(f"전처리된 데이터 로드 완료: {len(df)}개 레코드")
            return df
            
        except Exception as e:
            logger.error(f"S3 데이터 로드 실패: {str(e)}")
            raise
    
    def classify_policies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        정책 데이터 분류 수행
        
        Args:
            df: 전처리된 정책 데이터 DataFrame
            
        Returns:
            분류가 추가된 DataFrame
        """
        logger.info("정책 분류 시작")
        
        if not self.is_loaded:
            self.load_model_from_s3()
        
        # 결과 DataFrame 복사
        classified_df = df.copy()
        
        # 텍스트 특성 준비
        text_features = self._prepare_text_features(df)
        
        # 분류 수행
        if hasattr(self.model, 'predict') and hasattr(self.vectorizer, 'transform'):
            # 훈련된 모델이 있는 경우
            predictions = self._predict_with_model(text_features)
        else:
            # 기본 룰 베이스 분류
            predictions = self._predict_with_rules(text_features)
        
        # 예측 결과를 DataFrame에 추가
        classified_df['정책대분류명'] = predictions
        classified_df['분류신뢰도'] = self._calculate_confidence(text_features, predictions)
        classified_df['분류일시'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        logger.info(f"정책 분류 완료: {len(classified_df)}개 레코드")
        
        # 분류 결과 요약
        classification_summary = classified_df['정책대분류명'].value_counts()
        logger.info("분류 결과 요약:")
        for category, count in classification_summary.items():
            logger.info(f"  {category}: {count}개")
        
        return classified_df
    
    def _prepare_text_features(self, df: pd.DataFrame) -> pd.Series:
        """
        텍스트 특성 준비
        
        Args:
            df: 입력 DataFrame
            
        Returns:
            결합된 텍스트 Series
        """
        # 텍스트 컬럼들을 결합
        text_columns = ['plcyNm', 'plcyExplnCn', 'plcySprtCn', 'plcyKywdNm']
        
        text_features = ""
        for col in text_columns:
            if col in df.columns:
                text_features = (
                    df[col].fillna('').astype(str) if isinstance(text_features, str) and text_features == ""
                    else text_features + ' ' + df[col].fillna('').astype(str)
                )
        
        if isinstance(text_features, str):
            text_features = pd.Series([''] * len(df))
        
        return text_features
    
    def _predict_with_model(self, text_features: pd.Series) -> List[str]:
        """
        훈련된 모델로 예측
        
        Args:
            text_features: 텍스트 특성 Series
            
        Returns:
            예측 결과 리스트
        """
        try:
            # 텍스트 벡터화
            X = self.vectorizer.transform(text_features)
            
            # 예측 수행
            predictions = self.model.predict(X)
            
            # 라벨 디코딩
            predicted_labels = self.label_encoder.inverse_transform(predictions)
            
            return predicted_labels.tolist()
            
        except Exception as e:
            logger.warning(f"모델 예측 실패, 룰 기반 분류로 전환: {str(e)}")
            return self._predict_with_rules(text_features)
    
    def _predict_with_rules(self, text_features: pd.Series) -> List[str]:
        """
        룰 기반 분류
        
        Args:
            text_features: 텍스트 특성 Series
            
        Returns:
            예측 결과 리스트
        """
        logger.info("룰 기반 분류 수행")
        
        predictions = []
        
        for text in text_features:
            text_lower = str(text).lower()
            max_score = 0
            predicted_category = '기타'
            
            # 각 카테고리별로 키워드 매칭 점수 계산
            for category, keywords in self.keyword_mapping.items():
                score = sum(1 for keyword in keywords if keyword in text_lower)
                if score > max_score:
                    max_score = score
                    predicted_category = category
            
            predictions.append(predicted_category)
        
        return predictions
    
    def _calculate_confidence(self, text_features: pd.Series, predictions: List[str]) -> List[float]:
        """
        분류 신뢰도 계산
        
        Args:
            text_features: 텍스트 특성 Series
            predictions: 예측 결과 리스트
            
        Returns:
            신뢰도 리스트
        """
        confidences = []
        
        try:
            if hasattr(self.model, 'predict_proba') and hasattr(self.vectorizer, 'transform'):
                # 확률 기반 신뢰도
                X = self.vectorizer.transform(text_features)
                probabilities = self.model.predict_proba(X)
                confidences = np.max(probabilities, axis=1).tolist()
            else:
                # 룰 기반 신뢰도 (키워드 매칭 점수)
                for i, text in enumerate(text_features):
                    text_lower = str(text).lower()
                    category = predictions[i]
                    if category in self.keyword_mapping:
                        keywords = self.keyword_mapping[category]
                        score = sum(1 for keyword in keywords if keyword in text_lower)
                        confidence = min(0.9, 0.3 + (score * 0.1))  # 최대 0.9
                    else:
                        confidence = 0.3  # 기본 신뢰도
                    confidences.append(confidence)
                    
        except Exception as e:
            logger.warning(f"신뢰도 계산 실패, 기본값 사용: {str(e)}")
            confidences = [0.5] * len(predictions)  # 기본 신뢰도
        
        return confidences
    
    def save_to_s3(self, df: pd.DataFrame) -> str:
        """
        분류된 데이터를 S3에 저장
        
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
        
        logger.info(f"분류된 데이터 S3 저장 완료: s3://{self.bucket_name}/{s3_key}")
        return s3_key


def test_ml_imports() -> Dict[str, Any]:
    """
    ML 라이브러리 import 테스트
    
    Returns:
        테스트 결과 딕셔너리
    """
    test_results = {}
    libraries = ['pandas', 'numpy', 'sklearn', 'psycopg2', 'boto3']
    
    for lib in libraries:
        try:
            if lib == 'pandas':
                import pandas as pd
                test_results[lib] = f"✅ {pd.__version__}"
            elif lib == 'numpy':
                import numpy as np
                test_results[lib] = f"✅ {np.__version__}"
            elif lib == 'sklearn':
                import sklearn
                test_results[lib] = f"✅ {sklearn.__version__}"
            elif lib == 'psycopg2':
                import psycopg2
                test_results[lib] = f"✅ {psycopg2.__version__}"
            elif lib == 'boto3':
                import boto3
                test_results[lib] = f"✅ {boto3.__version__}"
        except ImportError as e:
            test_results[lib] = f"❌ Import Error: {str(e)}"
        except Exception as e:
            test_results[lib] = f"⚠️ Other Error: {str(e)}"
    
    return test_results


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 메인 핸들러 (S3 이벤트 트리거 또는 테스트 요청)
    
    Args:
        event: S3 이벤트 또는 테스트 이벤트
        context: Lambda 컨텍스트
        
    Returns:
        응답 딕셔너리
    """
    try:
        logger.info("Lambda3 (ML Policy Classification) 실행 시작")
        
        # 테스트 요청 처리
        if 'action' in event and event['action'] == 'test_imports':
            logger.info("ML 라이브러리 import 테스트 실행")
            test_results = test_ml_imports()
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'ML library import test completed',
                    'test_results': test_results,
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        # 일반 테스트 모드
        if event.get('test_mode', False):
            logger.info("테스트 모드로 실행")
            test_results = test_ml_imports()
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Lambda3 test mode completed successfully',
                    'ml_library_test': test_results,
                    'timestamp': datetime.now().isoformat()
                })
            }
        
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
        
        # preprocessed/ 디렉터리의 파일만 처리
        if not s3_key.startswith('preprocessed/'):
            logger.info(f"preprocessed/ 디렉터리가 아닌 파일 건너뛰기: {s3_key}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'File not in preprocessed directory, skipped',
                    'file': s3_key
                })
            }
        
        logger.info(f"처리할 S3 파일: s3://{bucket_name}/{s3_key}")
        
        # ML 분류기 초기화
        classifier = PolicyMLClassifier()
        
        # 전처리된 데이터 로드
        preprocessed_data = classifier.load_preprocessed_data_from_s3(s3_key)
        
        if preprocessed_data.empty:
            logger.warning("로드된 데이터가 없습니다.")
            return {
                'statusCode': 204,
                'body': json.dumps({
                    'message': 'No data to classify',
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        # ML 분류 수행
        classified_data = classifier.classify_policies(preprocessed_data)
        
        if classified_data.empty:
            logger.warning("분류 후 데이터가 없습니다.")
            return {
                'statusCode': 204,
                'body': json.dumps({
                    'message': 'No data after classification',
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        # S3에 저장
        output_s3_key = classifier.save_to_s3(classified_data)
        
        # 분류 통계 계산
        classification_stats = classified_data['정책대분류명'].value_counts().to_dict()
        avg_confidence = float(classified_data['분류신뢰도'].mean())
        
        logger.info(f"Lambda3 실행 완료. {len(classified_data)}개 레코드 분류")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ML policy classification completed successfully',
                'input_records': len(preprocessed_data),
                'output_records': len(classified_data),
                'input_s3_key': s3_key,
                'output_s3_key': output_s3_key,
                'classification_stats': classification_stats,
                'average_confidence': round(avg_confidence, 4),
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda3 실행 중 오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'ML policy classification failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            })
        }


if __name__ == "__main__":
    # 로컬 테스트용
    test_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'test-bucket'},
                'object': {'key': 'preprocessed/year=2025/month=01/week=04/data_20250128_120000.csv'}
            }
        }]
    }
    test_context = None
    result = lambda_handler(test_event, test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False)) 