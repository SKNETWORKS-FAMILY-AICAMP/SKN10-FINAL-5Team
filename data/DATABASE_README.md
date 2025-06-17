# 청년정책 데이터베이스 설계 및 구축

## 개요
청년정책 CSV 데이터를 PostgreSQL 데이터베이스에 저장하기 위한 테이블 설계 및 데이터 삽입 스크립트입니다.

## 테이블 구조

### 1. policies (정책 기본정보)
- **plcy_no**: 정책번호 (Primary Key)
- **plcy_nm**: 정책명
- **plcy_expln_cn**: 정책설명내용
- **plcy_sprt_cn**: 정책지원내용
- **plcy_aply_mthd_cn**: 정책신청방법내용
- **srng_mthd_cn**: 심사방법내용
- **sbmsn_dcmnt_cn**: 제출서류내용
- **etc_mttr_cn**: 기타사항내용
- **inq_cnt**: 조회수
- **frst_reg_dt**: 최초등록일시
- **last_mdfcn_dt**: 최종수정일시
- **aply_bgng_ymd**: 신청시작일자
- **aply_end_ymd**: 신청종료일자

### 2. policy_conditions (정책 조건)
- **condition_id**: 조건ID (Primary Key, Auto Increment)
- **plcy_no**: 정책번호 (Foreign Key)
- **sprt_trgt_min_age**: 지원대상최소연령
- **sprt_trgt_max_age**: 지원대상최대연령
- **mrg_stts_cd**: 결혼상태코드
- **plcy_major_cd**: 정책전공요건코드
- **job_cd**: 정책취업요건코드
- **school_cd**: 정책학력요건코드
- **zip_cd**: 정책거주지역코드
- **earn_cnd_se_cd**: 소득조건구분코드

### 3. policy_condition_details (정책 조건 상세)
- **condition_id**: 조건ID (Primary Key, Foreign Key)
- **earn_etc_cn**: 소득기타내용
- **add_aply_qlfcc_cn**: 추가신청자격요건
- **ptcp_prp_trgt_cn**: 참여제안대상내용

### 4. policy_metadata (정책 메타데이터)
- **plcy_no**: 정책번호 (Primary Key, Foreign Key)
- **lclsf_nm**: 정책대분류명
- **mclsf_nm**: 정책중분류명
- **plcy_pvsn_mthd_cd**: 정책제공방법코드
- **plcy_kywd_nm**: 정책키워드명
- **sprvsn_inst_cd_nm**: 주관기관코드명
- **oper_inst_cd_nm**: 운영기관코드명
- **aply_prd_se_cd**: 신청기간구분코드
- **biz_prd_se_cd**: 사업기간구분코드
- **biz_prd_bgng_ymd**: 사업기간시작일자
- **biz_prd_end_ymd**: 사업기간종료일자
- **biz_prd_etc_cn**: 사업기간기타내용
- **sprt_arvl_seq_yn**: 지원도착순서여부
- **s_biz_cd**: 정책특화요건코드

### 5. policy_urls (정책 URL)
- **plcy_no**: 정책번호 (Primary Key, Foreign Key)
- **aply_url_addr**: 신청URL주소
- **ref_url_addr1**: 참고URL주소1
- **ref_url_addr2**: 참고URL주소2

### 6. policy_embeddings (정책 임베딩)
- **plcy_no**: 정책번호 (Primary Key, Foreign Key)
- **embedding**: 정책 임베딩 (3072차원 벡터)

## 설치 및 실행

### 1. 필요 패키지 설치
```bash
pip install -r requirements_embedding.txt
```

### 2. 환경변수 설정
`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 실제 값으로 수정:
```bash
cp .env.example .env
```

`.env` 파일에서 다음 값들을 설정:
- `OPENAI_API_KEY`: OpenAI API 키 (임베딩 생성용)
- `DB_PASSWORD`: PostgreSQL 비밀번호
- 기타 DB 연결 정보

### 3. PostgreSQL 데이터베이스 설정
```sql
-- 데이터베이스 생성
CREATE DATABASE youth_policy;

-- pgvector 확장 설치 (임베딩 테이블용)
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. 테이블 생성
```bash
psql -U postgres -d youth_policy -f create_youth_policy_tables.sql
```

