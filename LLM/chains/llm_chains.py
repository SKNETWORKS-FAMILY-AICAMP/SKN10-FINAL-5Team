"""
LLM 체인 팩토리 및 체인 생성 함수들
"""
from langchain_core.prompts import ChatPromptTemplate
from config.settings import YouthPolicyRAGConfig
from models.query_models import SQLQueryGeneration, PolicySelection
from database.queries import get_postgresql_schema
import logging

logger = logging.getLogger(__name__)


class LLMChainFactory:
    """LLM 체인 팩토리 클래스"""
    
    def __init__(self, config: YouthPolicyRAGConfig):
        self.config = config
    
    def create_sql_generation_chain(self, schema_info: str, query_analysis):
        """SQL 생성 체인 생성"""
        sql_prompt = ChatPromptTemplate.from_messages([
            ("system", f"""당신은 PostgreSQL 전문가입니다. 
주어진 자연어 질문을 바탕으로 정확한 PostgreSQL 쿼리를 생성해주세요.

**데이터베이스 스키마:**
{schema_info}

**분류 정보:** {query_analysis.lclsf_nm}
**조건 정보:** {query_analysis}

**쿼리 생성 규칙:**
1. 반드시 PostgreSQL 문법을 사용하세요
2. 안전한 쿼리만 생성하세요 (SELECT문만 허용, INSERT/UPDATE/DELETE 금지)
3. 테이블명과 컬럼명을 정확히 사용하세요
5. LIMIT을 사용하여 결과 수를 10개로 제한하세요
6. 분류 정보로 policies 테이블의 lclsf_nm을 사용하여 필터링하세요
7. 나이 정보는 policies 테이블의 sprt_trgt_min_age, sprt_trgt_max_age 컬럼을 사용하여 필터링하세요
8. mrg_stts_cd 검색 시 IN (조건 정보,'제한없음') 형태로 필터링하세요
9. school_cd, plcy_major_cd, job_cd 검색 시 '제한없음'과 해당 조건을 필터링 하세요
10. zip_cd 검색 시 전국, 해당지역, 해당 지역의 상위 지역을 포함하여 필터링 해야 합니다.
11. earn_etc_cn은 유사도를 판단하는데 사용합니다.
12. additional_requirement도 필터링은 하지 않고 add_aply_qlfcc_cn, ptcp_prp_trgt_cn 컬럼과 유사도 판단으로 사용합니다.
13. query_keywords는 policies 테이블의 plcy_nm, plcy_expl_cn 컬럼과 유사도 판단으로 사용합니다.
14. policies 테이블의 모든 컬럼을 SELECT 하여 반환하세요
15. 사용자 조건과 제일 유사한 정책으로 정렬하도록 쿼리를 구성해주세요
16. 필터링 할 때는 분류 정보, 조건 정보만 사용해서 쿼리를 구성해야 합니다
"""),
            ("human", "다음 질문에 PostgreSQL 쿼리를 생성해주세요: {query}")
        ])
        
        llm_no_stream = self.config.thinking_model.bind(stream=False)
        structured_llm = llm_no_stream.with_structured_output(SQLQueryGeneration)
        return sql_prompt | structured_llm
    
    def create_policy_selection_chain(self):
        """정책 선정 체인 생성"""
        policy_selection_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 청년정책 전문가입니다. 
검색된 정책 데이터를 분석하여 사용자의 질문과 조건에 가장 적합한 정책들을 선정하고 친절한 답변을 제공해주세요.

**분류 정보:** {classification_type}
**사용자 질문:** {user_query}
**사용자 조건:** {user_conditions}
**검색된 정책 데이터:** {search_data}

**정책 선정 가이드라인:**
1. 사용자의 조건(나이, 거주지, 학력, 취업상태 등)에 가장 적합한 정책을 우선 선정
2. 사용자 질문의 키워드와 관련성이 높은 정책을 선정
3. 최대 10개까지의 정책을 선정
4. 선정된 각 정책에 대해 plcy_no, plcy_nm, plcy_expln_nm, lclsf_nm, mclsf_nm, zip_cd, inq_cnt 정보를 정확히 추출

