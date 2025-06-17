-- 청년정책 DB 테이블 설계
-- 작성일: 2025-06-18

-- pgvector 확장 설치 (임베딩 테이블용)
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 정책 테이블 (메인 테이블)
CREATE TABLE policies (
    plcy_no VARCHAR(50) PRIMARY KEY,
    plcy_nm TEXT NOT NULL,
    plcy_expln_cn TEXT,
    plcy_sprt_cn TEXT,
    plcy_aply_mthd_cn TEXT,
    srng_mthd_cn TEXT,
    sbmsn_dcmnt_cn TEXT,
    etc_mttr_cn TEXT,
    inq_cnt INTEGER DEFAULT 0,
    frst_reg_dt TIMESTAMP,
    last_mdfcn_dt TIMESTAMP,
    aply_bgng_ymd DATE,
    aply_end_ymd DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 정책 조건 테이블
CREATE TABLE policy_conditions (
    condition_id SERIAL PRIMARY KEY,
    plcy_no VARCHAR(50) NOT NULL UNIQUE,
    sprt_trgt_min_age INTEGER,
    sprt_trgt_max_age INTEGER,
    mrg_stts_cd VARCHAR(10),
    plcy_major_cd VARCHAR(500),
    job_cd VARCHAR(500),
    school_cd VARCHAR(500),
    zip_cd VARCHAR(500),
    earn_cnd_se_cd VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plcy_no) REFERENCES policies(plcy_no) ON DELETE CASCADE
);

-- 3. 정책 조건 내용 테이블
CREATE TABLE policy_condition_details (
    condition_id INTEGER NOT NULL,
    earn_etc_cn TEXT,
    add_aply_qlfcc_cn TEXT,
    ptcp_prp_trgt_cn TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (condition_id),
    FOREIGN KEY (condition_id) REFERENCES policy_conditions(condition_id) ON DELETE CASCADE
);

-- 4. 정책 메타데이터 테이블
CREATE TABLE policy_metadata (
    plcy_no VARCHAR(50) NOT NULL,
    lclsf_nm VARCHAR(100),
    mclsf_nm VARCHAR(100),
    plcy_pvsn_mthd_cd VARCHAR(10),
    plcy_kywd_nm TEXT,
    sprvsn_inst_cd_nm VARCHAR(200),
    oper_inst_cd_nm VARCHAR(200),
    aply_prd_se_cd VARCHAR(10),
    biz_prd_se_cd VARCHAR(10),
    biz_prd_bgng_ymd DATE,
    biz_prd_end_ymd DATE,
    biz_prd_etc_cn TEXT,
    s_biz_cd VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (plcy_no),
    FOREIGN KEY (plcy_no) REFERENCES policies(plcy_no) ON DELETE CASCADE
);

-- 5. 정책 URL 테이블
CREATE TABLE policy_urls (
    plcy_no VARCHAR(50) NOT NULL,
    aply_url_addr TEXT,
    ref_url_addr1 TEXT,
    ref_url_addr2 TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (plcy_no),
    FOREIGN KEY (plcy_no) REFERENCES policies(plcy_no) ON DELETE CASCADE
);

