from openai import OpenAI
import time
from tqdm import tqdm
from datetime import datetime
import pandas as pd
import re
import boto3
import io

# ==================== 컬럼 한국어로 ====================

def drop_columns(df):
    columns_to_drop = [
        'bscPlanCycl', 'bscPlanPlcyWayNo', 'bscPlanFcsAsmtNo', 'bscPlanAsmtNo',
        'pvsnInstGroupCd', 'plcyPvsnMthdCd', 'plcyAprvSttsCd',
        'sprvsnInstCd', 'sprvsnInstPicNm', 'operInstCd', 'operInstPicNm',
        'sprtSclLmtYn', 'bizPrdSeCd', 'bizPrdBgngYmd', 'bizPrdEndYmd', 'bizPrdEtcCn',
        'refUrlAddr2', 'earnMinAmt', 'rgtrInstCdNm', 'rgtrUpInstCd',
        'rgtrUpInstCdNm', 'rgtrHghrkInstCd', 'rgtrHghrkInstCdNm',
        'frstRegDt', 'lastMdfcnDt','rgtrInstCd'
    ]
    return df.drop(columns=[col for col in columns_to_drop if col in df.columns])

def rename_columns_kor(df):
    rename_map = {
        'plcyNo': '정책번호', 'plcyNm': '정책명', 'plcyKywdNm': '정책키워드명',
        'plcyExplnCn': '정책설명내용', 'lclsfNm': '정책대분류명', 'mclsfNm': '정책중분류명',
        'plcySprtCn': '정책지원내용', 'plcyAplyMthdCn': '정책신청방법내용',
        'srngMthdCn': '심사방법내용', 'aplyUrlAddr': '신청URL주소',
        'sbmsnDcmntCn': '제출서류내용', 'etcMttrCn': '기타사항내용',
        'refUrlAddr1': '참고URL주소', 'sprtSclCnt': '지원규모수',
        'sprtArvlSeqYn': '지원도착순서여부', 'sprtTrgtMinAge': '지원대상최소연령',
        'sprtTrgtMaxAge': '지원대상최대연령', 'sprtTrgtAgeLmtYn': '지원대상연령제한여부',
        'mrgSttsCd': '결혼상태코드', 'earnCndSeCd': '소득조건구분코드',
        'earnMaxAmt': '소득최대금액', 'earnEtcCn': '소득기타내용',
        'addAplyQlfcCndCn': '추가신청자격조건내용', 'ptcpPrpTrgtCn': '참여제안대상내용',
        'inqCnt': '조회수', 'zipCd': '정책거주지역코드', 'plcyMajorCd': '정책전공요건코드',
        'jobCd': '정책취업요건코드', 'schoolCd': '정책학력요건코드', 'aplyYmd': '신청기간',
        'sbizCd': '정책특화요건코드', 'sprvsnInstCdNm': '주관기관코드명',
        'operInstCdNm': '운영기관코드명', 'aplyPrdSeCd': '신청기간구분코드',
    }
    return df.rename(columns=rename_map)

# ==================== 기간 필터링 ====================

def extract_dates(text):
    try:
        if isinstance(text, str):
            matches = re.findall(r'(\d{8})\s*~\s*(\d{8})', text)
            if matches:
                start_str, end_str = matches[-1]  # 마지막 구간 사용
                start = pd.to_datetime(start_str, format="%Y%m%d", errors='coerce')
                end = pd.to_datetime(end_str, format="%Y%m%d", errors='coerce')
                return pd.Series([start, end])
    except Exception as e:
        print(f"[파싱 실패] {text} → {e}")
    return pd.Series([pd.NaT, pd.NaT])

def filter_valid_application_periods(df, period_col='신청기간'):
    today = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
    df[['신청시작일', '신청마감일']] = df[period_col].apply(extract_dates)
    df['신청마감일'] = pd.to_datetime(df['신청마감일'], errors='coerce')
    df_filtered = df[df['신청마감일'].apply(lambda x: pd.notnull(x) and x >= today)]
    return df_filtered.drop(columns=[period_col])

