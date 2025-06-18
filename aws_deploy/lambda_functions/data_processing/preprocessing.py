"""
청년정책 데이터 전처리 스크립트
- 코드 매핑 및 지역 정보 변환
- 중복 카테고리 제거
- 최종 데이터 저장
"""

import pandas as pd
from datetime import datetime


def map_codes_to_names(df, df_code, column_name):
    """코드를 코드명으로 매핑하는 함수"""
    code_map = df_code[df_code['코드그룹명'] == column_name].set_index('코드')['코드명'].to_dict()
    df[column_name] = df[column_name].map(code_map)
    return df


def create_code_mapping_function(df_code, code_group_name):
    """특정 코드그룹에 대한 매핑 함수를 생성합니다."""
    code_map = df_code[df_code['코드그룹명'] == code_group_name].set_index('코드')['코드명'].to_dict()
    
    def transform_code(code_value):
        if pd.isna(code_value):
            return code_value
            
        if isinstance(code_value, str) and ',' in code_value:
            codes = code_value.split(',')
            transformed_codes = []
            
            for code in codes:
                if code.strip().startswith('00'):
                    try:
                        transformed_code = int(code.strip()[2:])
                        code_name = code_map.get(transformed_code)
                        if code_name:
                            transformed_codes.append(code_name)
                    except ValueError:
                        transformed_codes.append(code.strip())
                else:
                    transformed_codes.append(code.strip())
                    
            return ', '.join(transformed_codes) if transformed_codes else code_value
        
        elif isinstance(code_value, str) and code_value.startswith('00'):
            try:
                transformed_code = int(code_value[2:])
                return code_map.get(transformed_code, code_value)
            except ValueError:
                return code_value
        
        return code_value
    
    return transform_code


def apply_code_mapping(df, df_code, column_name, code_group_name):
    """데이터프레임의 특정 컬럼에 코드 매핑을 적용합니다."""
    transform_function = create_code_mapping_function(df_code, code_group_name)
    df[column_name] = df[column_name].apply(transform_function)
    return df


def transform_region_code(code_value, region_code_map):
    """지역 코드를 지역명으로 변환하는 함수"""
    if pd.isna(code_value):
        return code_value
        
    if isinstance(code_value, str) and ',' in code_value:
        codes = code_value.split(',')
        transformed_codes = []
        
        for code in codes:
            code = code.strip()
            region_name = region_code_map.get(code)
            if region_name:
                transformed_codes.append(region_name)
            else:
                transformed_codes.append(code)
        return ', '.join(transformed_codes) if transformed_codes else code_value
    
    else:
        return region_code_map.get(code_value, code_value)


def transform_region_code_detailed(code_value, region_code_map):
    """법정동코드 기반 상세 지역 코드를 변환하는 함수"""
    if pd.isna(code_value):
        return code_value
        
    if isinstance(code_value, str) and ',' in code_value:
        codes = code_value.split(',')
        transformed_codes = []
        
        for code in codes:
            code = code.strip()
            code_5digits = code[:5] if len(code) >= 5 else code
            region_name = region_code_map.get(code_5digits)
            if region_name:
                transformed_codes.append(region_name)
            else:
                transformed_codes.append(code)
        return ', '.join(transformed_codes) if transformed_codes else code_value
    
    else:
        if isinstance(code_value, str) and len(code_value) >= 5:
            code_5digits = code_value[:5]
            region_name = region_code_map.get(code_5digits)
            if region_name:
                return region_name
        return code_value


# def transform_requirement_code(code_value, threshold=4):
#     """
#     요건코드에서 쉼표로 분리된 항목이 임계값 이상이면 '제한없음'으로 변환하는 통합 함수
    
#     Args:
#         code_value: 변환할 코드 값
#         threshold: 임계값 (기본값: 4)
    
#     Returns:
#         변환된 코드 값 또는 '제한없음'
#     """
#     if pd.isna(code_value) or not isinstance(code_value, str):
#         return code_value
    
#     # 쉼표로 분리하고 공백 제거
#     items = [item.strip() for item in code_value.split(',') if item.strip()]
    