**주의사항:**
- 검색 결과에서 실제 존재하는 정책만 선정
- 정책 정보는 검색 결과에서 정확히 추출

**답변 가이드라인:**
1. 검색 결과를 바탕으로 정확한 정보를 제공하세요
2. 정책명, 지원내용, 신청방법 등을 구체적으로 안내하세요
3. 사용자의 조건에 맞는 정책을 우선적으로 추천하세요
4. 검색 결과가 없거나 부족한 경우 그 이유를 설명하세요
5. 친근하고 도움이 되는 톤으로 답변하세요
6. 필요시 추가 문의 방법이나 관련 기관 정보를 제공하세요
7. 답변 시 markdown 형식을 사용하여 가독성을 높이세요
8. 적절한 이모지를 사용하여 답변을 더 친근하게 만드세요
9. 주거정책과 일자리 정책을 구분하여 답변하세요
10. 2개 이상의 정책목록 나열 시 구분할 수 있도록 정책 앞과 뒤에 --- 형태로 구분하세요
11. query_intent가 '정책 상세 설명'인 경우 해당 정책에 대해 사용자 질문에 답변을 제공하세요

"""),
            ("human", "위 검색 결과에서 사용자에게 적합한 정책들을 선정하고 사용자 질문에 대한 답변을 생성해주세요.")
        ])
        
        llm_no_stream = self.config.chat_llm.bind(stream=False)
        policy_selection_llm = llm_no_stream.with_structured_output(PolicySelection)
        return policy_selection_prompt | policy_selection_llm


def create_direct_sql_chain(config, query_analysis):
    """직접 SQL 쿼리를 생성하는 LLM 체인을 생성하는 함수"""
    
    # 데이터베이스 스키마 정보 가져오기
    schema_info = get_postgresql_schema(config)
    
    # SQL 쿼리 생성을 위한 프롬프트 템플릿
    sql_prompt = ChatPromptTemplate.from_messages([
        ("system", f"""당신은 PostgreSQL 전문가입니다. 주어진 자연어 질문을 바탕으로 정확한 PostgreSQL 쿼리를 생성해주세요.

**데이터베이스 스키마:**
{schema_info}


mrg_stts_cd -> ('기혼', '미혼', '제한없음')
plcy_major_cd -> ('인문계열', '자연계열', '사회계열', '상경계열', '이학계열', '공학계열', '예체능계열', '농산업계열', '제한없음')
job_cd -> ('재직자', '미취업자', '자영업자', '(예비)창업자', '영농종사자', '비정규직', '제한없음')
school_cd -> ('고졸 미만', '고교 재학', '고졸 예정', '고교 졸업', '대학 재학', '대졸 예정', '대학 졸업', '석·박사', '제한없음')
zip_cd -> string 값 (예: '전국', '서울특별시', '대구광역시', '경상북도', '전북특별자치도', '서울 구로구', '대구 달서구', '경기도 수원시', '경기도 수원시 팔달구')
earn_etc_cn -> string 값 (예: '중위소득 150% 이하', '월소득 200만원 이하')

**분류 정보:** {query_analysis.lclsf_nm}
**조건 정보:** {query_analysis}

**쿼리 생성 규칙:**
1. 반드시 PostgreSQL 문법을 사용하세요
2. 안전한 쿼리만 생성하세요 (SELECT문만 허용, INSERT/UPDATE/DELETE 금지)
3. 테이블명과 컬럼명을 정확히 사용하세요
5. LIMIT을 사용하여 결과 수를 10개로 제한하세요
6. 분류 정보로 policies 테이블의 lclsf_nm을 사용하여 필터링하세요
    - lclsf_nm 이 '일반'인 경우 policies 테이블의 lclsf_nm 컬럼을 '주거' 또는 '일자리'로 필터링합니다.
    - lclsf_nm 이 '일반'인 경우 policies 테이블의 lclsf_nm의 '주거', '일자리'를 각각 5개씩 반환합니다.
