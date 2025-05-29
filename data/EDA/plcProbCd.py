import pandas as pd
import numpy as np
from openai import OpenAI
import os
import time
from tqdm import tqdm
import json
from dotenv import load_dotenv
# .env 파일에서 환경변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),  # 환경변수에서 API 키 가져오기
)

def analyze_policy_method(row):
    """
    정책 정보를 분석하여 적절한 정책제공방법코드를 추천하는 함수
    """
    # 분석할 컬럼들
    policy_name = str(row.get('정책명', ''))
    policy_keywords = str(row.get('정책키워드명', ''))
    policy_description = str(row.get('정책설명내용', ''))
    policy_support_content = str(row.get('정책지원내용', ''))
    policy_large_category = str(row.get('정책대분류명', ''))
    policy_medium_category = str(row.get('정책중분류명', ''))
    
    # 분석용 텍스트 조합
    analysis_text = f"""
    정책명: {policy_name}
    정책키워드: {policy_keywords}
    정책설명: {policy_description}
    지원내용: {policy_support_content}
    대분류: {policy_large_category}
    중분류: {policy_medium_category}
    """
    
    # 가능한 정책제공방법코드 목록
    method_codes = [
        '인프라 구축', '프로그램', '직접대출', '공공기관', 
        '계약(위탁운영)', '보조금', '대출보증', '공적보험', 
        '조세지출', '바우처', '정보제공', '경제적 규제', '기타'
    ]
    
    try:
        # OpenAI API 호출
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": f"""당신은 청년정책 전문가입니다. 주어진 정책 정보를 분석하여 가장 적절한 정책제공방법코드를 선택해주세요.

다음 중에서 하나를 선택해야 합니다:
{', '.join(method_codes)}

각 코드의 의미:
- 인프라 구축: 시설, 기반시설 구축 관련
- 프로그램: 교육, 훈련, 체험 프로그램 등
- 직접대출: 정부나 공공기관이 직접 자금을 대출
- 공공기관: 공공기관을 통한 서비스 제공
- 계약(위탁운영): 민간에 위탁하여 운영
- 보조금: 현금 지원, 장학금, 생활비 지원 등
- 대출보증: 대출에 대한 보증 제공
- 공적보험: 보험 형태의 지원
- 조세지출: 세금 혜택, 감면 등
- 바우처: 이용권, 쿠폰 형태 지원
- 정보제공: 정보, 상담, 컨설팅 서비스
- 경제적 규제: 규제를 통한 간접 지원
- 기타: 위 분류에 해당하지 않는 경우

응답은 반드시 위 목록 중 하나의 코드만 정확히 반환해주세요."""
                },
                {
                    "role": "user",
                    "content": f"다음 정책 정보를 분석하여 가장 적절한 정책제공방법코드를 선택해주세요:\n\n{analysis_text}"
                }
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        predicted_method = response.choices[0].message.content.strip()
        
        # 예측된 방법이 유효한 코드인지 확인
        if predicted_method in method_codes:
            return predicted_method
        else:
            # 부분 매칭 시도
            for code in method_codes:
                if code in predicted_method:
                    return code
            return '기타'  # 매칭되지 않으면 기타로 분류
            
    except Exception as e:
        print(f"API 호출 오류: {e}")
        return '기타'  # 오류 발생 시 기타로 분류

def fill_missing_policy_methods():
    """
    메인 실행 함수
    """
    print("청년정책목록 데이터 로딩 중...")
    
    # CSV 파일 읽기
    df = pd.read_csv('청년정책목록_전체_매핑완료.csv')
    
    print(f"전체 데이터 개수: {len(df)}")
    print(f"정책제공방법코드 결측치 개수: {df['정책제공방법코드'].isnull().sum()}")
    
    # 결측치가 있는 행들 찾기
    missing_mask = df['정책제공방법코드'].isnull()
    missing_indices = df[missing_mask].index.tolist()
    
    print(f"처리할 결측치 개수: {len(missing_indices)}")
    
    if len(missing_indices) == 0:
        print("처리할 결측치가 없습니다.")
        return df
    
    # 결측치 처리 진행
    print("OpenAI API를 사용하여 결측치 처리 중...")
    
    # API 호출 제한을 위해 배치 처리
    batch_size = 50  # 한 번에 처리할 개수
    processed_count = 0
    
    for i in tqdm(range(0, len(missing_indices), batch_size), desc="배치 처리"):
        batch_indices = missing_indices[i:i+batch_size]
        
        for idx in batch_indices:
            if pd.isnull(df.loc[idx, '정책제공방법코드']):
                # 해당 행의 정보로 정책제공방법코드 예측
                predicted_method = analyze_policy_method(df.loc[idx])
                df.loc[idx, '정책제공방법코드'] = predicted_method
                processed_count += 1
                
                # API 호출 제한을 위한 딜레이
                time.sleep(0.5)  # 0.5초 대기
        
        print(f"진행률: {processed_count}/{len(missing_indices)} 완료")
    
    print(f"결측치 처리 완료! 총 {processed_count}개 처리됨")
    
    # 처리 결과 확인
    remaining_missing = df['정책제공방법코드'].isnull().sum()
    print(f"남은 결측치 개수: {remaining_missing}")
    
    # 결과 저장
    print("결과 저장 중...")
    
    # CSV 파일로 저장
    output_csv = '청년정책목록_전체_매핑완료_수정.csv'
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"CSV 파일 저장 완료: {output_csv}")
    
    # Excel 파일로 저장
    output_xlsx = '청년정책목록_전체_매핑완료_수정.xlsx'
    df.to_excel(output_xlsx, index=False, engine='openpyxl')
    print(f"Excel 파일 저장 완료: {output_xlsx}")
    
    # 수정된 데이터 통계 출력
    print("\n=== 처리 결과 통계 ===")
    print("정책제공방법코드 분포:")
    print(df['정책제공방법코드'].value_counts())
    
    return df

def main():
    """
    메인 함수
    """
    # API 키 확인
    if not os.environ.get("OPENAI_API_KEY"):
        print("오류: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("다음과 같이 API 키를 설정해주세요:")
        print("set OPENAI_API_KEY=your_api_key_here  (Windows)")
        print("export OPENAI_API_KEY=your_api_key_here  (Linux/Mac)")
        return
    
    try:
        # 결측치 처리 실행
        df_processed = fill_missing_policy_methods()
        print("모든 작업이 완료되었습니다!")
        
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()