#     # 임계값 이상이면 '제한없음'으로 변환
#     if len(items) >= threshold:
#         return '제한없음'
    
#     return code_value


# def transform_employment_status(code_value):
#     """
#     정책취업요건코드에서 특정 취업 상태를 '비정규직'로 변환하는 함수
    
#     Args:
#         code_value: 변환할 코드 값
    
#     Returns:
#         변환된 코드 값
#     """
#     if pd.isna(code_value) or not isinstance(code_value, str):
#         return code_value
    
#     # 변환 대상 취업 상태 목록
#     target_statuses = ['프리랜서', '일용근로자', '단기근로자']
    
#     # 쉼표로 분리된 경우 처리
#     if ',' in code_value:
#         items = [item.strip() for item in code_value.split(',') if item.strip()]
#         transformed_items = []
        
#         for item in items:
#             if item in target_statuses:
#                 transformed_items.append('비정규직')
#             else:
#                 transformed_items.append(item)
        
#         return ', '.join(transformed_items)
#     # 단일 값인 경우 처리
#     else:
#         if code_value.strip() in target_statuses:
#             return '비정규직'
#         return code_value

def remove_duplicate_categories(category_string):
    """쉼표로 분리된 카테고리 문자열에서 중복을 제거하는 함수"""
    if pd.isna(category_string) or not isinstance(category_string, str):
        return category_string
    
    categories = category_string.split(',')
    unique_categories = []
    for category in categories:
        cleaned_category = category.strip()
        if cleaned_category and cleaned_category not in unique_categories:
            unique_categories.append(cleaned_category)
    
    return ', '.join(unique_categories)


def reclassify_policy_category(category_string):
    """정책대분류명을 주거, 일자리, 기타로 재분류하는 함수"""
    if pd.isna(category_string) or not isinstance(category_string, str):
        return '기타'
    
    category_lower = category_string.lower()
    
    # 주거 관련 키워드 확인
    if '주거' in category_lower:
        return '주거'
    
    # 일자리 관련 키워드 확인
    if '일자리' in category_lower:
        return '일자리'
    
    if '교육' in category_lower:
        return '교육'
    
    # 그 외에는 기타로 분류
    return '기타'


def split_application_period(period_string):
    """신청기간 문자열을 시작일자와 종료일자로 분리하는 함수"""
    if pd.isna(period_string) or not isinstance(period_string, str):
        return None, None
    
    if '~' in period_string:
        parts = period_string.split('~')
        if len(parts) == 2:
            start_date = parts[0].strip()
            end_date = parts[1].strip()
            start_date = start_date if start_date else None
            end_date = end_date if end_date else None
            return start_date, end_date
    
    period_string = period_string.strip()
    return period_string if period_string else None, None


def convert_to_datetime(date_string):
    """YYYYMMDD 형식의 문자열을 datetime으로 변환"""
    if pd.isna(date_string) or not isinstance(date_string, str):
        return None
    
    if len(date_string) == 8 and date_string.isdigit():
        try:
            return pd.to_datetime(date_string, format='%Y%m%d')
        except:
            return None
    return None


