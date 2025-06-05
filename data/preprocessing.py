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

def load_all_datasets(
    policy_csv='청년정책목록_전체.csv',
    code_csv='청년정책_전체코드매핑.csv',
    region_excel='법정동 기준 시군구 단위.xlsx',
    region_txt='법정동코드 전체자료.txt'
):
    """
    모든 주요 데이터를 불러옵니다.

    Returns:
        df_all: 정책 전체 목록
        df_code: 코드 매핑 테이블
        df_region: 시군구 통합 버전
        df_region2: 법정동 코드 전체
    """
    df_all = pd.read_csv(policy_csv, encoding='utf-8')
    df_code = pd.read_csv(code_csv, encoding='utf-8')
    df_region = pd.read_excel(region_excel, sheet_name="통합 버전")
    df_region2 = pd.read_csv(region_txt, encoding='cp949', sep='\t')

    return df_all, df_code, df_region, df_region2


def get_matching_code_columns(df: pd.DataFrame, df_code: pd.DataFrame):
    """
    df_code의 '코드그룹명'을 기준으로, df에서 해당하는 컬럼명을 찾음

    Args:
        df (pd.DataFrame): 전체 정책 데이터프레임
        df_code (pd.DataFrame): 코드 매핑 데이터프레임 (코드그룹명 컬럼 포함)

    Returns:
        List[str]: df에 존재하는 코드 그룹 컬럼명 리스트
    """
    unique_code_groups = df_code['코드그룹명'].unique()
    matching_columns = [col for col in df.columns if col in unique_code_groups]
    return matching_columns


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
    # print(f"{column_name}: 총 {len(df)}개 중 {mapped_count}개 매핑 완료 ({mapped_count/len(df)*100:.2f}%)")
    
    # 매핑된 샘플 몇 개 보여주기
    if mapped_count > 0:
        sample_df = pd.DataFrame({
            '원래 코드': original_values.head(5),
            '매핑된 이름': df[column_name].head(5)
        })
        print(sample_df)
    
    return df