def filter_periods(df, period_col='신청기간'):
    today = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
    df[['신청시작일', '신청마감일']] = df[period_col].apply(extract_dates)
    df['신청시작일'] = pd.to_datetime(df['신청시작일'], errors='coerce')
    df['신청마감일'] = pd.to_datetime(df['신청마감일'], errors='coerce')
    df_filtered = df[
        (df['신청시작일'].notna()) &
        (df['신청마감일'].notna()) &
        (df['신청시작일'] <= today) &
        (today <= df['신청마감일'])
    ]
    return df_filtered.drop(columns=[period_col])

# ==================== 나이 필터링 ====================

def remove_age_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    지원대상최소연령이 45세 이상이거나 지원대상최대연령이 15세 이하인 행을 제거합니다.
    연령이 NaN인 경우는 제거하지 않습니다.
    """
    # 조건 설정
    condition = ~(
        (df["지원대상최소연령"].notnull() & (df["지원대상최소연령"] >= 45)) |
        (df["지원대상최대연령"].notnull() & (df["지원대상최대연령"] <= 15))
    )
    return df[condition].reset_index(drop=True)

# ==================== 주거 분류 ====================

def classify_top_category_gpt(name, content, api_key):
    client = OpenAI(api_key=api_key)
    prompt = f"""
다음은 청년 정책에 대한 정보입니다. 이 정책이 어떤 분야에 속하는지 '주거', '일자리(교육)', '기타' 중 하나로 분류하세요.

- 정책명: {name}
- 정책내용: {content}

응답 형식:
분류: [주거 or 일자리(교육) or 기타]
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
    except Exception:
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
        except Exception:
            return "기타"

    result = response.choices[0].message.content
    match = re.search(r"분류:\s*(주거|일자리\(교육\)|기타)", result)
    return match.group(1) if match else "기타"

def add_category_column(df, api_key, name_col='정책명', content_col='정책설명내용', new_col='정책대분류명', delay=0.3):
    results = []
    for _, row in tqdm(df.iterrows(), total=len(df)):
        name = row[name_col]
        content = row[content_col]
        category = classify_top_category_gpt(name, content, api_key)
        results.append(category)
        time.sleep(delay)
    df[new_col] = results
    return df

# ==================== 주거 세부분류 ====================

def classify_residential_subcategory_gpt(name, content, api_key):
    client = OpenAI(api_key=api_key)
    prompt = f"""
다음은 청년 정책 중 '주거' 분야에 대한 정보입니다. 이 정책이 어떤 세부분류에 속하는지 한글 1~3단어로 간단히 분류하세요.

- 정책명: {name}
- 정책내용: {content}

응답 형식:
세부분류: [보조금 or 전월세 or 대출 or 기타]
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        result = response.choices[0].message.content
        match = re.search(r"세부분류:\s*(보조금|전월세|대출|기타)", result)
        return match.group(1) if match else "기타"
    except Exception as e:
        print(f"[GPT 오류] {name}: {e}")
        return "기타"

def classify_residential_gpt(df, api_key, name_col='정책명', content_col='정책설명내용', new_col='주거_세부분류', delay=0.3):
    df = df.copy()
    df[new_col] = None  # 일단 전체에 None을 기본값으로 설정

    residential_mask = df['정책대분류명'] == '주거'
    residential_rows = df[residential_mask]

    results = []
    for _, row in tqdm(residential_rows.iterrows(), total=len(residential_rows)):
        category = classify_residential_subcategory_gpt(row[name_col], row[content_col], api_key)
        results.append(category)
        time.sleep(delay)

    # 결과를 원본 df에 반영
    df.loc[residential_mask, new_col] = results
    return df


# ==================== 텍스트 정제 ====================

def preprocess_policy_texts(row, client):
    prompt = f"""
아래는 정책 관련 여러 설명입니다. 특수기호를 제거하고, 내용을 깔끔하게 정리하고 중복되거나 불필요한 문장을 제거해서 간결하게 요약해주세요.

- 정책설명: {row['정책설명내용']}
- 지원내용: {row['정책지원내용']}
- 정책신청방법: {row['정책신청방법내용']}
- 심사방법: {row['심사방법내용']}
- 제출서류: {row['제출서류내용']}
- 기타사항: {row['기타사항내용']}
- 소득기타내용: {row['소득기타내용']}
- 신청자격조건: {row['추가신청자격조건내용']}
- 참여제안대상: {row['참여제안대상내용']}

요약된 결과를 다음 항목별로 구분해서 출력해주세요:

