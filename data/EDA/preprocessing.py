"""
청년정책 데이터 전처리 스크립트
- 코드 매핑 및 지역 정보 변환
- 중복 카테고리 제거
- 최종 데이터 저장
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import koreanize_matplotlib

# 데이터 로딩
print("데이터 로딩 중...")
df = pd.read_csv('청년정책목록_전체.csv', encoding='utf-8')
df_code = pd.read_csv('청년정책_전체코드매핑.csv', encoding='utf-8')
df_region = pd.read_excel("법정동 기준 시군구 단위.xlsx", sheet_name="통합 버전")
df_region2 = pd.read_csv("법정동코드 전체자료.txt", encoding='cp949', sep='\t')

# 컬럼명 영어 -> 한글
col = ['정책번호', '기본계획차수', '기본계획정책방향번호', '기본계획중점과제번호', '기본계획과제번호', '제공기관그룹코드', '정책제공방법코드', '정책승인상태코드', '정책명', '정책키워드명',
      '정책설명내용', '정책대분류명', '정책중분류명', '정책지원내용', '주관기관코드', '주관기관코드명', '주관기관담당자명', '운영기관코드', '운영기관코드명', '운영기관담당자명',
      '지원규모제한여부', '신청기간구분코드', '사업기간구분코드', '사업기간시작일자', '사업기간종료일자', '사업기간기타내용', '정책신청방법내용', '심사방법내용', '신청URL주소', '제출서류내용',
      '기타사항내용', '참고URL주소1', '참고URL주소2', '지원규모수', '지원도착순서여부', '지원대상최소연령', '지원대상최대연령', '지원대상연령제한여부', '결혼상태코드', '소득조건구분코드',
      '소득최소금액', '소득최대금액', '소득기타내용', '추가신청자격조건내용', '참여제안대상내용', '조회수', '등록자기관코드', '등록자기관코드명', '등록자상위기관코드', '등록자상위기관코드명',
      '등록자최상위기관코드', '등록자최상위기관코드명', '정책거주지역코드', '정책전공요건코드', '정책취업요건코드', '정책학력요건코드', '신청기간', '최초등록일시', '최종수정일시', '정책특화요건코드',
      ]
df.columns = col

print("컬럼명 변경 완료")

# df_code의 코드그룹명과 df 컬럼이 일치하는 경우 코드를 코드명으로 매핑
print("코드 매핑 시작...")

# df_code에서 존재하는 코드그룹명 목록 확인
unique_code_groups = df_code['코드그룹명'].unique()
print(f"코드 그룹 종류: {len(unique_code_groups)}개")
print(unique_code_groups)

# df 컬럼 중에서 코드그룹명과 일치하는 컬럼 확인
matching_columns = [col for col in df.columns if col in unique_code_groups]
print(f"\n데이터프레임에서 매핑 가능한 컬럼: {len(matching_columns)}개")
print(matching_columns)

def map_codes_to_names(df, df_code, column_name):
    """코드를 코드명으로 매핑하는 함수"""
    # 해당 코드그룹에 대한 코드-코드명 매핑 딕셔너리 생성
    code_map = df_code[df_code['코드그룹명'] == column_name].set_index('코드')['코드명'].to_dict()
    
    # 원래 컬럼값을 저장 (로깅 목적)
    original_values = df[column_name].copy()
    
    # 코드를 코드명으로 변환 (기존 컬럼 값 대체)
    df[column_name] = df[column_name].map(code_map)
    
    # 매핑된 결과 요약
    mapped_count = df[column_name].notna().sum()
    print(f"{column_name}: 총 {len(df)}개 중 {mapped_count}개 매핑 완료 ({mapped_count/len(df)*100:.2f}%)")
    
    # 매핑된 샘플 몇 개 보여주기
    if mapped_count > 0:
        sample_df = pd.DataFrame({
            '원래 코드': original_values.head(5),
            '매핑된 이름': df[column_name].head(5)
        })
        print(sample_df)
    
    return df

# 매칭되는 모든 컬럼에 대해 매핑 실행
for column in matching_columns:
    df = map_codes_to_names(df, df_code, column)
    print('-' * 50)

print("\n매핑 완료!")
# 일부 매핑 결과 확인
print("매핑된 데이터 샘플:")
if matching_columns:
    print(df[matching_columns].head())
else:
    print("매핑할 컬럼이 없습니다.")

# 특수 코드 필드 매핑 함수들
def create_code_mapping_function(df_code, code_group_name):
    """
    특정 코드그룹에 대한 매핑 함수를 생성합니다.
    
    Args:
        df_code: 코드 매핑 정보가 있는 데이터프레임
        code_group_name: 코드그룹명 (예: '전공조건코드', '자격학력코드' 등)
        
    Returns:
        코드를 코드명으로 변환하는 함수
    """
    # 코드-코드명 매핑 딕셔너리 생성
    code_map = df_code[df_code['코드그룹명'] == code_group_name].set_index('코드')['코드명'].to_dict()
    
    def transform_code(code_value):
        # None이나 NaN인 경우 그대로 반환
        if pd.isna(code_value):
            return code_value
            
        # 쉼표로 구분된 여러 코드가 있는지 확인
        if isinstance(code_value, str) and ',' in code_value:
            # 쉼표로 구분된 각 코드를 처리
            codes = code_value.split(',')
            transformed_codes = []
            
            for code in codes:
                if code.strip().startswith('00'):
                    try:
                        # '00' 제거 후 정수로 변환
                        transformed_code = int(code.strip()[2:])
                        # 매핑 딕셔너리에서 코드명 찾기
                        code_name = code_map.get(transformed_code)
                        if code_name:
                            transformed_codes.append(code_name)
                    except ValueError:
                        # 변환 실패 시 원래 코드 유지
                        transformed_codes.append(code.strip())
                else:
                    transformed_codes.append(code.strip())
                    
            # 변환된 코드명들을 쉼표로 연결하여 반환
            return ', '.join(transformed_codes) if transformed_codes else code_value
        
        # 단일 코드인 경우    
        elif isinstance(code_value, str) and code_value.startswith('00'):
            try:
                # '00' 제거 후 정수로 변환
                transformed_code = int(code_value[2:])
                # 매핑 딕셔너리에서 코드명 찾기
                return code_map.get(transformed_code, code_value)
            except ValueError:
                # 변환 실패 시 원래 코드 유지
                return code_value
        
        # 그 외의 경우 원래 값 그대로 반환
        return code_value
    
    return transform_code


def apply_code_mapping(df, df_code, column_name, code_group_name):
    """
    데이터프레임의 특정 컬럼에 코드 매핑을 적용합니다.
    
    Args:
        df: 대상 데이터프레임
        df_code: 코드 매핑 정보가 있는 데이터프레임
        column_name: 매핑을 적용할 컬럼명
        code_group_name: 코드그룹명 (예: '전공조건코드', '자격학력코드' 등)
        
    Returns:
        매핑이 적용된 데이터프레임
    """
    # 매핑 함수 생성
    transform_function = create_code_mapping_function(df_code, code_group_name)
    
    # 원래 값 저장 (비교용)
    original_codes = df[column_name].copy()
    
    # 변환 함수 적용하여 코드명으로 매핑
    df[column_name] = df[column_name].apply(transform_function)
    
    # 매핑 결과 확인
    mapped_count = df[column_name].notna().sum()
    print(f"{column_name}: 총 {len(df)}개 중 {mapped_count}개 매핑 완료 ({mapped_count/len(df)*100:.2f}%)")
    
    # 매핑 전후 비교 샘플 출력
    sample_df = pd.DataFrame({
        '원래 코드': original_codes.head(10),
        '매핑된 이름': df[column_name].head(10)
    })
    print("\n매핑 전후 샘플 비교:")
    print(sample_df)
    
    # 매핑된 값들의 분포 확인
    value_counts = df[column_name].value_counts()
    print(f"\n{column_name} 값 분포 (상위 10개):")
    print(value_counts.head(10))
    
    return df


def map_all_code_fields(df, df_code):
    """
    여러 코드 필드에 대해 매핑을 일괄 적용합니다.
    
    Args:
        df: 대상 데이터프레임
        df_code: 코드 매핑 정보가 있는 데이터프레임
        
    Returns:
        매핑이 적용된 데이터프레임
    """
    # 매핑할 컬럼과 코드그룹 정의
    mapping_configs = [
        ('정책전공요건코드', '전공조건코드'),
        ('정책학력요건코드', '자격학력코드'),
        ('정책취업요건코드', '취업상태코드'),
        ('정책특화요건코드', '특수분야코드')
    ]
    
    # 각 매핑 설정에 대해 매핑 적용
    for column_name, code_group_name in mapping_configs:
        print(f"\n{'-'*50}")
        print(f"{code_group_name} 매핑 시작...")
        df = apply_code_mapping(df, df_code, column_name, code_group_name)
    
    print(f"\n{'-'*50}")
    print("모든 코드 매핑 완료!")
    return df

# 모든 코드 필드에 매핑 적용
df = map_all_code_fields(df, df_code)

# 첫 번째 행 확인
print("\n첫 번째 데이터 행:")
print(df.iloc[0])

# 지역 코드 매핑 (df_region 사용)
print("\n지역 코드 매핑 시작...")

# 1. 지역 코드-시군구명 매핑 딕셔너리 생성
df_region['시군구_코드_법정동기준'] = df_region['시군구_코드_법정동기준'].astype(str)
region_code_map = df_region.set_index('시군구_코드_법정동기준')['시군구'].to_dict()

# 2. 코드 변환 함수 정의 - 쉼표로 구분된 코드들도 처리
def transform_region_code(code_value):
    # None이나 NaN인 경우 그대로 반환
    if pd.isna(code_value):
        return code_value
        
    # 쉼표로 구분된 여러 코드가 있는지 확인
    if isinstance(code_value, str) and ',' in code_value:
        # 쉼표로 구분된 각 코드를 처리
        codes = code_value.split(',')
        transformed_codes = []
        
        for code in codes:
            code = code.strip()
            # 매핑 딕셔너리에서 시군구명 찾기
            region_name = region_code_map.get(code)
            if region_name:
                transformed_codes.append(region_name)
            else:
                transformed_codes.append(code)
        # 변환된 코드명들을 쉼표로 연결하여 반환
        return ', '.join(transformed_codes) if transformed_codes else code_value
    
    # 단일 코드인 경우    
    else:
        # 매핑 딕셔너리에서 시군구명 찾기
        return region_code_map.get(code_value, code_value)

# 3. 원래 값 저장 (비교용)
original_region_codes = df['정책거주지역코드'].copy()

# 4. 변환 함수 적용하여 시군구명으로 매핑
df['정책거주지역코드'] = df['정책거주지역코드'].apply(transform_region_code)

# 5. 매핑 결과 확인
mapped_count = df['정책거주지역코드'].notna().sum()
print(f"정책거주지역코드: 총 {len(df)}개 중 {mapped_count}개 매핑 완료 ({mapped_count/len(df)*100:.2f}%)")

# 6. 매핑 전후 비교 샘플 출력
sample_df = pd.DataFrame({
    '원래 코드': original_region_codes.head(10),
    '매핑된 시군구명': df['정책거주지역코드'].head(10)
})
print("\n매핑 전후 샘플 비교:")
print(sample_df)

# 7. 매핑된 값들의 분포 확인 (상위 10개)
print("\n지역별 정책 수 (상위 10개):")
print(df['정책거주지역코드'].value_counts().head(10))

# df_region2를 사용한 추가 지역 매핑
print("\n법정동코드 기반 지역 매핑 시작...")

# 1. 법정동코드 앞 5자리 기준으로 중복을 제거한 데이터프레임 생성
filtered_df_region2 = df_region2[df_region2['폐지여부'] == '존재'].copy()
filtered_df_region2['법정동코드_5자리'] = filtered_df_region2['법정동코드'].astype(str).str[:5]

# 중복된 5자리 코드 중 첫 번째 데이터만 유지
unique_region_df = filtered_df_region2.drop_duplicates(subset=['법정동코드_5자리'])

print(f"원본 데이터 크기: {len(filtered_df_region2)}개")
print(f"중복 제거 후 데이터 크기: {len(unique_region_df)}개")
print(f"제거된 중복 데이터 수: {len(filtered_df_region2) - len(unique_region_df)}개")

# 2. 코드-법정동명 매핑 딕셔너리 생성 
region_code_map = unique_region_df.set_index('법정동코드_5자리')['법정동명'].to_dict()

print(f"법정동 코드 매핑 딕셔너리 크기: {len(region_code_map)}개")
print("법정동 코드 예시:", list(region_code_map.items())[:5])

# 3. 코드 변환 함수 재정의
def transform_region_code(code_value):
    # None이나 NaN인 경우 그대로 반환
    if pd.isna(code_value):
        return code_value
        
    # 쉼표로 구분된 여러 코드가 있는지 확인
    if isinstance(code_value, str) and ',' in code_value:
        # 쉼표로 구분된 각 코드를 처리
        codes = code_value.split(',')
        transformed_codes = []
        
        for code in codes:
            code = code.strip()
            # 앞 5자리 추출
            code_5digits = code[:5] if len(code) >= 5 else code
            # 매핑 딕셔너리에서 법정동명 찾기
            region_name = region_code_map.get(code_5digits)
            if region_name:
                transformed_codes.append(region_name)
            else:
                transformed_codes.append(code)
        # 변환된 코드명들을 쉼표로 연결하여 반환
        return ', '.join(transformed_codes) if transformed_codes else code_value
    
    # 단일 코드인 경우    
    else:
        # 앞 5자리 추출
        if isinstance(code_value, str) and len(code_value) >= 5:
            code_5digits = code_value[:5]
            # 매핑 딕셔너리에서 법정동명 찾기
            region_name = region_code_map.get(code_5digits)
            if region_name:
                return region_name
        return code_value

# 4. 원래 값 저장 및 변환 함수 적용
original_region_codes = df['정책거주지역코드'].copy()
df['정책거주지역코드'] = df['정책거주지역코드'].apply(transform_region_code)

# 5. 매핑 결과 확인
mapped_count = (df['정책거주지역코드'] != original_region_codes).sum()
print(f"정책거주지역코드: 총 {len(df)}개 중 {mapped_count}개 매핑 완료 ({mapped_count/len(df)*100:.2f}%)")

# 6. 매핑 전후 비교 샘플 출력
sample_df = pd.DataFrame({
    '원래 코드': original_region_codes.head(10),
    '매핑된 법정동명': df['정책거주지역코드'].head(10)
})
print("\n매핑 전후 샘플 비교:")
print(sample_df)

# 전국 지역 코드를 '전국'으로 변경
print("\n지역 코드 통합 변경 중...")

regions = {
        'all_region': "서울 종로구, 서울 중구, 서울 용산구, 서울 성동구, 서울 광진구, 서울 동대문구, 서울 중랑구, 서울 성북구, 서울 강북구, 서울 도봉구, 서울 노원구, 서울 은평구, 서울 서대문구, 서울 마포구, 서울 양천구, 서울 강서구, 서울 구로구, 서울 금천구, 서울 영등포구, 서울 동작구, 서울 관악구, 서울 서초구, 서울 강남구, 서울 송파구, 서울 강동구, 부산 중구, 부산 서구, 부산 동구, 부산 영도구, 부산 부산진구, 부산 동래구, 부산 남구, 부산 북구, 부산 해운대구, 부산 사하구, 부산 금정구, 부산 강서구, 부산 연제구, 부산 수영구, 부산 사상구, 부산 기장군, 대구 중구, 대구 동구, 대구 서구, 대구 남구, 대구 북구, 대구 수성구, 대구 달서구, 대구 달성군, 대구광역시 군위군, 인천 중구, 인천 동구, 인천 미추홀구, 인천 연수구, 인천 남동구, 인천 부평구, 인천 계양구, 인천 서구, 인천 강화군, 인천 옹진군, 광주 동구, 광주 서구, 광주 남구, 광주 북구, 광주 광산구, 대전 동구, 대전 중구, 대전 서구, 대전 유성구, 대전 대덕구, 울산 중구, 울산 남구, 울산 동구, 울산 북구, 울산 울주군, 세종특별자치시, 경기도 수원시 장안구, 경기도 수원시 권선구, 경기도 수원시 팔달구, 경기도 수원시 영통구, 경기도 성남시 수정구, 경기도 성남시 중원구, 경기도 성남시 분당구, 경기도 의정부시, 경기도 안양시 만안구, 경기도 안양시 동안구, 경기도 부천시 원미구 , 경기도 부천시 소사구 , 경기도 부천시 오정구 , 경기도 광명시, 경기도 평택시, 경기도 동두천시, 경기도 안산시 상록구, 경기도 안산시 단원구, 경기도 고양시 덕양구, 경기도 고양시 일산동구, 경기도 고양시 일산서구, 경기도 과천시, 경기도 구리시, 경기도 남양주시, 경기도 오산시, 경기도 시흥시, 경기도 군포시, 경기도 의왕시, 경기도 하남시, 경기도 용인시 처인구, 경기도 용인시 기흥구, 경기도 용인시 수지구, 경기도 파주시, 경기도 이천시, 경기도 안성시, 경기도 김포시, 경기도 화성시, 경기도 광주시, 경기도 양주시, 경기도 포천시, 경기도 여주시, 경기도 연천군, 경기도 가평군, 경기도 양평군, 충청북도 청주시 상당구, 충청북도 청주시 서원구, 충청북도 청주시 흥덕구, 충청북도 청주시 청원구, 충청북도 충주시, 충청북도 제천시, 충청북도 보은군, 충청북도 옥천군, 충청북도 영동군, 충청북도 증평군, 충청북도 진천군, 충청북도 괴산군, 충청북도 음성군, 충청북도 단양군, 충청남도 천안시 동남구, 충청남도 천안시 서북구, 충청남도 공주시, 충청남도 보령시, 충청남도 아산시, 충청남도 서산시, 충청남도 논산시, 충청남도 계룡시, 충청남도 당진시, 충청남도 금산군, 충청남도 부여군, 충청남도 서천군, 충청남도 청양군, 충청남도 홍성군, 충청남도 예산군, 충청남도 태안군, 전라남도 목포시, 전라남도 여수시, 전라남도 순천시, 전라남도 나주시, 전라남도 광양시, 전라남도 담양군, 전라남도 곡성군, 전라남도 구례군, 전라남도 고흥군, 전라남도 보성군, 전라남도 화순군, 전라남도 장흥군, 전라남도 강진군, 전라남도 해남군, 전라남도 영암군, 전라남도 무안군, 전라남도 함평군, 전라남도 영광군, 전라남도 장성군, 전라남도 완도군, 전라남도 진도군, 전라남도 신안군, 경상북도 포항시 남구, 경상북도 포항시 북구, 경상북도 경주시, 경상북도 김천시, 경상북도 안동시, 경상북도 구미시, 경상북도 영주시, 경상북도 영천시, 경상북도 상주시, 경상북도 문경시, 경상북도 경산시, 경상북도 의성군, 경상북도 청송군, 경상북도 영양군, 경상북도 영덕군, 경상북도 청도군, 경상북도 고령군, 경상북도 성주군, 경상북도 칠곡군, 경상북도 예천군, 경상북도 봉화군, 경상북도 울진군, 경상북도 울릉군, 경상남도 창원시 의창구, 경상남도 창원시 성산구, 경상남도 창원시 마산합포구, 경상남도 창원시 마산회원구, 경상남도 창원시 진해구, 경상남도 진주시, 경상남도 통영시, 경상남도 사천시, 경상남도 김해시, 경상남도 밀양시, 경상남도 거제시, 경상남도 양산시, 경상남도 의령군, 경상남도 함안군, 경상남도 창녕군, 경상남도 고성군, 경상남도 남해군, 경상남도 하동군, 경상남도 산청군, 경상남도 함양군, 경상남도 거창군, 경상남도 합천군, 제주 제주시, 제주 서귀포시, 강원특별자치도 춘천시, 강원특별자치도 원주시, 강원특별자치도 강릉시, 강원특별자치도 동해시, 강원특별자치도 태백시, 강원특별자치도 속초시, 강원특별자치도 삼척시, 강원특별자치도 홍천군, 강원특별자치도 횡성군, 강원특별자치도 영월군, 강원특별자치도 평창군, 강원특별자치도 정선군, 강원특별자치도 철원군, 강원특별자치도 화천군, 강원특별자치도 양구군, 강원특별자치도 인제군, 강원특별자치도 고성군, 강원특별자치도 양양군, 전북특별자치도 전주시 완산구, 전북특별자치도 전주시 덕진구, 전북특별자치도 군산시, 전북특별자치도 익산시, 전북특별자치도 정읍시, 전북특별자치도 남원시, 전북특별자치도 김제시, 전북특별자치도 완주군, 전북특별자치도 진안군, 전북특별자치도 무주군, 전북특별자치도 장수군, 전북특별자치도 임실군, 전북특별자치도 순창군, 전북특별자치도 고창군, 전북특별자치도 부안군",
        'seoul_region': "서울 종로구, 서울 중구, 서울 용산구, 서울 성동구, 서울 광진구, 서울 동대문구, 서울 중랑구, 서울 성북구, 서울 강북구, 서울 도봉구, 서울 노원구, 서울 은평구, 서울 서대문구, 서울 마포구, 서울 양천구, 서울 강서구, 서울 구로구, 서울 금천구, 서울 영등포구, 서울 동작구, 서울 관악구, 서울 서초구, 서울 강남구, 서울 송파구, 서울 강동구",
        'busan_region': "부산 중구, 부산 서구, 부산 동구, 부산 영도구, 부산 부산진구, 부산 동래구, 부산 남구, 부산 북구, 부산 해운대구, 부산 사하구, 부산 금정구, 부산 강서구, 부산 연제구, 부산 수영구, 부산 사상구, 부산 기장군",
        'gwangju_region': "광주 동구, 광주 서구, 광주 남구, 광주 북구, 광주 광산구",
        'daegu_region': "대구 중구, 대구 동구, 대구 서구, 대구 남구, 대구 북구, 대구 수성구, 대구 달서구, 대구 달성군, 대구광역시 군위군",
        'daejeon_region': "대전 동구, 대전 중구, 대전 서구, 대전 유성구, 대전 대덕구",
        'changwon_region': "경상남도 창원시 의창구, 경상남도 창원시 성산구, 경상남도 창원시 마산합포구, 경상남도 창원시 마산회원구, 경상남도 창원시 진해구",
        'ulsan_region': "울산 중구, 울산 남구, 울산 동구, 울산 북구, 울산 울주군",
        'incheon_region': "인천 중구, 인천 동구, 인천 미추홀구, 인천 연수구, 인천 남동구, 인천 부평구, 인천 계양구, 인천 서구, 인천 강화군, 인천 옹진군",
        'jeonnam_region': "전라남도 목포시, 전라남도 여수시, 전라남도 순천시, 전라남도 나주시, 전라남도 광양시, 전라남도 담양군, 전라남도 곡성군, 전라남도 구례군, 전라남도 고흥군, 전라남도 보성군, 전라남도 화순군, 전라남도 장흥군, 전라남도 강진군, 전라남도 해남군, 전라남도 영암군, 전라남도 무안군, 전라남도 함평군, 전라남도 영광군, 전라남도 장성군, 전라남도 완도군, 전라남도 진도군, 전라남도 신안군",
        'gangwon_region': "강원특별자치도 춘천시, 강원특별자치도 원주시, 강원특별자치도 강릉시, 강원특별자치도 동해시, 강원특별자치도 태백시, 강원특별자치도 속초시, 강원특별자치도 삼척시, 강원특별자치도 홍천군, 강원특별자치도 횡성군, 강원특별자치도 영월군, 강원특별자치도 평창군, 강원특별자치도 정선군, 강원특별자치도 철원군, 강원특별자치도 화천군, 강원특별자치도 양구군, 강원특별자치도 인제군, 강원특별자치도 고성군, 강원특별자치도 양양군",
        'bucheon_region': "경기도 부천시 원미구 , 경기도 부천시 소사구 , 경기도 부천시 오정구",
        'cheongju_region': "충청북도 청주시 상당구, 충청북도 청주시 서원구, 충청북도 청주시 흥덕구, 충청북도 청주시 청원구",
        'yongin_region': "경기도 용인시 처인구, 경기도 용인시 기흥구, 경기도 용인시 수지구",
        'chungbuk_region': "충청북도 청주시 상당구, 충청북도 청주시 서원구, 충청북도 청주시 흥덕구, 충청북도 청주시 청원구, 충청북도 충주시, 충청북도 제천시, 충청북도 보은군, 충청북도 옥천군, 충청북도 영동군, 충청북도 증평군, 충청북도 진천군, 충청북도 괴산군, 충청북도 음성군, 충청북도 단양군",
        'jeonbuk_region': "전북특별자치도 전주시 완산구, 전북특별자치도 전주시 덕진구, 전북특별자치도 군산시, 전북특별자치도 익산시, 전북특별자치도 정읍시, 전북특별자치도 남원시, 전북특별자치도 김제시, 전북특별자치도 완주군, 전북특별자치도 진안군, 전북특별자치도 무주군, 전북특별자치도 장수군, 전북특별자치도 임실군, 전북특별자치도 순창군, 전북특별자치도 고창군, 전북특별자치도 부안군",
        'gyeonggi_region': "경기도 수원시 장안구, 경기도 수원시 권선구, 경기도 수원시 팔달구, 경기도 수원시 영통구, 경기도 성남시 수정구, 경기도 성남시 중원구, 경기도 성남시 분당구, 경기도 의정부시, 경기도 안양시 만안구, 경기도 안양시 동안구, 경기도 부천시 원미구 , 경기도 부천시 소사구 , 경기도 부천시 오정구 , 경기도 광명시, 경기도 평택시, 경기도 동두천시, 경기도 안산시 상록구, 경기도 안산시 단원구, 경기도 고양시 덕양구, 경기도 고양시 일산동구, 경기도 고양시 일산서구, 경기도 과천시, 경기도 구리시, 경기도 남양주시, 경기도 오산시, 경기도 시흥시, 경기도 군포시, 경기도 의왕시, 경기도 하남시, 경기도 용인시 처인구, 경기도 용인시 기흥구, 경기도 용인시 수지구, 경기도 파주시, 경기도 이천시, 경기도 안성시, 경기도 김포시, 경기도 화성시, 경기도 광주시, 경기도 양주시, 경기도 포천시, 경기도 여주시, 경기도 연천군, 경기도 가평군, 경기도 양평군",
        'gyeongbuk_region': "경상북도 포항시 남구, 경상북도 포항시 북구, 경상북도 경주시, 경상북도 김천시, 경상북도 안동시, 경상북도 구미시, 경상북도 영주시, 경상북도 영천시, 경상북도 상주시, 경상북도 문경시, 경상북도 경산시, 경상북도 의성군, 경상북도 청송군, 경상북도 영양군, 경상북도 영덕군, 경상북도 청도군, 경상북도 고령군, 경상북도 성주군, 경상북도 칠곡군, 경상북도 예천군, 경상북도 봉화군, 경상북도 울진군, 경상북도 울릉군",
        'gyeongnam_region': "경상남도 창원시 의창구, 경상남도 창원시 성산구, 경상남도 창원시 마산합포구, 경상남도 창원시 마산회원구, 경상남도 창원시 진해구, 경상남도 진주시, 경상남도 통영시, 경상남도 사천시, 경상남도 김해시, 경상남도 밀양시, 경상남도 거제시, 경상남도 양산시, 경상남도 의령군, 경상남도 함안군, 경상남도 창녕군, 경상남도 고성군, 경상남도 남해군, 경상남도 하동군, 경상남도 산청군, 경상남도 함양군, 경상남도 거창군, 경상남도 합천군",
        'sejong_region': "36000"
    }

# 지역명과 대표명 매핑
region_mapping = {
    regions['all_region']: '전국',
    regions['seoul_region']: '서울특별시',
    regions['busan_region']: '부산광역시',
    regions['gwangju_region']: '광주광역시',
    regions['daegu_region']: '대구광역시',
    regions['daejeon_region']: '대전광역시',
    regions['changwon_region']: '경상남도 창원시',
    regions['ulsan_region']: '울산광역시',
    regions['incheon_region']: '인천광역시',
    regions['jeonnam_region']: '전라남도',
    regions['gangwon_region']: '강원특별자치도',
    regions['bucheon_region']: '경기도 부천시',
    regions['cheongju_region']: '충청북도 청주시',
    regions['yongin_region']: '경기도 용인시',
    regions['chungbuk_region']: '충청북도',
    regions['jeonbuk_region']: '전북특별자치도',
    regions['gyeonggi_region']: '경기도',
    regions['gyeongbuk_region']: '경상북도',
    regions['gyeongnam_region']: '경상남도',
    regions['sejong_region']: '세종특별자치시'
}

# 변경 전 데이터 확인
print("변경 전 지역별 정책 수:")
print(df['정책거주지역코드'].value_counts().head(10))

# 각 지역을 대표명으로 변경
total_changed = 0
for region_string, representative_name in region_mapping.items():
    # 해당 지역과 일치하는 항목을 대표명으로 변경
    mask = df['정책거주지역코드'] == region_string
    changed_count = mask.sum()
    
    if changed_count > 0:
        df.loc[mask, '정책거주지역코드'] = representative_name
        print(f"'{representative_name}'으로 변경된 행 수: {changed_count}")
        total_changed += changed_count

print(f"\n총 변경된 행 수: {total_changed}")

# 변경 후 데이터 확인
print("\n변경 후 지역별 정책 수:")
print(df['정책거주지역코드'].value_counts().head(15))

# 데이터 몇 건 확인하기
print("\n변경 후 대표 지역명을 가진 데이터 샘플:")
representative_regions = ['전국', '서울특별시', '부산광역시', '대구광역시', '광주광역시']
for region in representative_regions:
    count = (df['정책거주지역코드'] == region).sum()
    if count > 0:
        print(f"\n{region} ({count}건):")
        print(df[df['정책거주지역코드'] == region][['정책명', '정책거주지역코드']].head(2))

# 중복 카테고리 제거
print("\n중복 카테고리 제거 중...")

def remove_duplicate_categories(category_string):
    """
    쉼표로 분리된 카테고리 문자열에서 중복을 제거하는 함수
    
    Args:
        category_string: 쉼표로 구분된 카테고리 문자열 (예: "교육, 취업, 교육")
    
    Returns:
        중복이 제거된 카테고리 문자열 (예: "교육, 취업")
    """
    # None이나 NaN인 경우 그대로 반환
    if pd.isna(category_string):
        return category_string
    
    # 문자열이 아닌 경우 그대로 반환
    if not isinstance(category_string, str):
        return category_string
    
    # 쉼표로 분리
    categories = category_string.split(',')
    
    # 각 카테고리의 공백 제거 및 중복 제거 (순서 유지)
    unique_categories = []
    for category in categories:
        cleaned_category = category.strip()
        if cleaned_category and cleaned_category not in unique_categories:
            unique_categories.append(cleaned_category)
    
    # 다시 쉼표로 연결하여 반환
    return ', '.join(unique_categories)

# 원본 데이터 백업 (비교용)
original_categories = df['정책대분류명'].copy()

# 중복 제거 함수 적용
df['정책대분류명'] = df['정책대분류명'].apply(remove_duplicate_categories)

# 변경 사항 확인
changed_rows = original_categories != df['정책대분류명']
changed_count = changed_rows.sum()

print(f"총 {len(df)}개 행 중 {changed_count}개 행이 변경되었습니다. ({changed_count/len(df)*100:.2f}%)")

# 변경된 행들의 예시 출력
if changed_count > 0:
    print("\n변경된 데이터 예시:")
    comparison_df = pd.DataFrame({
        '변경 전': original_categories[changed_rows],
        '변경 후': df['정책대분류명'][changed_rows]
    })
    print(comparison_df.head(10))
else:
    print("\n중복이 발견되지 않았습니다.")

# 최종 데이터 저장
print("\n최종 데이터 저장 중...")
df.to_excel('청년정책목록_전체_매핑완료.xlsx', index=False)
print("Excel 파일 저장 완료: 청년정책목록_전체_매핑완료.xlsx")

# CSV 파일로도 저장 (주석 처리됨)
df.to_csv('청년정책목록_전체_매핑완료.csv', encoding='utf-8', index=False)

print("\n전처리 작업이 완료되었습니다!")
print(f"최종 데이터 크기: {df.shape}")
print(f"컬럼 수: {len(df.columns)}")

# 신청기간 데이터 분리
print("\n신청기간 데이터 분리 중...")

def split_application_period(period_string):
    """
    신청기간 문자열을 시작일자와 종료일자로 분리하는 함수
    
    Args:
        period_string: 신청기간 문자열 (예: "20250523 ~ 20250623")
    
    Returns:
        tuple: (시작일자, 종료일자) 형태의 튜플
    """
    # None이나 NaN인 경우 None 반환
    if pd.isna(period_string):
        return None, None
    
    # 문자열이 아닌 경우 None 반환
    if not isinstance(period_string, str):
        return None, None
    
    # '~' 기준으로 분리
    if '~' in period_string:
        parts = period_string.split('~')
        
        # 분리된 부분이 2개인 경우
        if len(parts) == 2:
            start_date = parts[0].strip()
            end_date = parts[1].strip()
            
            # 빈 문자열이 아닌 경우만 반환
            start_date = start_date if start_date else None
            end_date = end_date if end_date else None
            
            return start_date, end_date
    
    # '~'가 없거나 분리할 수 없는 경우
    # 전체 문자열을 시작일자로, 종료일자는 None으로 설정
    period_string = period_string.strip()
    return period_string if period_string else None, None

def convert_to_datetime(date_string):
    """YYYYMMDD 형식의 문자열을 datetime으로 변환"""
    if pd.isna(date_string) or not isinstance(date_string, str):
        return None
    
    # 8자리 숫자인지 확인
    if len(date_string) == 8 and date_string.isdigit():
        try:
            return pd.to_datetime(date_string, format='%Y%m%d')
        except:
            return None
    return None

# 신청기간 데이터 확인
print("신청기간 데이터 샘플:")
print(df['신청기간'].head(10))
print(f"\n신청기간 데이터 타입: {df['신청기간'].dtype}")
print(f"신청기간 결측값 개수: {df['신청기간'].isna().sum()}")

# 고유한 신청기간 패턴 확인
unique_patterns = df['신청기간'].value_counts().head(10)
print(f"\n신청기간 패턴 (상위 10개):")
print(unique_patterns)

# 신청기간 분리 적용
print("\n신청기간 분리 적용 중...")
split_results = df['신청기간'].apply(split_application_period)

# 분리된 결과를 새로운 컬럼으로 추가 (문자열로 먼저 저장)
df['신청시작일자'] = [result[0] for result in split_results]
df['신청종료일자'] = [result[1] for result in split_results]

# 분리 결과 확인
print("분리 완료!")
print(f"신청시작일자 결측값: {df['신청시작일자'].isna().sum()}개")
print(f"신청종료일자 결측값: {df['신청종료일자'].isna().sum()}개")

# 분리 결과 샘플 확인
print("\n분리 결과 샘플 (문자열 형태):")
sample_df = pd.DataFrame({
    '원본 신청기간': df['신청기간'].head(10),
    '신청시작일자': df['신청시작일자'].head(10),
    '신청종료일자': df['신청종료일자'].head(10)
})
print(sample_df)

# 기존 컬럼을 datetime 형식으로 변환 (덮어쓰기)
print("\n기존 컬럼을 datetime 형식으로 변환 중...")
df['신청시작일자'] = df['신청시작일자'].apply(convert_to_datetime)
df['신청종료일자'] = df['신청종료일자'].apply(convert_to_datetime)

converted_start = df['신청시작일자'].notna().sum()
converted_end = df['신청종료일자'].notna().sum()

print(f"datetime 변환 완료:")
print(f"신청시작일자: {converted_start}개")
print(f"신청종료일자: {converted_end}개")

# 기존 신청기간 컬럼 제거
print("\n기존 신청기간 컬럼 제거 중...")
columns_before = df.columns.tolist()
df = df.drop(columns=['신청기간'])
columns_after = df.columns.tolist()

print(f"컬럼 제거 완료!")
print(f"제거 전 컬럼 수: {len(columns_before)}")
print(f"제거 후 컬럼 수: {len(columns_after)}")
print(f"제거된 컬럼: 신청기간")

# 최종 결과 확인
print("\n최종 컬럼 구성:")
date_columns = ['신청시작일자', '신청종료일자']
print(df[date_columns].head())

# 데이터 타입 확인
print(f"\n신청시작일자 데이터 타입: {df['신청시작일자'].dtype}")
print(f"신청종료일자 데이터 타입: {df['신청종료일자'].dtype}")

# 유효한 날짜 범위 확인
valid_start_dates = df['신청시작일자'].dropna()
valid_end_dates = df['신청종료일자'].dropna()

if len(valid_start_dates) > 0:
    print(f"\n신청시작일자 범위:")
    print(f"최소값: {valid_start_dates.min()}")
    print(f"최대값: {valid_start_dates.max()}")

if len(valid_end_dates) > 0:
    print(f"\n신청종료일자 범위:")
    print(f"최소값: {valid_end_dates.min()}")
    print(f"최대값: {valid_end_dates.max()}")

# 신청기간 길이 계산 (신청시작일자와 신청종료일자가 모두 있는 경우)
valid_both = df[(df['신청시작일자'].notna()) & (df['신청종료일자'].notna())]
if len(valid_both) > 0:
    valid_both_copy = valid_both.copy()
    valid_both_copy['신청기간_일수'] = (valid_both_copy['신청종료일자'] - valid_both_copy['신청시작일자']).dt.days
    print(f"\n신청기간 길이 통계 (일 단위):")
    print(valid_both_copy['신청기간_일수'].describe())

# 년도별 분포 확인
if len(valid_start_dates) > 0:
    start_years = valid_start_dates.dt.year.value_counts().sort_index()
    print(f"\n신청시작일자 년도별 분포:")
    print(start_years)

print(f"\n최종 날짜 관련 컬럼:")
print(f"- 신청시작일자: datetime 형태")
print(f"- 신청종료일자: datetime 형태")

print("\n신청기간 분리 및 datetime 변환 완료!")

# ...existing code...