### 5. 데이터 삽입 (임베딩 포함)
```bash
python insert_youth_policy_data_with_embeddings.py
```

### 6. 임베딩 검색 테스트
```bash
python policy_search_engine.py
```

## 특징

### 정규화된 설계
- 데이터 중복을 최소화하고 일관성을 보장하는 3차 정규화 적용
- 외래키 제약조건으로 데이터 무결성 보장
- 인덱스를 통한 검색 성능 최적화

### AI/ML 지원 임베딩 시스템
- **OpenAI text-embedding-3-large** 모델을 사용한 3072차원 벡터 임베딩
- 정책명, 설명, 지원내용, 키워드를 종합한 **의미적 검색** 지원
- **pgvector** 확장을 통한 고성능 벡터 유사도 검색
- **코사인 유사도** 기반 정책 추천 시스템

### 확장성
- 임베딩 테이블을 통한 AI/ML 활용 가능
- pgvector 확장을 통한 벡터 유사도 검색 지원
- 조건 테이블 분리로 복잡한 검색 조건 처리 용이

### 성능 최적화
- 주요 검색 필드에 인덱스 생성
- 한국어 전문검색을 위한 GIN 인덱스 적용
- **IVFFlat 인덱스**를 통한 벡터 검색 최적화
- 파티셔닝 및 샤딩 확장 가능한 구조

## 데이터 검색 예시

### 임베딩 기반 유사도 검색
```sql
-- 쿼리 텍스트와 가장 유사한 정책 검색
SELECT 
    p.plcy_nm,
    p.plcy_expln_cn,
    pm.plcy_kywd_nm,
    (pe.embedding <=> '[쿼리_임베딩_벡터]'::vector) as similarity
FROM policies p
JOIN policy_embeddings pe ON p.plcy_no = pe.plcy_no
JOIN policy_metadata pm ON p.plcy_no = pm.plcy_no
ORDER BY pe.embedding <=> '[쿼리_임베딩_벡터]'::vector
LIMIT 10;
```

### 연령별 정책 검색
```sql
SELECT p.plcy_nm, pc.sprt_trgt_min_age, pc.sprt_trgt_max_age
FROM policies p
JOIN policy_conditions pc ON p.plcy_no = pc.plcy_no
WHERE pc.sprt_trgt_min_age <= 25 AND pc.sprt_trgt_max_age >= 25;
```

### 키워드별 정책 검색
```sql
SELECT p.plcy_nm, pm.plcy_kywd_nm
FROM policies p
JOIN policy_metadata pm ON p.plcy_no = pm.plcy_no
WHERE pm.plcy_kywd_nm ILIKE '%주거%';
```

### 지역별 정책 검색
```sql
SELECT p.plcy_nm, pc.zip_cd
FROM policies p
JOIN policy_conditions pc ON p.plcy_no = pc.plcy_no
WHERE pc.zip_cd LIKE '%서울%';
```

### Python을 통한 의미적 검색
```python
from policy_search_engine import PolicySearchEngine

# 검색 엔진 초기화
search_engine = PolicySearchEngine(db_config)

# 자연어 쿼리로 유사한 정책 검색
results = search_engine.search_similar_policies("청년 주거 지원 임대료 보조", limit=5)

# 조건 기반 검색
results = search_engine.search_policies_by_condition(
    age=25, 
    region="서울", 
    keyword="취업"
)
```

## 주의사항

1. **데이터 타입**: 날짜 필드는 PostgreSQL의 DATE/TIMESTAMP 타입 사용
2. **인코딩**: UTF-8 인코딩으로 한글 데이터 처리
3. **NULL 값**: CSV의 빈 값은 NULL로 처리
4. **중복 처리**: UPSERT (ON CONFLICT) 구문으로 중복 데이터 방지
5. **트랜잭션**: 오류 발생 시 롤백을 통한 데이터 일관성 보장

## 향후 확장 계획

1. **검색 엔진 연동**: Elasticsearch와 연동하여 고급 검색 기능 제공
2. **API 개발**: RESTful API를 통한 정책 데이터 제공
3. **추천 시스템**: 임베딩 벡터를 활용한 개인화된 정책 추천
4. **실시간 업데이트**: 정책 변경사항 실시간 반영 시스템