7. 나이 정보는 policies 테이블의 sprt_trgt_min_age, sprt_trgt_max_age 컬럼을 사용하여 필터링하세요
    - sprt_trgt_min_age와 sprt_trgt_max_age 가 0 인 경우는 필터링하지 않습니다.
    - 예: sprt_trgt_min_age <= 25 AND sprt_trgt_max_age >= 25 OR (sprt_trgt_min_age = 0 AND sprt_trgt_max_age = 0)
8. mrg_stts_cd 검색 시 IN (조건 정보,'제한없음') 형태로 필터링하세요
9. school_cd, plcy_major_cd, job_cd 검색 시 '제한없음'과 해당 조건을 필터링 하세요
    - 예 school_cd ILIKE '%대학 졸업%' OR school_cd = '제한없음'
    - 예 plcy_major_cd ILIKE '%인문계열%' OR plcy_major_cd = '제한없음'
10. zip_cd 검색 시 전국, 해당지역, 해당 지역의 상위 지역을 포함하여 필터링 해야 합니다.
    - zip_cd 데이터가 예를들을 '경기도 수원시 팔달구'이면 '경기도', '경기도 수원시', '경기도 수원시 팔달구' 데이터를 모두 포함해야 합니다.
    - 예 zip_cd ILIKE '%경기도 수원시 팔달구%' OR zip_cd ILIKE '%경기도 수원시%' OR zip_cd ILIKE '%경기도%' OR zip_cd = '전국'
11. earn_etc_cn은 유사도를 판단하는데 사용합니다.
    - 예 ORDER BY similarity(earn_etc_cn, 조건 정보의 earn_etc_cn) DESC
12. additional_requirement도 필터링은 하지 않고 add_aply_qlfcc_cn, ptcp_prp_trgt_cn 컬럼과 유사도 판단으로 사용합니다.
    - 예 ORDER BY similarity(add_aply_qlfcc_cn, additional_requirement) DESC, similarity(ptcp_prp_trgt_cn, additional_requirement) DESC
13. query_keywords는 policies 테이블의 plcy_nm, plcy_expl_cn 컬럼과 유사도 판단으로 사용합니다.
    - 예 ORDER BY similarity(plcy_nm, query_keywords) DESC, similarity(plcy_expl_cn, query_keywords) DESC
    - query_keywords 정렬은 반드시 사용을 해야 합니다.
14. policies 테이블의 모든 컬럼을 SELECT 하여 반환하세요
15. 사용자 조건과 제일 유사한 정책으로 정렬하도록 쿼리를 구성해주세요
    - 정렬 순서: zip_cd > mrg_stts_cd, school_cd, plcy_major_cd, job_cd > query_keywords >earn_etc_cn, additional_requirement
16. 필터링 할 때는 분류 정보, 조건 정보만 사용해서 쿼리를 구성해야 합니다

**주의사항:**
- 쿼리는 반드시 실행 가능한 형태여야 합니다
- 존재하지 않는 테이블이나 컬럼을 참조하지 마세요
- SQL injection을 방지하기 위해 안전한 쿼리만 생성하세요
- SELECT DISTINCT를 사용할 때 ORDER BY에 사용되는 모든 표현식은 SELECT 목록에 포함되어야 합니다
- similarity 함수나 복잡한 ORDER BY 표현식을 사용할 때는 SELECT DISTINCT 대신 일반 SELECT를 사용하세요
- 중복 제거가 필요한 경우 서브쿼리나 윈도우 함수를 사용하여 해결하세요

"""),
        ("human", "다음 질문에 PostgreSQL 쿼리를 생성해주세요: {query}")
    ])
    # 구조화된 출력을 위한 LLM 체인 (streaming 비활성화)
    llm_no_stream = config.thinking_model.bind(stream=False)
    structured_llm = llm_no_stream.with_structured_output(SQLQueryGeneration)
    sql_chain = sql_prompt | structured_llm
    
    return sql_chain
