#!/usr/bin/env python3
"""
청년정책 대분류 자동 분류 시스템
RandomForest + TF-IDF를 사용한 정책 분류 모델

기능:
- 정책 텍스트를 기반으로 대분류(기타, 일자리, 주거) 자동 분류
- 모델 훈련, 저장, 로드, 예측 기능 제공
- 배치 처리 및 단일 예측 지원

작성일: 2025-01-28
"""

import pandas as pd
import numpy as np
import pickle
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
from datetime import datetime

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.metrics import precision_score, recall_score, f1_score

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PolicyClassifier:
    """청년정책 대분류 분류기"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        분류기 초기화
        
        Args:
            model_path: 저장된 모델 경로 (없으면 새로 생성)
        """
        self.vectorizer = TfidfVectorizer(max_features=3000)
        self.label_encoder = LabelEncoder()
        self.model = RandomForestClassifier(random_state=42)
        self.is_trained = False
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
    
    def _prepare_text_features(self, df: pd.DataFrame, 
                             policy_name_col: str = '정책명',
                             description_col: str = '정책설명내용',
                             support_col: str = '정책지원내용', 
                             keyword_col: str = '정책키워드명') -> pd.Series:
        """
        정책 텍스트 특성 준비
        
        Args:
            df: 정책 데이터프레임
            policy_name_col: 정책명 컬럼명
            description_col: 정책설명 컬럼명
            support_col: 정책지원내용 컬럼명
            keyword_col: 정책키워드 컬럼명
        
        Returns:
            결합된 텍스트 시리즈
        """
        # 컬럼명 유연성 지원 (원본 데이터와 전처리된 데이터 모두 지원)
        columns_map = {
            'description': description_col if description_col in df.columns else 'plcyExplnCn',
            'support': support_col if support_col in df.columns else 'plcySprtCn',
            'keyword': keyword_col if keyword_col in df.columns else 'plcyKywdNm'
        }
        
        # 텍스트 결합 (결측값 처리 포함)
        text_features = (
            df[columns_map['description']].fillna('') + ' ' +
            df[columns_map['support']].fillna('') + ' ' +
            df[columns_map['keyword']].fillna('')
        )
        
        return text_features
    
    def train(self, 
              train_data_path: str,
              target_col: str = '정책대분류명',
              test_size: float = 0.2,
              validate_on_separate_data: Optional[str] = None) -> Dict[str, float]:
        """
        모델 훈련
        
        Args:
            train_data_path: 훈련 데이터 CSV 파일 경로
            target_col: 타겟 컬럼명 (대분류명)
            test_size: 테스트 데이터 비율
            validate_on_separate_data: 별도 검증 데이터 경로 (선택사항)
        
        Returns:
            성능 지표 딕셔너리
        """
        logger.info(f"모델 훈련 시작: {train_data_path}")
        
        # 훈련 데이터 로드
        df = pd.read_csv(train_data_path)
        logger.info(f"훈련 데이터 로드 완료: {len(df)}개 레코드")
        
        # 텍스트 특성 준비
        text_features = self._prepare_text_features(df)
        
        # 타겟 컬럼명 유연성 지원
        if target_col not in df.columns:
            target_col = 'lclsfNm'  # 원본 데이터 컬럼명
        
        # 라벨 인코딩
        y = self.label_encoder.fit_transform(df[target_col])
        logger.info(f"분류 클래스: {list(self.label_encoder.classes_)}")
        
        # 텍스트 벡터화
        X = self.vectorizer.fit_transform(text_features)
        logger.info(f"텍스트 벡터화 완료: {X.shape}")
        
        # 훈련/테스트 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, stratify=y, test_size=test_size, random_state=42
        )
        
        # 모델 훈련
        logger.info("RandomForest 모델 훈련 중...")
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # 성능 평가
        y_pred = self.model.predict(X_test)
        metrics = self._calculate_metrics(y_test, y_pred)
        
        logger.info("훈련 완료! 성능 지표:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")
        
        # 별도 검증 데이터가 있는 경우 추가 평가
        if validate_on_separate_data:
            val_metrics = self.validate(validate_on_separate_data)
            metrics.update({f"validation_{k}": v for k, v in val_metrics.items()})
        
        return metrics
    
    def predict(self, 
                input_data: Union[str, List[str], pd.DataFrame],
                return_probabilities: bool = False) -> Union[List[str], List[Dict]]:
        """
        정책 분류 예측
        
        Args:
            input_data: 예측할 데이터 (텍스트, 텍스트 리스트, 또는 DataFrame)
            return_probabilities: 확률값도 함께 반환할지 여부
        
        Returns:
            예측 결과 (분류명 또는 확률 포함 딕셔너리)
        """
        if not self.is_trained:
            raise ValueError("모델이 훈련되지 않았습니다. train() 메서드를 먼저 실행하세요.")
        
        # 입력 데이터 타입별 처리
        if isinstance(input_data, str):
            # 단일 텍스트
            text_features = pd.Series([input_data])
        elif isinstance(input_data, list):
            # 텍스트 리스트
            text_features = pd.Series(input_data)
        elif isinstance(input_data, pd.DataFrame):
            # DataFrame
            text_features = self._prepare_text_features(input_data)
        else:
            raise ValueError("지원하지 않는 입력 데이터 타입입니다.")
        
        # 벡터화
        X = self.vectorizer.transform(text_features)
        
        # 예측
        predictions = self.model.predict(X)
        predicted_labels = self.label_encoder.inverse_transform(predictions)
        
        if return_probabilities:
            # 확률값 포함 반환
            probabilities = self.model.predict_proba(X)
            results = []
            for i, label in enumerate(predicted_labels):
                prob_dict = {
                    cls: float(prob) for cls, prob in 
                    zip(self.label_encoder.classes_, probabilities[i])
                }
                results.append({
                    'predicted_class': label,
                    'confidence': float(max(probabilities[i])),
                    'probabilities': prob_dict
                })
            return results
        else:
            return predicted_labels.tolist()
    
    def predict_file(self, 
                    input_file_path: str,
                    output_file_path: str,
                    include_probabilities: bool = False) -> None:
        """
        파일 기반 배치 예측
        
        Args:
            input_file_path: 입력 CSV 파일 경로
            output_file_path: 출력 CSV 파일 경로
            include_probabilities: 확률값 포함 여부
        """
        logger.info(f"파일 예측 시작: {input_file_path}")
        
        # 데이터 로드
        df = pd.read_csv(input_file_path)
        logger.info(f"예측 대상 데이터: {len(df)}개")
        
        # 예측 수행
        if include_probabilities:
            predictions = self.predict(df, return_probabilities=True)
            
            # 결과를 DataFrame에 추가
            df['예측_대분류명'] = [p['predicted_class'] for p in predictions]
            df['예측_신뢰도'] = [p['confidence'] for p in predictions]
            
            # 각 클래스별 확률도 추가
            for cls in self.label_encoder.classes_:
                df[f'확률_{cls}'] = [p['probabilities'][cls] for p in predictions]
        else:
            df['예측_대분류명'] = self.predict(df)
        
        # 결과 저장
        df.to_csv(output_file_path, index=False, encoding='utf-8-sig')
        logger.info(f"예측 결과 저장 완료: {output_file_path}")
    
    def validate(self, validation_data_path: str) -> Dict[str, float]:
        """
        별도 검증 데이터로 모델 성능 평가
        
        Args:
            validation_data_path: 검증 데이터 CSV 파일 경로
        
        Returns:
            성능 지표 딕셔너리
        """
        if not self.is_trained:
            raise ValueError("모델이 훈련되지 않았습니다.")
        
        logger.info(f"모델 검증 시작: {validation_data_path}")
        
        # 검증 데이터 로드
        df_val = pd.read_csv(validation_data_path)
        
        # 텍스트 특성 및 타겟 준비
        text_features = self._prepare_text_features(df_val)
        
        # 타겟 컬럼 확인
        target_col = '정책대분류명' if '정책대분류명' in df_val.columns else 'lclsfNm'
        y_true = self.label_encoder.transform(df_val[target_col])
        
        # 예측
        X_val = self.vectorizer.transform(text_features)
        y_pred = self.model.predict(X_val)
        
        # 성능 계산
        metrics = self._calculate_metrics(y_true, y_pred)
        
        logger.info("검증 완료! 성능 지표:")
        for metric, value in metrics.items():
            logger.info(f"  {metric}: {value:.4f}")
        
        # 상세 분류 리포트
        logger.info("\n" + classification_report(
            y_true, y_pred, target_names=self.label_encoder.classes_
        ))
        
        return metrics
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """성능 지표 계산"""
        return {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision_macro': precision_score(y_true, y_pred, average='macro'),
            'recall_macro': recall_score(y_true, y_pred, average='macro'),
            'f1_macro': f1_score(y_true, y_pred, average='macro')
        }
    
    def save_model(self, model_path: str) -> None:
        """
        모델 저장
        
        Args:
            model_path: 저장할 모델 파일 경로
        """
        if not self.is_trained:
            raise ValueError("훈련된 모델이 없습니다.")
        
        model_data = {
            'vectorizer': self.vectorizer,
            'label_encoder': self.label_encoder,
            'model': self.model,
            'classes': self.label_encoder.classes_.tolist(),
            'created_at': datetime.now().isoformat()
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        logger.info(f"모델 저장 완료: {model_path}")
    
    def load_model(self, model_path: str) -> None:
        """
        저장된 모델 로드
        
        Args:
            model_path: 로드할 모델 파일 경로
        """
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.vectorizer = model_data['vectorizer']
            self.label_encoder = model_data['label_encoder']
            self.model = model_data['model']
            self.is_trained = True
            
            logger.info(f"모델 로드 완료: {model_path}")
            logger.info(f"지원 클래스: {model_data['classes']}")
            logger.info(f"생성일시: {model_data.get('created_at', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"모델 로드 실패: {e}")
            raise


def main():
    """명령줄 인터페이스"""
    parser = argparse.ArgumentParser(description='청년정책 대분류 자동 분류 시스템')
    
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령어')
    
    # 훈련 명령어
    train_parser = subparsers.add_parser('train', help='모델 훈련')
    train_parser.add_argument('--data', required=True, help='훈련 데이터 CSV 파일 경로')
    train_parser.add_argument('--model', required=True, help='저장할 모델 파일 경로')
    train_parser.add_argument('--validate', help='검증 데이터 CSV 파일 경로 (선택사항)')
    train_parser.add_argument('--test-size', type=float, default=0.2, help='테스트 데이터 비율')
    
    # 예측 명령어
    predict_parser = subparsers.add_parser('predict', help='정책 분류 예측')
    predict_parser.add_argument('--model', required=True, help='학습된 모델 파일 경로')
    predict_parser.add_argument('--input', required=True, help='입력 CSV 파일 경로')
    predict_parser.add_argument('--output', required=True, help='출력 CSV 파일 경로')
    predict_parser.add_argument('--probabilities', action='store_true', help='확률값 포함')
    
    # 검증 명령어
    validate_parser = subparsers.add_parser('validate', help='모델 성능 검증')
    validate_parser.add_argument('--model', required=True, help='학습된 모델 파일 경로')
    validate_parser.add_argument('--data', required=True, help='검증 데이터 CSV 파일 경로')
    
    # 단일 예측 명령어
    single_parser = subparsers.add_parser('single', help='단일 텍스트 예측')
    single_parser.add_argument('--model', required=True, help='학습된 모델 파일 경로')
    single_parser.add_argument('--text', required=True, help='분류할 정책 텍스트')
    
    args = parser.parse_args()
    
    if args.command == 'train':
        # 모델 훈련
        classifier = PolicyClassifier()
        metrics = classifier.train(
            train_data_path=args.data,
            test_size=args.test_size,
            validate_on_separate_data=args.validate
        )
        classifier.save_model(args.model)
        
        print("\n=== 훈련 완료 ===")
        for metric, value in metrics.items():
            print(f"{metric}: {value:.4f}")
    
    elif args.command == 'predict':
        # 파일 예측
        classifier = PolicyClassifier(args.model)
        classifier.predict_file(
            input_file_path=args.input,
            output_file_path=args.output,
            include_probabilities=args.probabilities
        )
        print(f"예측 완료: {args.output}")
    
    elif args.command == 'validate':
        # 모델 검증
        classifier = PolicyClassifier(args.model)
        metrics = classifier.validate(args.data)
        
        print("\n=== 검증 결과 ===")
        for metric, value in metrics.items():
            print(f"{metric}: {value:.4f}")
    
    elif args.command == 'single':
        # 단일 텍스트 예측
        classifier = PolicyClassifier(args.model)
        result = classifier.predict(args.text, return_probabilities=True)[0]
        
        print(f"\n=== 예측 결과 ===")
        print(f"입력 텍스트: {args.text}")
        print(f"예측 분류: {result['predicted_class']}")
        print(f"신뢰도: {result['confidence']:.4f}")
        print("\n각 클래스별 확률:")
        for cls, prob in result['probabilities'].items():
            print(f"  {cls}: {prob:.4f}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 