def get_region_mappings():
    """지역 매핑 정보를 반환하는 함수"""
    regions = {
        'all_region': "서울 종로구, 서울 중구, 서울 용산구, 서울 성동구, 서울 광진구, 서울 동대문구, 서울 중랑구, 서울 성북구, 서울 강북구, 서울 도봉구, 서울 노원구, 서울 은평구, 서울 서대문구, 서울 마포구, 서울 양천구, 서울 강서구, 서울 구로구, 서울 금천구, 서울 영등포구, 서울 동작구, 서울 관악구, 서울 서초구, 서울 강남구, 서울 송파구, 서울 강동구, 부산 중구, 부산 서구, 부산 동구, 부산 영도구, 부산 부산진구, 부산 동래구, 부산 남구, 부산 북구, 부산 해운대구, 부산 사하구, 부산 금정구, 부산 강서구, 부산 연제구, 부산 수영구, 부산 사상구, 부산 기장군, 대구 중구, 대구 동구, 대구 서구, 대구 남구, 대구 북구, 대구 수성구, 대구 달서구, 대구 달성군, 대구광역시 군위군, 인천 중구, 인천 동구, 인천 미추홀구, 인천 연수구, 인천 남동구, 인천 부평구, 인천 계양구, 인천 서구, 인천 강화군, 인천 옹진군, 광주 동구, 광주 서구, 광주 남구, 광주 북구, 광주 광산구, 대전 동구, 대전 중구, 대전 서구, 대전 유성구, 대전 대덕구, 울산 중구, 울산 남구, 울산 동구, 울산 북구, 울산 울주군, 세종특별자치시, 경기도 수원시 장안구, 경기도 수원시 권선구, 경기도 수원시 팔달구, 경기도 수원시 영통구, 경기도 성남시 수정구, 경기도 성남시 중원구, 경기도 성남시 분당구, 경기도 의정부시, 경기도 안양시 만안구, 경기도 안양시 동안구, 경기도 부천시 원미구 , 경기도 부천시 소사구 , 경기도 부천시 오정구 , 경기도 광명시, 경기도 평택시, 경기도 동두천시, 경기도 안산시 상록구, 경기도 안산시 단원구, 경기도 고양시 덕양구, 경기도 고양시 일산동구, 경기도 고양시 일산서구, 경기도 과천시, 경기도 구리시, 경기도 남양주시, 경기도 오산시, 경기도 시흥시, 경기도 군포시, 경기도 의왕시, 경기도 하남시, 경기도 용인시 처인구, 경기도 용인시 기흥구, 경기도 용인시 수지구, 경기도 파주시, 경기도 이천시, 경기도 안성시, 경기도 김포시, 경기도 화성시, 경기도 광주시, 경기도 양주시, 경기도 포천시, 경기도 여주시, 경기도 연천군, 경기도 가평군, 경기도 양평군, 충청북도 청주시 상당구, 충청북도 청주시 서원구, 충청북도 청주시 흥덕구, 충청북도 청주시 청원구, 충청북도 충주시, 충청북도 제천시, 충청북도 보은군, 충청북도 옥천군, 충청북도 영동군, 충청북도 증평군, 충청북도 진천군, 충청북도 괴산군, 충청북도 음성군, 충청북도 단양군, 충청남도 천안시 동남구, 충청남도 천안시 서북구, 충청남도 공주시, 충청남도 보령시, 충청남도 아산시, 충청남도 서산시, 충청남도 논산시, 충청남도 계룡시, 충청남도 당진시, 충청남도 금산군, 충청남도 부여군, 충청남도 서천군, 충청남도 청양군, 충청남도 홍성군, 충청남도 예산군, 충청남도 태안군, 전라남도 목포시, 전라남도 여수시, 전라남도 순천시, 전라남도 나주시, 전라남도 광양시, 전라남도 담양군, 전라남도 곡성군, 전라남도 구례군, 전라남도 고흥군, 전라남도 보성군, 전라남도 화순군, 전라남도 장흥군, 전라남도 강진군, 전라남도 해남군, 전라남도 영암군, 전라남도 무안군, 전라남도 함평군, 전라남도 영광군, 전라남도 장성군, 전라남도 완도군, 전라남도 진도군, 전라남도 신안군, 경상북도 포항시 남구, 경상북도 포항시 북구, 경상북도 경주시, 경상북도 김천시, 경상북도 안동시, 경상북도 구미시, 경상북도 영주시, 경상북도 영천시, 경상북도 상주시, 경상북도 문경시, 경상북도 경산시, 경상북도 의성군, 경상북도 청송군, 경상북도 영양군, 경상북도 영덕군, 경상북도 청도군, 경상북도 고령군, 경상북도 성주군, 경상북도 칠곡군, 경상북도 예천군, 경상북도 봉화군, 경상북도 울진군, 경상북도 울릉군, 경상남도 창원시 의창구, 경상남도 창원시 성산구, 경상남도 창원시 마산합포구, 경상남도 창원시 마산회원구, 경상남도 창원시 진해구, 경상남도 진주시, 경상남도 통영시, 경상남도 사천시, 경상남도 김해시, 경상남도 밀양시, 경상남도 거제시, 경상남도 양산시, 경상남도 의령군, 경상남도 함안군, 경상남도 창녕군, 경상남도 고성군, 경상남도 남해군, 경상남도 하동군, 경상남도 산청군, 경상남도 함양군, 경상남도 거창군, 경상남도 합천군, 제주 제주시, 제주 서귀포시, 강원특별자치도 춘천시, 강원특별자치도 원주시, 강원특별자치도 강릉시, 강원특별자치도 동해시, 강원특별자치도 태백시, 강원특별자치도 속초시, 강원특별자치도 삼척시, 강원특별자치도 홍천군, 강원특별자치도 횡성군, 강원특별자치도 영월군, 강원특별자치도 평창군, 강원특별자치도 정선군, 강원특별자치도 철원군, 강원특별자치도 화천군, 강원특별자치도 양구군, 강원특별자치도 인제군, 강원특별자치도 고성군, 강원특별자치도 양양군, 전북특별자치도 전주시 완산구, 전북특별자치도 전주시 덕진구, 전북특별자치도 군산시, 전북특별자치도 익산시, 전북특별자치도 정읍시, 전북특별자치도 남원시, 전북특별자치도 김제시, 전북특별자치도 완주군, 전북특별자치도 진안군, 전북특별자치도 무주군, 전북특별자치도 장수군, 전북특별자치도 임실군, 전북특별자치도 순창군, 전북특별자치도 고창군, 전북특별자치도 부안군",
        'seoul_region': "서울 종로구, 서울 중구, 서울 용산구, 서울 성동구, 서울 광진구, 서울 동대문구, 서울 중랑구, 서울 성북구, 서울 강북구, 서울 도봉구, 서울 노원구, 서울 은평구, 서울 서대문구, 서울 마포구, 서울 양천구, 서울 강서구, 서울 구로구, 서울 금천구, 서울 영등포구, 서울 동작구, 서울 관악구, 서울 서초구, 서울 강남구, 서울 송파구, 서울 강동구",
        'busan_region': "부산 중구, 부산 서구, 부산 동구, 부산 영도구, 부산 부산진구, 부산 동래구, 부산 남구, 부산 북구, 부산 해운대구, 부산 사하구, 부산 금정구, 부산 강서구, 부산 연제구, 부산 수영구, 부산 사상구, 부산 기장군",
        'gwangju_region': "광주 동구, 광주 서구, 광주 남구, 광주 북구, 광주 광산구",
        'daegu_region': "대구 중구, 대구 동구, 대구 서구, 대구 남구, 대구 북구, 대구 수성구, 대구 달서구, 대구 달성군, 대구광역시 군위군",
        'daejeon_region': "대전 동구, 대전 중구, 대전 서구, 대전 유성구, 대전 대덕구",
        'ulsan_region': "울산 중구, 울산 남구, 울산 동구, 울산 북구, 울산 울주군",
        'incheon_region': "인천 중구, 인천 동구, 인천 미추홀구, 인천 연수구, 인천 남동구, 인천 부평구, 인천 계양구, 인천 서구, 인천 강화군, 인천 옹진군",
        'jeonnam_region': "전라남도 목포시, 전라남도 여수시, 전라남도 순천시, 전라남도 나주시, 전라남도 광양시, 전라남도 담양군, 전라남도 곡성군, 전라남도 구례군, 전라남도 고흥군, 전라남도 보성군, 전라남도 화순군, 전라남도 장흥군, 전라남도 강진군, 전라남도 해남군, 전라남도 영암군, 전라남도 무안군, 전라남도 함평군, 전라남도 영광군, 전라남도 장성군, 전라남도 완도군, 전라남도 진도군, 전라남도 신안군",
        'gangwon_region': "강원특별자치도 춘천시, 강원특별자치도 원주시, 강원특별자치도 강릉시, 강원특별자치도 동해시, 강원특별자치도 태백시, 강원특별자치도 속초시, 강원특별자치도 삼척시, 강원특별자치도 홍천군, 강원특별자치도 횡성군, 강원특별자치도 영월군, 강원특별자치도 평창군, 강원특별자치도 정선군, 강원특별자치도 철원군, 강원특별자치도 화천군, 강원특별자치도 양구군, 강원특별자치도 인제군, 강원특별자치도 고성군, 강원특별자치도 양양군",
        'chungbuk_region': "충청북도 청주시 상당구, 충청북도 청주시 서원구, 충청북도 청주시 흥덕구, 충청북도 청주시 청원구, 충청북도 충주시, 충청북도 제천시, 충청북도 보은군, 충청북도 옥천군, 충청북도 영동군, 충청북도 증평군, 충청북도 진천군, 충청북도 괴산군, 충청북도 음성군, 충청북도 단양군",
        'jeonbuk_region': "전북특별자치도 전주시 완산구, 전북특별자치도 전주시 덕진구, 전북특별자치도 군산시, 전북특별자치도 익산시, 전북특별자치도 정읍시, 전북특별자치도 남원시, 전북특별자치도 김제시, 전북특별자치도 완주군, 전북특별자치도 진안군, 전북특별자치도 무주군, 전북특별자치도 장수군, 전북특별자치도 임실군, 전북특별자치도 순창군, 전북특별자치도 고창군, 전북특별자치도 부안군",
        'gyeonggi_region': "경기도 수원시 장안구, 경기도 수원시 권선구, 경기도 수원시 팔달구, 경기도 수원시 영통구, 경기도 성남시 수정구, 경기도 성남시 중원구, 경기도 성남시 분당구, 경기도 의정부시, 경기도 안양시 만안구, 경기도 안양시 동안구, 경기도 부천시 원미구 , 경기도 부천시 소사구 , 경기도 부천시 오정구 , 경기도 광명시, 경기도 평택시, 경기도 동두천시, 경기도 안산시 상록구, 경기도 안산시 단원구, 경기도 고양시 덕양구, 경기도 고양시 일산동구, 경기도 고양시 일산서구, 경기도 과천시, 경기도 구리시, 경기도 남양주시, 경기도 오산시, 경기도 시흥시, 경기도 군포시, 경기도 의왕시, 경기도 하남시, 경기도 용인시 처인구, 경기도 용인시 기흥구, 경기도 용인시 수지구, 경기도 파주시, 경기도 이천시, 경기도 안성시, 경기도 김포시, 경기도 화성시, 경기도 광주시, 경기도 양주시, 경기도 포천시, 경기도 여주시, 경기도 연천군, 경기도 가평군, 경기도 양평군",
        'gyeongbuk_region': "경상북도 포항시 남구, 경상북도 포항시 북구, 경상북도 경주시, 경상북도 김천시, 경상북도 안동시, 경상북도 구미시, 경상북도 영주시, 경상북도 영천시, 경상북도 상주시, 경상북도 문경시, 경상북도 경산시, 경상북도 의성군, 경상북도 청송군, 경상북도 영양군, 경상북도 영덕군, 경상북도 청도군, 경상북도 고령군, 경상북도 성주군, 경상북도 칠곡군, 경상북도 예천군, 경상북도 봉화군, 경상북도 울진군, 경상북도 울릉군",
        'gyeongnam_region': "경상남도 창원시 의창구, 경상남도 창원시 성산구, 경상남도 창원시 마산합포구, 경상남도 창원시 마산회원구, 경상남도 창원시 진해구, 경상남도 진주시, 경상남도 통영시, 경상남도 사천시, 경상남도 김해시, 경상남도 밀양시, 경상남도 거제시, 경상남도 양산시, 경상남도 의령군, 경상남도 함안군, 경상남도 창녕군, 경상남도 고성군, 경상남도 남해군, 경상남도 하동군, 경상남도 산청군, 경상남도 함양군, 경상남도 거창군, 경상남도 합천군",
        'sejong_region': "36000",
        'jeju_region': "제주 제주시, 제주 서귀포시",
    }

    region_mapping = {
        regions['all_region']: '전국',
        regions['seoul_region']: '서울특별시',
        regions['busan_region']: '부산광역시',
        regions['gwangju_region']: '광주광역시',
        regions['daegu_region']: '대구광역시',
        regions['daejeon_region']: '대전광역시',
        regions['ulsan_region']: '울산광역시',
        regions['incheon_region']: '인천광역시',
        regions['jeonnam_region']: '전라남도',
        regions['gangwon_region']: '강원특별자치도',
        regions['chungbuk_region']: '충청북도',
        regions['jeonbuk_region']: '전북특별자치도',
        regions['gyeonggi_region']: '경기도',
        regions['gyeongbuk_region']: '경상북도',
        regions['gyeongnam_region']: '경상남도',
        regions['sejong_region']: '세종특별자치시',
        regions['jeju_region']: '제주특별자치도',
    }
    
    return region_mapping

