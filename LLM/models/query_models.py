"""
Pydantic 모델 정의 - 질의 분석, SQL 생성, 정책 선정 관련 모델
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class QueryAnalysis(BaseModel):
    """질의 분석을 위한 통합 구조화된 출력 모델 (분류 + 조건 추출)"""
    # 질의 분류 정보
    lclsf_nm: Literal["주거", "일자리", "일반", "그 외 정책", "기타"] = Field(
        description="대분류(lclsf_nm): 주거, 일자리, 일반, 그 외 정책, 기타"
    )
    query_keywords: str = Field(
        default=None,
        description="사용자 질문에서 추출된 키워드"
    )
    query_intent: Literal["맞춤 정책 검색", "정책 상세 설명", "기타"] = Field(
        default="맞춤 정책 검색",
        description="사용자 질문의 의도 (맞춤 정책 검색, 정책 상세 설명, 기타)"
    )
    
    # 사용자 조건 정보
    age: Optional[int] = Field(
        default=None,
        description="사용자 나이"
    )
    mrg_stts_cd: Optional[Literal["기혼", "미혼"]] = Field(
        default=None,
        description="결혼 상태"
    )
    plcy_major_cd: Optional[Literal["인문계열", "자연계열", "사회계열", "상경계열", "이학계열", "공학계열", "예체능계열", "농산업계열"]] = Field(
        default=None,
        description="전공 계열"
    )
    job_cd: Optional[Literal["재직자", "미취업자", "자영업자", "(예비)창업자", "영농종사자", "비정규직"]] = Field(
        default=None,
        description="취업 상태"
    )
    school_cd: Optional[Literal["고졸 미만", "고교 재학", "고졸 예정", "고교 졸업", "대학 재학", "대졸 예정", "대학 졸업", "석·박사"]] = Field(
        default=None,
        description="학력 상태"
    )
    zip_cd: Optional[str] = Field(
        default=None,
        description="거주지 (광역시/도, 시군구)"
    )
    earn_etc_cn: Optional[str] = Field(
        default=None,
        description="소득 요건 (예: 중위소득 150% 이하, 월소득 200만원 이하 등)"
    )
    additional_requirement: Optional[str] = Field(
        default=None,
        description="기타 추가 요건이나 상황"
    )


class SQLQueryGeneration(BaseModel):
    """SQL 쿼리 생성을 위한 구조화된 출력 모델"""
    sql_query: str = Field(
        description="생성된 PostgreSQL 쿼리"
    )


class SelectedPolicy(BaseModel):
    """선정된 정책 정보"""
    plcy_no: str = Field(description="정책 번호")
    plcy_nm: str = Field(description="정책명")
    plcy_expln_nm: str = Field(description="정책 설명명")
    lclsf_nm: str = Field(description="대분류명")
    mclsf_nm: str = Field(description="중분류명")
    zip_cd: str = Field(description="지역코드")
    inq_cnt: int = Field(description="문의 횟수")


class PolicySelection(BaseModel):
    """LLM이 선정한 정책들을 위한 구조화된 출력 모델"""
    selected_policies: List[SelectedPolicy] = Field(
        description="LLM이 선정한 정책 목록 (최대 10개)"
    )
    final_response: str = Field(
        description="최종 응답"
    )
