from openai import OpenAI
import time
from tqdm import tqdm
from datetime import datetime
import pandas as pd
import re

# ==================== 컬럼 한국어로 ====================

def drop_columns(df):
    columns_to_drop = [
        'bscPlanCycl','bscPlanPlcyWayNo','bscPlanFcsAsmtNo','bscPlanAsmtNo',
        'pvsnInstGroupCd','plcyAprvSttsCd','sprvsnInstCd','sprvsnInstPicNm',
        'operInstCd','operInstPicNm','rgtrInstCd','rgtrInstCdNm','rgtrUpInstCd',
        'rgtrUpInstCdNm','rgtrHghrkInstCd','rgtrHghrkInstCdNm','frstRegDt',
        'lastMdfcnDt','sprtSclCnt','sprtSclLmtYn','sprtTrgtAgeLmtYn','earnMinAmt',
        'earnMaxAmt'
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
        'bizPrdSeCd': '사업기간구분코드', 'bizPrdBgngYmd': '사업기간시작일자',
        'bizPrdEndYmd': '사업기간종료일자', 'bizPrdEtcCn': '사업기간기타내용',
        'refUrlAddr2':'참고URL주소','plcyPvsnMthdCd':'정책제공방법코드'
    }
    return df.rename(columns=rename_map)

# ==================== 기간 필터링 ====================
# 신청기간을 시작일과 종료일 추출해서 신청시작일 신청마감일 컬럼으로 만들기
# 신청마감일이 오늘보다 이전인 정책은 삭제
# 사업기간 만료 정책 삭제 (사업기간종료일자가 오늘보다 이전인 정책 삭제제)
# 신청기간 결측치 데이터 남겨두기
# 날짜 구간에서 유효한 미래 기간만 추출
def extract_dates(text):
    try:
        if isinstance(text, str):
            # 줄바꿈 및 특수문자 제거
            text = text.replace("\n", " ").replace("\\n", " ").strip()

            matches = re.findall(r'(\d{8})\s*~\s*(\d{8})', text)
            if matches:
                today = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
                future_periods = [
                    (pd.to_datetime(start, format="%Y%m%d", errors='coerce'),
                     pd.to_datetime(end, format="%Y%m%d", errors='coerce'))
                    for start, end in matches
                ]
                if future_periods:
                    # 가장 마지막 구간을 사용 (혹은 조건을 변경 가능)
                    future_periods.sort(key=lambda x: x[0])
                    return pd.Series(future_periods[-1])
    except Exception as e:
        print(f"[파싱 실패] {text} → {e}")
    return pd.Series([pd.NaT, pd.NaT])


# 신청기간 및 사업기간 종료일 기준 필터링
def filter_valid_application_periods(df, period_col='신청기간', biz_end_col='사업기간종료일자'):
    today = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
    df = df.copy()

    # 신청시작일/마감일 추출
    df[['신청시작일', '신청마감일']] = df[period_col].apply(extract_dates)

    # 사업기간 필터링
    if biz_end_col in df.columns:
        df[biz_end_col] = pd.to_datetime(df[biz_end_col], errors='coerce')
        df = df[(df[biz_end_col].isna()) | (df[biz_end_col] >= today)]

    # 신청마감일이 존재하면서 이미 지난 경우만 제거
    df = df[(df['신청마감일'].isna()) | (df['신청마감일'] >= today)]

    return df



# 신청 가능한 기간 내에 있는 정책만 필터링
# def filter_periods(df, period_col='신청기간'):
#     today = pd.to_datetime(datetime.today().strftime("%Y-%m-%d"))
#     df[['신청시작일', '신청마감일']] = df[period_col].apply(extract_dates)
#     df['신청시작일'] = pd.to_datetime(df['신청시작일'], errors='coerce')
#     df['신청마감일'] = pd.to_datetime(df['신청마감일'], errors='coerce')
#     df_filtered = df[
#         (df['신청시작일'].notna()) &
#         (df['신청마감일'].notna()) &
#         (df['신청시작일'] <= today) &
#         (today <= df['신청마감일'])
#     ]
#     return df_filtered.drop(columns=[period_col])

# ==================== 나이 필터링 ====================

def remove_age_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    지원대상최소연령이 18세 이상 39세 이하이고,
    지원대상최대연령도 18세 이상 39세 이하인 행만 남깁니다.
    연령이 NaN인 경우는 제거합니다.
    """
    # NaN 제거 먼저 수행
    df_filtered = df.dropna(subset=["지원대상최소연령", "지원대상최대연령"])

    # 범위 필터링
    condition = (
        (df_filtered["지원대상최소연령"] >= 18) & (df_filtered["지원대상최소연령"] <= 39) &
        (df_filtered["지원대상최대연령"] >= 18) & (df_filtered["지원대상최대연령"] <= 39)
    )

    return df_filtered[condition].reset_index(drop=True)


# ==================== 큰 카테고리 분류 ====================

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

# ==================== 세부분류 ====================

def classify_subcategory_gpt(name, content, top_category, api_key):
    client = OpenAI(api_key=api_key)

    if top_category == "주거":
        prompt = f"""
다음은 청년 정책 중 '주거' 분야에 대한 정보입니다. 이 정책이 어떤 세부분류에 속하는지 아래 보기 중 하나로 분류하세요.

[보기]
1. 금융지원 (대출, 이자, 전월세 등)
2. 임대주택/기숙사
3. 이사비/가전/중개비 지원
4. 기타

- 정책명: {name}
- 정책내용: {content}

응답 형식:
세부분류: [금융지원 or 임대주택 or 이사비지원 or 기타]
"""
        pattern = r"세부분류:\s*(금융지원|임대주택|이사비지원|기타)"

    elif top_category == "일자리(교육)":
        prompt = f"""
다음은 청년 정책 중 '일자리(교육)' 분야에 대한 정보입니다. 이 정책이 어떤 세부분류에 속하는지 아래 보기 중 하나로 분류하세요.

[보기]
1. 인턴/취업연계
2. 전문인력양성/직무훈련
3. 취업 전후 지원
4. 창업
5. 기타

- 정책명: {name}
- 정책내용: {content}

응답 형식:
세부분류: [인턴지원 or 직무훈련 or 취업지원 or 창업 or 기타]
"""
        pattern = r"세부분류:\s*(인턴지원|직무훈련|취업지원|창업|기타)"
    
    else:
        return "기타"

    # GPT 요청
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        result = response.choices[0].message.content
        match = re.search(pattern, result)
        return match.group(1) if match else "기타"
    except Exception as e:
        print(f"[GPT 오류] {name} - {top_category}: {e}")
        return "기타"


# 저장
def add_subcategory_column(df, api_key, name_col='정책명', content_col='정책설명내용', top_col='정책대분류명', new_col='정책세부분류명', delay=0.3):
    df = df.copy()
    df[new_col] = None

    valid_mask = df[top_col].isin(['주거', '일자리(교육)'])
    target_df = df[valid_mask]

    results = []
    for _, row in tqdm(target_df.iterrows(), total=len(target_df), desc="세부분류 중"):
        top_category = row[top_col]
        name = row[name_col]
        content = row[content_col]
        subcategory = classify_subcategory_gpt(name, content, top_category, api_key)
        results.append(subcategory)
        time.sleep(delay)

    df.loc[valid_mask, new_col] = results
    df.loc[~valid_mask, new_col] = "기타"

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