def redefine_mid_category_all(df, top_col='정책대분류명', mid_col='정책중분류명', keyword_col='정책키워드명'):
    def classify(top, mid, keyword):
        top = str(top).strip().lower()
        mid = str(mid).strip().lower() if pd.notna(mid) else ""
        keyword = str(keyword).strip().lower() if pd.notna(keyword) else ""

        # ✅ 주거: 정책키워드명 기반
        if top == '주거':
            if '대출' in keyword or '금리혜택' in keyword:
                return '대출, 이자, 전월세 등 금융지원'
            elif '공공임대주택' in keyword or '임대주택' in keyword:
                return '임대주택, 기숙사 등 주거지원'
            elif any(kw in keyword for kw in ['보조금', '청년가장', '이사비', '중개비']):
                return '이사비, 부동산 중개비 등 보조금지원'
            else:
                return '그 외 질문'

        # ✅ 일자리: 정책중분류명 기반 (우선순위 기반 정리)
        elif top == '일자리':  
            # 우선순위: 창업 > 미래역량 > 재직자 > 취업
            if '창업' in mid:
                return '창업'
            elif '미래역량강화' in mid:
                return '전문인력양성, 훈련'
            elif '재직자' in mid:
                return '취업 전후 지원'
            elif '취업' in mid:
                return '취업 전후 지원'
            else:
                return '그 외 질문'

        else:
            return mid  # 기타는 원래 중분류 유지
    


    df[mid_col] = df.apply(lambda row: classify(row[top_col], row[mid_col], row[keyword_col]), axis=1)
    return df