정책설명:  
지원내용:  
정책신청방법:  
심사방법:  
제출서류:  
기타사항:  
소득기타내용:  
신청자격조건:  
참여제안대상:
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"user", "content":prompt}],
        temperature=0.0,
    )
    return response.choices[0].message.content

def apply_preprocessing_to_df(df, api_key, target_category=None):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    def parse_and_update(row):
        summary_text = preprocess_policy_texts(row, client)
        pattern = (
            r"정책설명:\s*(.*?)\s*지원내용:\s*(.*?)\s*정책신청방법:\s*(.*?)\s*"
            r"심사방법:\s*(.*?)\s*제출서류:\s*(.*?)\s*기타사항:\s*(.*?)\s*"
            r"소득기타내용:\s*(.*?)\s*신청자격조건:\s*(.*?)\s*참여제안대상:\s*(.*)"
        )
        match = re.search(pattern, summary_text, re.DOTALL)
        if match:
            return pd.Series({
                '정책설명내용': match.group(1).strip(),
                '정책지원내용': match.group(2).strip(),
                '정책신청방법내용': match.group(3).strip(),
                '심사방법내용': match.group(4).strip(),
                '제출서류내용': match.group(5).strip(),
                '기타사항내용': match.group(6).strip(),
                '소득기타내용': match.group(7).strip(),
                '추가신청자격조건내용': match.group(8).strip(),
                '참여제안대상내용': match.group(9).strip(),
            })
        else:
            # 파싱 실패 시 원본 유지
            return pd.Series({
                '정책설명내용': row['정책설명내용'],
                '정책지원내용': row['정책지원내용'],
                '정책신청방법내용': row['정책신청방법내용'],
                '심사방법내용': row['심사방법내용'],
                '제출서류내용': row['제출서류내용'],
                '기타사항내용': row['기타사항내용'],
                '소득기타내용': row['소득기타내용'],
                '추가신청자격조건내용': row['추가신청자격조건내용'],
                '참여제안대상내용': row['참여제안대상내용'],
            })

    # 진행바 적용
    updated_rows = []
    if target_category:
        df_to_process = df[df['정책대분류명'] == target_category].copy()
    else:
        df_to_process = df.copy()

    for idx, row in tqdm(df_to_process.iterrows(), total=len(df_to_process), desc="텍스트 정제 중"):
        updated_row = parse_and_update(row)
        updated_row.name = idx
        updated_rows.append(updated_row)

    updated_df = pd.DataFrame(updated_rows)

    # 원본 df에 업데이트 (대분류 조건에 맞는 행만)
    if target_category:
        df.loc[updated_df.index, updated_df.columns] = updated_df
    else:
        df[updated_df.columns] = updated_df

    return df

def get_openai_api_key():
    """
    AWS SSM Parameter Store에서 OpenAI API 키를 가져옵니다.
    """
    ssm = boto3.client('ssm')
    param = ssm.get_parameter(Name='/openai/api_key', WithDecryption=True)
    return param['Parameter']['Value']

def process_policy_data(df: pd.DataFrame, api_key: str, delay: float = 0.3) -> pd.DataFrame:
    """
    청년 정책 데이터를 전처리하는 전체 파이프라인을 실행합니다.
    
    Args:
        df (pd.DataFrame): 원본 정책 데이터프레임
        api_key (str): OpenAI API 키
        delay (float, optional): API 호출 간 딜레이 시간. 기본값 0.3초
        
    Returns:
        pd.DataFrame: 전처리가 완료된 데이터프레임
    """
    print("1. 불필요 컬럼 제거 중...")
    df = drop_columns(df)
    
    print("2. 컬럼명 한글로 변환 중...")
    df = rename_columns_kor(df)
    
    print("3. 신청기간 필터링 중...")
    df = filter_valid_application_periods(df)
    
    print("4. 나이 조건 필터링 중...")
    df = remove_age_outliers(df)
    
    print("5. 정책 대분류 분류 중...")
    df = add_category_column(df, api_key, delay=delay)
    
    print("6. 주거 정책 세부분류 중...")
    df = classify_residential_gpt(df, api_key, delay=delay)
    
    print("7. 텍스트 정제 중...")
    df = apply_preprocessing_to_df(df, api_key)
    
    return df