# 모듈화화
# 매칭되는 모든 컬럼에 대해 매핑 실행
def apply_code_mappings(df: pd.DataFrame, df_code: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    지정된 컬럼들에 대해 df_code를 참조하여 코드값을 한글명으로 매핑합니다.

    Args:
        df (pd.DataFrame): 매핑 대상 데이터프레임
        df_code (pd.DataFrame): 코드 매핑표 (컬럼: 코드값, 한글명, 코드그룹명)
        columns (list): 매핑할 컬럼명 리스트

    Returns:
        pd.DataFrame: 매핑이 적용된 데이터프레임
    """
    for column in columns:
        df = map_codes_to_names(df, df_code, column)
    return df




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
   
    
    # 매핑된 값들의 분포 확인
    value_counts = df[column_name].value_counts()

    
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
    
    
    return df





# 1. 지역 코드-시군구명 매핑 딕셔너리 생성
def create_region_code_map(df_region: pd.DataFrame, code_col: str = '시군구_코드_법정동기준', name_col: str = '시군구') -> dict:
    """
    시군구 코드와 이름을 매핑하는 딕셔너리를 생성합니다.

    Args:
        df_region (pd.DataFrame): 시군구 코드 정보가 포함된 데이터프레임
        code_col (str): 시군구 코드 컬럼명 (기본값: '시군구_코드_법정동기준')
        name_col (str): 시군구 이름 컬럼명 (기본값: '시군구')

    Returns:
        dict: {시군구 코드 (str): 시군구 이름} 형태의 매핑 딕셔너리
    """
    df_region[code_col] = df_region[code_col].astype(str)
    return df_region.set_index(code_col)[name_col].to_dict()



# 2. 코드 변환 함수 정의 - 쉼표로 구분된 코드들도 처리
def transform_region_code(code_value, region_code_map: dict):
    """
    코드 값을 시군구 이름으로 변환합니다.

    Args:
        code_value (str): 단일 또는 쉼표로 구분된 코드 문자열
        region_code_map (dict): {코드: 시군구명} 형태의 매핑 딕셔너리

    Returns:
        str: 시군구명 또는 변환 실패 시 원래 값
    """
    if pd.isna(code_value):
        return code_value

    if isinstance(code_value, str) and ',' in code_value:
        codes = code_value.split(',')
        transformed_codes = []

        for code in codes:
            code = code.strip()
            region_name = region_code_map.get(code)
            transformed_codes.append(region_name if region_name else code)

        return ', '.join(transformed_codes) if transformed_codes else code_value

    else:
        return region_code_map.get(code_value, code_value)


# 3. 원래 값 저장 (비교용)
def map_and_compare_region_codes(df: pd.DataFrame, code_col: str, transform_func) -> tuple[pd.DataFrame, int]:
    """
    지역 코드 컬럼을 시군구명으로 매핑하고, 매핑 전후 비교 샘플과 매핑된 개수를 반환합니다.

    Args:
        df (pd.DataFrame): 원본 데이터프레임
        code_col (str): 지역 코드 컬럼명
        transform_func (function): 지역 코드를 시군구명으로 변환하는 함수

    Returns:
        tuple:
            - sample_df (pd.DataFrame): 매핑 전후 10개 샘플 비교
            - mapped_count (int): 매핑이 성공한 (NaN이 아닌) 개수
    """
    # 원래 값 저장
    original_codes = df[code_col].copy()

    # 매핑 적용
    df[code_col] = df[code_col].apply(transform_func)

    # 매핑 결과 개수
    mapped_count = df[code_col].notna().sum()

    # 비교 샘플 생성
    sample_df = pd.DataFrame({
        '원래 코드': original_codes.head(10),
        '매핑된 시군구명': df[code_col].head(10)
    })

    return sample_df, mapped_count









def create_region_code_map(df_region2: pd.DataFrame) -> dict:
    """
    법정동코드 데이터에서 '존재' 상태의 코드만 추출하고, 
    법정동코드 앞 5자리를 기준으로 중복 제거하여 법정동명 매핑 딕셔너리를 생성합니다.

    Args:
        df_region2 (pd.DataFrame): '법정동코드 전체자료.txt'에서 읽어온 데이터프레임

    Returns:
        dict: {'법정동코드_5자리': '법정동명'} 형태의 매핑 딕셔너리
    """
    # '존재'하는 코드만 필터링
    filtered = df_region2[df_region2['폐지여부'] == '존재'].copy()

    # 앞 5자리 기준 처리
    filtered['법정동코드_5자리'] = filtered['법정동코드'].astype(str).str[:5]

    # 중복 제거 후 매핑 생성
    unique_df = filtered.drop_duplicates(subset=['법정동코드_5자리'])
    region_code_map = unique_df.set_index('법정동코드_5자리')['법정동명'].to_dict()

    return region_code_map




def transform_region_code(code_value, region_code_map: dict):
    """
    시군구 코드값을 시군구명으로 변환합니다.

    Args:
        code_value (str): 단일 코드 또는 쉼표로 구분된 복수 코드 문자열
        region_code_map (dict): {시군구 코드(앞 5자리): 시군구명} 형태의 매핑 딕셔너리

    Returns:
        str: 시군구명 또는 변환 실패 시 원래 값
    """
    if pd.isna(code_value):
        return code_value

    # 복수 코드 처리
    if isinstance(code_value, str) and ',' in code_value:
        codes = code_value.split(',')
        transformed_codes = []

        for code in codes:
            code = code.strip()
            code_5digits = code[:5] if len(code) >= 5 else code
            region_name = region_code_map.get(code_5digits)
            transformed_codes.append(region_name if region_name else code)

        return ', '.join(transformed_codes) if transformed_codes else code_value

    # 단일 코드 처리
    else:
        if isinstance(code_value, str) and len(code_value) >= 5:
            code_5digits = code_value[:5]
            region_name = region_code_map.get(code_5digits)
            if region_name:
                return region_name

        return code_value


# 4. 원래 값 저장 및 변환 함수 적용
def apply_region_code_mapping(df: pd.DataFrame, column: str, transform_func) -> pd.DataFrame:
    """
    지정된 컬럼에 변환 함수를 적용하여 값을 변경하고, 
    원래 값을 '원래_{컬럼명}'으로 저장합니다.

    Args:
        df (pd.DataFrame): 변환 대상 데이터프레임
        column (str): 변환할 컬럼명 (예: '정책거주지역코드')
        transform_func (callable): 각 값에 적용할 변환 함수

    Returns:
        pd.DataFrame: 변환된 결과가 반영된 데이터프레임
    """
    df = df.copy()
    df[f'원래_{column}'] = df[column].copy()
    df[column] = df[column].apply(transform_func)
    return df




def map_region_to_representative(df, column_name="정책거주지역코드") -> pd.DataFrame:
    """
    정책거주지역코드 값을 대표 지역명으로 일괄 변환하는 함수.
    지역 전체 문자열을 기반으로 대표 지역명으로 매핑한다.
    """
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

    total_changed = 0
    for region_string, representative_name in region_mapping.items():
        mask = df[column_name] == region_string
        changed_count = mask.sum()
        if changed_count > 0:
            df.loc[mask, column_name] = representative_name
            print(f"'{representative_name}'으로 변경된 행 수: {changed_count}")
            total_changed += changed_count

    return df




def remove_duplicate_categories(category_string):
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





# CSV 파일로도 저장 (주석 처리됨)
def save_dataframe(df: pd.DataFrame, filename: str, filetype: str = "excel", encoding: str = "utf-8") -> None:
    """
    DataFrame을 엑셀 또는 CSV 형식으로 저장하는 함수.

    Parameters:
        df (pd.DataFrame): 저장할 데이터프레임
        filename (str): 저장할 파일 이름 (확장자는 생략 가능)
        filetype (str): "excel" 또는 "csv"
        encoding (str): CSV 저장 시 사용할 인코딩 (기본값: "utf-8")
    """
    if filetype == "excel":
        if not filename.endswith(".xlsx"):
            filename += ".xlsx"
        df.to_excel(filename, index=False)
    elif filetype == "csv":
        if not filename.endswith(".csv"):
            filename += ".csv"
        df.to_csv(filename, index=False, encoding=encoding)
    else:
        raise ValueError("filetype은 'excel' 또는 'csv' 중 하나여야 합니다.")