# def standardize_metropolitan_city_names(region_value):
#     """
#     정책거주지역코드에서 광역시 이름을 정식 명칭으로 변경하는 함수
#     예: '서울 구로구' -> '서울특별시 구로구'
    
#     Args:
#         region_value: 지역 코드 값
    
#     Returns:
#         변환된 지역 코드 값
#     """
#     if pd.isna(region_value) or not isinstance(region_value, str):
#         return region_value
    
#     # 광역시 매핑 딕셔너리
#     city_mapping = {
#         '서울': '서울특별시',
#         '부산': '부산광역시',
#         '대구': '대구광역시',
#         '울산': '울산광역시',
#         '광주': '광주광역시',
#         '대전': '대전광역시',
#         '인천': '인천광역시',
#         '제주': '제주특별자치도',
#     }
    
#     # 쉼표로 분리된 경우 처리
#     if ',' in region_value:
#         regions = region_value.split(',')
#         transformed_regions = []
        
#         for region in regions:
#             region = region.strip()
#             transformed_region = region
            
#             # 각 광역시에 대해 변환 수행
#             for short_name, full_name in city_mapping.items():
#                 if region.startswith(short_name + ' '):
#                     transformed_region = region.replace(short_name + ' ', full_name + ' ', 1)
#                     break
            
