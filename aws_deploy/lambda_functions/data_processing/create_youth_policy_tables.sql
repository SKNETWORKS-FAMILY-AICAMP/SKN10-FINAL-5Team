-- 청년정책 DB 테이블 설계
-- 작성일: 2025-06-18
-- 수정일: 2025-01-28 (데이터 관리 컬럼 추가)

-- pgvector 확장 설치 (임베딩 테이블용)
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. 정책 테이블 (통합 메인 테이블)
CREATE TABLE policies (
    -- 기본 정책 정보
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
    
    -- 정책 조건 정보
    sprt_trgt_min_age INTEGER,
    sprt_trgt_max_age INTEGER,
    mrg_stts_cd VARCHAR(10),
    plcy_major_cd VARCHAR(500),
    job_cd VARCHAR(500),
    school_cd VARCHAR(500),
    zip_cd VARCHAR(500),
    earn_cnd_se_cd VARCHAR(10),
    earn_etc_cn TEXT,
    add_aply_qlfcc_cn TEXT,
    ptcp_prp_trgt_cn TEXT,
    
    -- 정책 메타데이터 정보
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
    
    -- 정책 URL 정보
    aply_url_addr TEXT,
    ref_url_addr1 TEXT,
    ref_url_addr2 TEXT,
    
    -- 데이터 관리 정보 (중복/삭제 처리용)
    data_hash VARCHAR(32),                          -- 데이터 변경 감지용 MD5 해시
    is_active BOOLEAN DEFAULT TRUE,                 -- 정책 활성 상태 (논리적 삭제)
    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- 마지막 확인 시간
    deactivated_at TIMESTAMP,                       -- 비활성화 시간
    
    -- 타임스탬프
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 정책 임베딩 테이블
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
CREATE INDEX idx_policies_age ON policies(sprt_trgt_min_age, sprt_trgt_max_age);
CREATE INDEX idx_policies_classification ON policies(lclsf_nm, mclsf_nm);

-- 데이터 관리용 인덱스 추가
CREATE INDEX idx_policies_is_active ON policies(is_active);
CREATE INDEX idx_policies_data_hash ON policies(data_hash);
CREATE INDEX idx_policies_last_checked ON policies(last_checked_at);
CREATE INDEX idx_policies_deactivated ON policies(deactivated_at) WHERE deactivated_at IS NOT NULL;

-- 테이블 코멘트
COMMENT ON TABLE policies IS '정책 통합 정보 테이블 (중복/삭제 관리 포함)';
COMMENT ON TABLE policy_embeddings IS '정책 임베딩 벡터 테이블';

-- 컬럼 코멘트
-- policies 테이블
-- 기본 정책 정보
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

-- 정책 조건 정보
COMMENT ON COLUMN policies.sprt_trgt_min_age IS '지원대상최소연령';
COMMENT ON COLUMN policies.sprt_trgt_max_age IS '지원대상최대연령';
COMMENT ON COLUMN policies.mrg_stts_cd IS '결혼상태코드';
COMMENT ON COLUMN policies.plcy_major_cd IS '정책전공요건코드';
COMMENT ON COLUMN policies.job_cd IS '정책취업요건코드';
COMMENT ON COLUMN policies.school_cd IS '정책학력요건코드';
COMMENT ON COLUMN policies.zip_cd IS '정책거주지역코드';
COMMENT ON COLUMN policies.earn_cnd_se_cd IS '소득조건구분코드';
COMMENT ON COLUMN policies.earn_etc_cn IS '소득기타내용';
COMMENT ON COLUMN policies.add_aply_qlfcc_cn IS '추가신청자격요건';
COMMENT ON COLUMN policies.ptcp_prp_trgt_cn IS '참여제안대상내용';

-- 정책 메타데이터 정보
COMMENT ON COLUMN policies.lclsf_nm IS '정책대분류명';
COMMENT ON COLUMN policies.mclsf_nm IS '정책중분류명';
COMMENT ON COLUMN policies.plcy_pvsn_mthd_cd IS '정책제공방법코드';
COMMENT ON COLUMN policies.plcy_kywd_nm IS '정책키워드명';
COMMENT ON COLUMN policies.sprvsn_inst_cd_nm IS '주관기관코드명';
COMMENT ON COLUMN policies.oper_inst_cd_nm IS '운영기관코드명';
COMMENT ON COLUMN policies.aply_prd_se_cd IS '신청기간구분코드';
COMMENT ON COLUMN policies.biz_prd_se_cd IS '사업기간구분코드';
COMMENT ON COLUMN policies.biz_prd_bgng_ymd IS '사업기간시작일자';
COMMENT ON COLUMN policies.biz_prd_end_ymd IS '사업기간종료일자';
COMMENT ON COLUMN policies.biz_prd_etc_cn IS '사업기간기타내용';
COMMENT ON COLUMN policies.s_biz_cd IS '정책특화요건코드';

-- 정책 URL 정보
COMMENT ON COLUMN policies.aply_url_addr IS '신청URL주소';
COMMENT ON COLUMN policies.ref_url_addr1 IS '참고URL주소1';
COMMENT ON COLUMN policies.ref_url_addr2 IS '참고URL주소2';

-- 데이터 관리 정보
COMMENT ON COLUMN policies.data_hash IS '데이터 변경 감지용 MD5 해시값';
COMMENT ON COLUMN policies.is_active IS '정책 활성 상태 (FALSE: 논리적 삭제)';
COMMENT ON COLUMN policies.last_checked_at IS '마지막 데이터 확인 시간';
COMMENT ON COLUMN policies.deactivated_at IS '정책 비활성화 시간';

-- policy_embeddings 테이블
COMMENT ON COLUMN policy_embeddings.plcy_no IS '정책번호';
COMMENT ON COLUMN policy_embeddings.embedding IS '정책 임베딩 (3072차원)';

-- 기존 테이블이 있는 경우 컬럼 추가용 ALTER 스크립트
-- (새로 설치할 때는 실행하지 않아도 됨)
/*
-- 기존 policies 테이블에 새 컬럼 추가
DO $$
BEGIN
    -- data_hash 컬럼 추가
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'policies' AND column_name = 'data_hash') THEN
        ALTER TABLE policies ADD COLUMN data_hash VARCHAR(32);
    END IF;
    
    -- is_active 컬럼 추가
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'policies' AND column_name = 'is_active') THEN
        ALTER TABLE policies ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
    END IF;
    
    -- last_checked_at 컬럼 추가
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'policies' AND column_name = 'last_checked_at') THEN
        ALTER TABLE policies ADD COLUMN last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- deactivated_at 컬럼 추가
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'policies' AND column_name = 'deactivated_at') THEN
        ALTER TABLE policies ADD COLUMN deactivated_at TIMESTAMP;
    END IF;
END $$;

-- 새 인덱스 생성 (중복 방지)
CREATE INDEX IF NOT EXISTS idx_policies_is_active ON policies(is_active);
CREATE INDEX IF NOT EXISTS idx_policies_data_hash ON policies(data_hash);
CREATE INDEX IF NOT EXISTS idx_policies_last_checked ON policies(last_checked_at);
CREATE INDEX IF NOT EXISTS idx_policies_deactivated ON policies(deactivated_at) WHERE deactivated_at IS NOT NULL;
*/
