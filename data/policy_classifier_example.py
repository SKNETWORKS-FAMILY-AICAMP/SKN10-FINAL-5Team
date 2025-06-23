#!/usr/bin/env python3
"""
정책 분류기 사용 예제 스크립트
다양한 사용 시나리오를 보여주는 예제 코드

작성일: 2025-01-28
"""

from policy_classifier import PolicyClassifier
import pandas as pd


def example_1_train_model():
    """예제 1: 모델 훈련"""
    print("=== 예제 1: 모델 훈련 ===")
    
    # 분류기 생성
    classifier = PolicyClassifier()
    
    # 모델 훈련
    metrics = classifier.train(
        train_data_path="청년정책목록_전체.csv",
        validate_on_separate_data="청년정책목록_전처리완료_2025-06-09.csv"
    )
    
    # 모델 저장
    classifier.save_model("policy_classifier_model.pkl")
    
    print("훈련 완료!")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")


def example_2_load_and_predict():
    """예제 2: 저장된 모델 로드 및 예측"""
    print("\n=== 예제 2: 모델 로드 및 예측 ===")
    
    # 저장된 모델 로드
    classifier = PolicyClassifier("policy_classifier_model.pkl")
    
    # 단일 텍스트 예측
    test_text = "청년 취업 지원 프로그램으로 면접 기술과 이력서 작성을 도와드립니다"
    result = classifier.predict(test_text, return_probabilities=True)[0]
    
    print(f"입력 텍스트: {test_text}")
    print(f"예측 분류: {result['predicted_class']}")
    print(f"신뢰도: {result['confidence']:.4f}")
    print("각 클래스별 확률:")
    for cls, prob in result['probabilities'].items():
        print(f"  {cls}: {prob:.4f}")


def example_3_batch_prediction():
    """예제 3: 배치 예측"""
    print("\n=== 예제 3: 배치 예측 ===")
    
    # 저장된 모델 로드
    classifier = PolicyClassifier("policy_classifier_model.pkl")
    
    # 파일 기반 배치 예측 (확률값 포함)
    classifier.predict_file(
        input_file_path="청년정책목록_전처리완료_2025-06-09.csv",
        output_file_path="예측_결과_with_probabilities.csv",
        include_probabilities=True
    )
    
    print("배치 예측 완료: 예측_결과_with_probabilities.csv")


def example_4_multiple_texts():
    """예제 4: 여러 텍스트 동시 예측"""
    print("\n=== 예제 4: 여러 텍스트 동시 예측 ===")
    
    classifier = PolicyClassifier("policy_classifier_model.pkl")
    
    # 여러 텍스트 리스트
    test_texts = [
        "청년 창업 지원금 및 사업 아이디어 개발 프로그램",
        "저소득 청년을 위한 임대주택 및 전세자금 대출",
        "청년 문화 활동 지원 및 취미 개발 프로그램"
    ]
    
    # 예측 수행
    results = classifier.predict(test_texts, return_probabilities=True)
    
    for i, (text, result) in enumerate(zip(test_texts, results)):
        print(f"\n텍스트 {i+1}: {text}")
        print(f"예측: {result['predicted_class']} (신뢰도: {result['confidence']:.4f})")


def example_5_dataframe_prediction():
    """예제 5: DataFrame 직접 예측"""
    print("\n=== 예제 5: DataFrame 직접 예측 ===")
    
    classifier = PolicyClassifier("policy_classifier_model.pkl")
    
    # 샘플 DataFrame 생성
    sample_data = pd.DataFrame({
        '정책명': [
            '청년 취업 면접 스킬업',
            '청년 주거 안정 지원',
            '청년 문화예술 활동 지원'
        ],
        '정책설명내용': [
            '청년들의 면접 기술 향상을 위한 교육 프로그램',
            '청년들의 안정적인 주거를 위한 임대료 지원',
            '청년 예술가들의 창작 활동을 지원하는 프로그램'
        ],
        '정책지원내용': [
            '면접 교육, 이력서 컨설팅, 취업 정보 제공',
            '월세 지원, 보증금 대출, 주거 상담',
            '창작 지원금, 전시 공간 제공, 멘토링'
        ],
        '정책키워드명': [
            '취업, 면접, 교육',
            '주거, 임대료, 지원',
            '문화, 예술, 창작'
        ]
    })
    
    # 예측 수행
    predictions = classifier.predict(sample_data)
    sample_data['예측_대분류명'] = predictions
    
    print(sample_data[['정책명', '예측_대분류명']])


def example_6_model_validation():
    """예제 6: 모델 성능 검증"""
    print("\n=== 예제 6: 모델 성능 검증 ===")
    
    classifier = PolicyClassifier("policy_classifier_model.pkl")
    
    # 검증 수행
    metrics = classifier.validate("청년정책목록_전처리완료_2025-06-09.csv")
    
    print("검증 결과:")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")


def main():
    """모든 예제 실행"""
    print("정책 분류기 사용 예제")
    print("=" * 50)
    
    try:
        # 예제 1: 모델 훈련 (시간이 오래 걸리므로 주석 처리)
        # example_1_train_model()
        print("예제 1은 시간이 오래 걸리므로 건너뜁니다.")
        print("직접 실행하려면 example_1_train_model() 주석을 해제하세요.")
        
        # 예제 2-6은 훈련된 모델이 있다고 가정
        # example_2_load_and_predict()
        # example_3_batch_prediction()
        # example_4_multiple_texts()
        # example_5_dataframe_prediction()
        # example_6_model_validation()
        
        print("\n모든 예제를 실행하려면 먼저 모델을 훈련하세요:")
        print("python policy_classifier.py train --data 청년정책목록_전체.csv --model policy_classifier_model.pkl")
        
    except FileNotFoundError as e:
        print(f"파일을 찾을 수 없습니다: {e}")
        print("필요한 데이터 파일이 있는지 확인하세요.")
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    main() 