#             transformed_regions.append(transformed_region)
        
#         return ', '.join(transformed_regions)
    
#     # 단일 값인 경우 처리
#     else:
#         for short_name, full_name in city_mapping.items():
#             if region_value.startswith(short_name + ' '):
#                 return region_value.replace(short_name + ' ', full_name + ' ', 1)
        
#         return region_value

def main():
    """메인 실행 함수"""
    # 데이터 로딩
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
          '등록자최상위기관코드', '등록자최상위기관코드명', '정책거주지역코드', '정책전공요건코드', '정책취업요건코드', '정책학력요건코드', '신청기간', '최초등록일시', '최종수정일시', '정책특화요건코드']
    df.columns = col

    # 코드그룹명과 일치하는 컬럼 매핑
    unique_code_groups = df_code['코드그룹명'].unique()
    matching_columns = [col for col in df.columns if col in unique_code_groups]

    for column in matching_columns:
        df = map_codes_to_names(df, df_code, column)

    # 특수 코드 필드 매핑
    mapping_configs = [
        ('정책전공요건코드', '전공조건코드'),
        ('정책학력요건코드', '자격학력코드'),
        ('정책취업요건코드', '취업상태코드'),
        ('정책특화요건코드', '특수분야코드')    ]

    for column_name, code_group_name in mapping_configs:
        df = apply_code_mapping(df, df_code, column_name, code_group_name)    
    
    # # 정책학력요건코드 변환 (3개 이상 항목이 있으면 '제한없음'으로 변환)
    # df['정책학력요건코드'] = df['정책학력요건코드'].apply(lambda x: transform_requirement_code(x, threshold=3))

    # # 정책전공요건코드 변환 (4개 이상 항목이 있으면 '제한없음'으로 변환)
    # df['정책전공요건코드'] = df['정책전공요건코드'].apply(lambda x: transform_requirement_code(x, threshold=4))    # 정책취업요건코드 변환 (4개 이상 항목이 있으면 '제한없음'으로 변환)
    # df['정책취업요건코드'] = df['정책취업요건코드'].apply(lambda x: transform_requirement_code(x, threshold=4))
    
    # # 정책취업요건코드에서 프리랜서, 일용근로자, 단기근로자를 '기타'로 변환
    # df['정책취업요건코드'] = df['정책취업요건코드'].apply(transform_employment_status)

    # 지역 코드 매핑
    df_region['시군구_코드_법정동기준'] = df_region['시군구_코드_법정동기준'].astype(str)
    region_code_map = df_region.set_index('시군구_코드_법정동기준')['시군구'].to_dict()

    df['정책거주지역코드'] = df['정책거주지역코드'].apply(lambda x: transform_region_code(x, region_code_map))

    # 법정동코드 기반 추가 지역 매핑
    filtered_df_region2 = df_region2[df_region2['폐지여부'] == '존재'].copy()
    filtered_df_region2['법정동코드_5자리'] = filtered_df_region2['법정동코드'].astype(str).str[:5]
    unique_region_df = filtered_df_region2.drop_duplicates(subset=['법정동코드_5자리'])
    region_code_map_detailed = unique_region_df.set_index('법정동코드_5자리')['법정동명'].to_dict()

    df['정책거주지역코드'] = df['정책거주지역코드'].apply(lambda x: transform_region_code_detailed(x, region_code_map_detailed))    # 지역 코드 통합 변경
    region_mapping = get_region_mappings()

    for region_string, representative_name in region_mapping.items():
        mask = df['정책거주지역코드'] == region_string
        if mask.sum() > 0:
            df.loc[mask, '정책거주지역코드'] = representative_name

    # # 광역시 이름 정식 명칭으로 변경 (예: '서울 구로구' -> '서울특별시 구로구')
    # df['정책거주지역코드'] = df['정책거주지역코드'].apply(standardize_metropolitan_city_names)

    # 중복 카테고리 제거
    df['정책대분류명'] = df['정책대분류명'].apply(remove_duplicate_categories)

    # 정책대분류명 재분류 (주거, 일자리, 기타)
    df['정책대분류명'] = df['정책대분류명'].apply(reclassify_policy_category)

    # 정책 분류 재조정: 교육 -> 일자리 재분류
    education_to_job_filter = (
        (df['정책대분류명'] == '교육') & 
        (df['정책중분류명'].str.contains('미래역량강화|취업', na=False))
    )
    df.loc[education_to_job_filter, '정책대분류명'] = '일자리'

    # 남은 교육 데이터를 기타로 분류
    remaining_education_filter = df['정책대분류명'] == '교육'
    df.loc[remaining_education_filter, '정책대분류명'] = '기타'

    # 정책중분류명 재정의
    df = redefine_mid_category_all(df)
    
    # 신청기간 분리 및 변환
    split_results = df['신청기간'].apply(split_application_period)
    df['신청시작일자'] = [result[0] for result in split_results]
    df['신청종료일자'] = [result[1] for result in split_results]
    df['신청시작일자'] = df['신청시작일자'].apply(convert_to_datetime)
    df['신청종료일자'] = df['신청종료일자'].apply(convert_to_datetime)
    df = df.drop(columns=['신청기간'])

    # 청년 대상 정책 필터링 (18세~39세)
    youth_filter = (
        ~(
            (df['지원대상최소연령'].between(1, 17, inclusive='both')) |
            (df['지원대상최소연령'].between(40, 999, inclusive='both')) |
            (df['지원대상최대연령'].between(1, 17, inclusive='both')) |
            (df['지원대상최대연령'].between(40, 999, inclusive='both'))
        )
    )
    df = df[youth_filter].copy()

    # 신청기간구분코드가 '마감'인 데이터 삭제
    expired_application_filter = df['신청기간구분코드'] != '마감'
    df = df[expired_application_filter].copy()    # 만료된 정책 제거
    today = pd.Timestamp.now().normalize()  # 오늘 날짜를 pandas Timestamp로 변환 (시간은 00:00:00으로 설정)

    # 사업기간종료일자 필터링
    business_end_dates = df['사업기간종료일자'].apply(convert_to_datetime)
    business_period_filter = (
        (df['사업기간종료일자'].isna()) |
        (business_end_dates.isna()) |
        (business_end_dates >= today)    )

    # 신청종료일자 필터링
    if df['신청종료일자'].dtype == 'datetime64[ns]':
        application_period_filter = (
            (df['신청종료일자'].isna()) |
            (df['신청종료일자'] >= today)
        )
    else:
        application_end_dates = df['신청종료일자'].apply(convert_to_datetime)
        application_period_filter = (
            (df['신청종료일자'].isna()) |
            (application_end_dates.isna()) |
            (application_end_dates >= today)
        )

    active_policy_filter = business_period_filter & application_period_filter
    df = df[active_policy_filter].copy()

    # 사업기간시작일자, 사업기간종료일자 datetime 변환
    df['사업기간시작일자'] = df['사업기간시작일자'].apply(convert_to_datetime)
    df['사업기간종료일자'] = df['사업기간종료일자'].apply(convert_to_datetime)

    # 불필요한 컬럼 제거
    columns_to_drop = [
        '기본계획차수', '기본계획정책방향번호', '기본계획중점과제번호', '기본계획과제번호',
        '제공기관그룹코드', '정책승인상태코드', '주관기관코드', '주관기관담당자명',
        '운영기관코드', '운영기관담당자명', '등록자기관코드', '등록자기관코드명',
        '등록자상위기관코드', '등록자상위기관코드명', '등록자최상위기관코드', '등록자최상위기관코드명',
        '지원규모수', '지원규모제한여부','지원대상연령제한여부', '소득최소금액', '소득최대금액'
    ]

    existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
    if existing_columns_to_drop:
        df = df.drop(columns=existing_columns_to_drop)


    # 최종 데이터 저장
    today_str = datetime.now().strftime('%Y-%m-%d')
    df.to_excel(f'청년정책목록_전처리완료_{today_str}.xlsx', index=False)
    df.to_csv(f'청년정책목록_전처리완료_{today_str}.csv', encoding='utf-8', index=False)
    
    print("데이터 전처리가 완료되었습니다.")
    print(f"최종 데이터 건수: {len(df)}")
    print(f"저장된 파일: 청년정책목록_전체_매핑완료_{today_str}.xlsx, 청년정책목록_전체_매핑완료_{today_str}.csv")


if __name__ == "__main__":
    main()