-- 6. 정책 임베딩 테이블
CREATE TABLE policy_embeddings (
    plcy_no VARCHAR(50) NOT NULL,
    embedding VECTOR(3072),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (plcy_no),
    FOREIGN KEY (plcy_no) REFERENCES policies(plcy_no) ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX idx_policies_plcy_nm ON policies(plcy_nm);
CREATE INDEX idx_policies_aply_dates ON policies(aply_bgng_ymd, aply_end_ymd);

CREATE INDEX idx_policy_conditions_age ON policy_conditions(sprt_trgt_min_age, sprt_trgt_max_age);

CREATE INDEX idx_policy_metadata_classification ON policy_metadata(lclsf_nm, mclsf_nm);

-- 테이블 코멘트
COMMENT ON TABLE policies IS '정책 기본 정보 테이블';
COMMENT ON TABLE policy_conditions IS '정책 지원 조건 테이블';
COMMENT ON TABLE policy_condition_details IS '정책 조건 상세 내용 테이블';
COMMENT ON TABLE policy_metadata IS '정책 메타데이터 테이블';
COMMENT ON TABLE policy_urls IS '정책 관련 URL 테이블';
COMMENT ON TABLE policy_embeddings IS '정책 임베딩 벡터 테이블';

-- 컬럼 코멘트
-- policies 테이블
COMMENT ON COLUMN policies.plcy_no IS '정책번호';
COMMENT ON COLUMN policies.plcy_nm IS '정책명';
COMMENT ON COLUMN policies.plcy_expln_cn IS '정책설명내용';
COMMENT ON COLUMN policies.plcy_sprt_cn IS '정책지원내용';
COMMENT ON COLUMN policies.plcy_aply_mthd_cn IS '정책신청방법내용';
COMMENT ON COLUMN policies.srng_mthd_cn IS '심사방법내용';
COMMENT ON COLUMN policies.sbmsn_dcmnt_cn IS '제출서류내용';
COMMENT ON COLUMN policies.etc_mttr_cn IS '기타사항내용';
COMMENT ON COLUMN policies.inq_cnt IS '조회수';
COMMENT ON COLUMN policies.frst_reg_dt IS '최초등록일시';
COMMENT ON COLUMN policies.last_mdfcn_dt IS '최종수정일시';
COMMENT ON COLUMN policies.aply_bgng_ymd IS '신청시작일자';
COMMENT ON COLUMN policies.aply_end_ymd IS '신청종료일자';

-- policy_conditions 테이블
COMMENT ON COLUMN policy_conditions.condition_id IS '조건ID';
COMMENT ON COLUMN policy_conditions.plcy_no IS '정책번호';
COMMENT ON COLUMN policy_conditions.sprt_trgt_min_age IS '지원대상최소연령';
COMMENT ON COLUMN policy_conditions.sprt_trgt_max_age IS '지원대상최대연령';
COMMENT ON COLUMN policy_conditions.mrg_stts_cd IS '결혼상태코드';
COMMENT ON COLUMN policy_conditions.plcy_major_cd IS '정책전공요건코드';
COMMENT ON COLUMN policy_conditions.job_cd IS '정책취업요건코드';
COMMENT ON COLUMN policy_conditions.school_cd IS '정책학력요건코드';
COMMENT ON COLUMN policy_conditions.zip_cd IS '정책거주지역코드';
COMMENT ON COLUMN policy_conditions.earn_cnd_se_cd IS '소득조건구분코드';

-- policy_condition_details 테이블
COMMENT ON COLUMN policy_condition_details.condition_id IS '조건ID';
COMMENT ON COLUMN policy_condition_details.earn_etc_cn IS '소득기타내용';
COMMENT ON COLUMN policy_condition_details.add_aply_qlfcc_cn IS '추가신청자격요건';
COMMENT ON COLUMN policy_condition_details.ptcp_prp_trgt_cn IS '참여제안대상내용';

-- policy_metadata 테이블
COMMENT ON COLUMN policy_metadata.plcy_no IS '정책번호';
COMMENT ON COLUMN policy_metadata.lclsf_nm IS '정책대분류명';
COMMENT ON COLUMN policy_metadata.mclsf_nm IS '정책중분류명';
COMMENT ON COLUMN policy_metadata.plcy_pvsn_mthd_cd IS '정책제공방법코드';
COMMENT ON COLUMN policy_metadata.plcy_kywd_nm IS '정책키워드명';
COMMENT ON COLUMN policy_metadata.sprvsn_inst_cd_nm IS '주관기관코드명';
COMMENT ON COLUMN policy_metadata.oper_inst_cd_nm IS '운영기관코드명';
COMMENT ON COLUMN policy_metadata.aply_prd_se_cd IS '신청기간구분코드';
COMMENT ON COLUMN policy_metadata.biz_prd_se_cd IS '사업기간구분코드';
COMMENT ON COLUMN policy_metadata.biz_prd_bgng_ymd IS '사업기간시작일자';
COMMENT ON COLUMN policy_metadata.biz_prd_end_ymd IS '사업기간종료일자';
COMMENT ON COLUMN policy_metadata.biz_prd_etc_cn IS '사업기간기타내용';
COMMENT ON COLUMN policy_metadata.s_biz_cd IS '정책특화요건코드';

-- policy_urls 테이블
COMMENT ON COLUMN policy_urls.plcy_no IS '정책번호';
COMMENT ON COLUMN policy_urls.aply_url_addr IS '신청URL주소';
COMMENT ON COLUMN policy_urls.ref_url_addr1 IS '참고URL주소1';
COMMENT ON COLUMN policy_urls.ref_url_addr2 IS '참고URL주소2';

-- policy_embeddings 테이블
COMMENT ON COLUMN policy_embeddings.plcy_no IS '정책번호';
COMMENT ON COLUMN policy_embeddings.embedding IS '정책 임베딩 (3072차원)';
