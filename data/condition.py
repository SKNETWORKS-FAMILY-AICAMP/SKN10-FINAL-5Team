import pandas as pd
import json
import time
import re
from tqdm import tqdm
from openai import OpenAI
import textwrap

# ─────────────────────────────────────
# 1. GPT 호출 함수 (조건 추출용)
# ─────────────────────────────────────
def extract_conditions_from_text(text, api_key):
    if not isinstance(text, str) or len(text.strip()) == 0:
        return []

    prompt = textwrap.dedent(f"""
아래는 청년 정책의 지원 대상 및 요건에 대한 설명입니다. 이 내용에서 **정책을 신청할 때 필요한 '신청 자격 조건'**만 추출해 주세요.

💡 다음 조건들이 '명시적'이든 '묵시적'이든 반드시 추출 대상입니다:

✅ 반드시 추출할 조건 유형:
- 연령: "만 19세 이상", "20대", "1985년생~2006년생" 등 포함
- 지역: "서울 거주", "부산 주소지 등록", "주민등록상 경상북도" 등
- 거주 기간: "1년 이상 거주", "2023년부터 거주 중" 등
- 소득: "중위소득 150% 이하", "세전 월 255만 원 이하", "고소득자 제외"
- 직업 상태: "재직자", "미취업자", "창업자"
- 신분 조건: "대학생", "고등학생", "청년", "군 복무자", "청소년", "기초생활수급자", "차상위계층"

❗ 표현 방식이 아래와 같이 다양해도 조건으로 간주하여 추출하세요:
- "서울에 주소지를 둔"
- "주민등록이 경북으로 되어 있는"
- "1985년~2006년 출생자"
- "기초생활수급자 혹은 차상위계층"
- "고소득자(1억 원 이상)는 제외"

❌ 아래 항목들은 조건이 아니므로 절대 추출하지 마세요:
- 지원금, 포인트, 수당, 장학금, 물품 지급 등 혜택 내용
- 프로그램 구성, 서비스 항목, 신청 방법, 이용 방법, 신청 사이트

✅ 출력 형식 (JSON 리스트):
[
  {{"조건명": "지역", "조건내용": "서울시 거주"}},
  {{"조건명": "연령", "조건내용": "만 19세 이상 34세 이하"}}
]

조건이 전혀 없으면 빈 리스트 [] 만 출력하세요.

--- 텍스트 ---
{text}
""")



    client = OpenAI(api_key=api_key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        result = response.choices[0].message.content.strip()
        # JSON 파싱
        return json.loads(result)
    except Exception as e:
        # print(f"[조건 추출 오류]: {e}")
        return []

# ─────────────────────────────────────
# 2. 조건 테이블 생성 함수
# ─────────────────────────────────────
def create_condition_table(df, api_key,
                           policy_id_col='정책번호',
                           condition_cols=['정책지원내용', '소득기타내용', '추가신청자격조건내용','참여제안대상내용'],
                           delay=0.3):
    condition_rows = []
    condition_id = 1  # auto-increment ID

    for _, row in tqdm(df.iterrows(), total=len(df), desc="조건 추출 중"):
        policy_id = row[policy_id_col]

        for col in condition_cols:
            content = row.get(col, "")
            condition_list = extract_conditions_from_text(content, api_key)

            for condition in condition_list:
                condition_rows.append({
                    "조건ID": condition_id,
                    "정책ID": policy_id,
                    "조건명": condition.get("조건명", "").strip(),
                    "조건내용": condition.get("조건내용", "").strip()
                })
                condition_id += 1

            time.sleep(delay)

    condition_df = pd.DataFrame(condition_rows)
    return condition_df
