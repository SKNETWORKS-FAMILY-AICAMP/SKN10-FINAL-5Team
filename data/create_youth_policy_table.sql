-- 청년정책 테이블 생성 SQL (PostgreSQL)
CREATE TABLE youth_policy (
    plcy_no VARCHAR(100) NOT NULL,
    plcy_pvsn_mthd_cd VARCHAR(100),
    plcy_nm VARCHAR(200) NOT NULL,
    plcy_kywd_nm VARCHAR(100),
    plcy_expln_cn TEXT,
    lclsf_nm VARCHAR(100),
    mclsf_nm VARCHAR(100),
    plcy_sprt_cn TEXT,
    sprvsn_inst_cd_nm VARCHAR(100),
    oper_inst_cd_nm VARCHAR(100),
    aply_prd_se_cd VARCHAR(100),
    biz_prd_se_cd VARCHAR(100),
    biz_prd_bgng_ymd DATE,
    biz_prd_end_ymd DATE,
    biz_prd_etc_cn TEXT,
    plcy_aply_mthd_cn TEXT,
    srng_mthd_cn TEXT,
    aply_url_addr TEXT,
    sbmsn_dcmnt_cn TEXT,
    etc_mttr_cn TEXT,
    ref_url_addr1 TEXT,
    ref_url_addr2 TEXT,
    sprt_arvl_seq_yn CHAR(1),
    sprt_trgt_min_age INTEGER,
    sprt_trgt_max_age INTEGER,
    mrg_stts_cd VARCHAR(100),
    earn_cnd_se_cd VARCHAR(100),
    earn_etc_cn TEXT,
    add_aply_qlfcnd_cn TEXT,
    ptcp_prp_trgt_cn TEXT,
    inq_cnt INTEGER DEFAULT 0,
    zip_cd TEXT,
    plcy_major_cd VARCHAR(100),
    job_cd VARCHAR(100),
    school_cd VARCHAR(100),
    s_biz_cd VARCHAR(100),
    aply_start_date DATE,
    aply_end_date DATE,
    frst_reg_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_mdfcn_dt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (plcy_no)
);

-- 컬럼 코멘트 추가
COMMENT ON TABLE youth_policy IS '청년정책 정보';
COMMENT ON COLUMN youth_policy.plcy_no IS '정책번호';
COMMENT ON COLUMN youth_policy.plcy_pvsn_mthd_cd IS '정책제공방법코드';
COMMENT ON COLUMN youth_policy.plcy_nm IS '정책명';
COMMENT ON COLUMN youth_policy.plcy_kywd_nm IS '정책키워드명';
COMMENT ON COLUMN youth_policy.plcy_expln_cn IS '정책설명내용';
COMMENT ON COLUMN youth_policy.lclsf_nm IS '정책대분류명';
COMMENT ON COLUMN youth_policy.mclsf_nm IS '정책중분류명';
COMMENT ON COLUMN youth_policy.plcy_sprt_cn IS '정책지원내용';
COMMENT ON COLUMN youth_policy.sprvsn_inst_cd_nm IS '주관기관코드명';
COMMENT ON COLUMN youth_policy.oper_inst_cd_nm IS '운영기관코드명';
COMMENT ON COLUMN youth_policy.aply_prd_se_cd IS '신청기간구분코드';
COMMENT ON COLUMN youth_policy.biz_prd_se_cd IS '사업기간구분코드';
COMMENT ON COLUMN youth_policy.biz_prd_bgng_ymd IS '사업기간시작일자';
COMMENT ON COLUMN youth_policy.biz_prd_end_ymd IS '사업기간종료일자';
COMMENT ON COLUMN youth_policy.biz_prd_etc_cn IS '사업기간기타내용';
COMMENT ON COLUMN youth_policy.plcy_aply_mthd_cn IS '정책신청방법내용';
COMMENT ON COLUMN youth_policy.srng_mthd_cn IS '심사방법내용';
COMMENT ON COLUMN youth_policy.aply_url_addr IS '신청URL주소';
COMMENT ON COLUMN youth_policy.sbmsn_dcmnt_cn IS '제출서류내용';
COMMENT ON COLUMN youth_policy.etc_mttr_cn IS '기타사항내용';
COMMENT ON COLUMN youth_policy.ref_url_addr1 IS '참고URL주소1';
COMMENT ON COLUMN youth_policy.ref_url_addr2 IS '참고URL주소2';
COMMENT ON COLUMN youth_policy.sprt_arvl_seq_yn IS '지원도착순서여부';
COMMENT ON COLUMN youth_policy.sprt_trgt_min_age IS '지원대상최소연령';
COMMENT ON COLUMN youth_policy.sprt_trgt_max_age IS '지원대상최대연령';
COMMENT ON COLUMN youth_policy.mrg_stts_cd IS '결혼상태코드';
COMMENT ON COLUMN youth_policy.earn_cnd_se_cd IS '소득조건구분코드';
COMMENT ON COLUMN youth_policy.earn_etc_cn IS '소득기타내용';
COMMENT ON COLUMN youth_policy.add_aply_qlfcnd_cn IS '추가신청자격조건내용';
COMMENT ON COLUMN youth_policy.ptcp_prp_trgt_cn IS '참여제안대상내용';
COMMENT ON COLUMN youth_policy.inq_cnt IS '조회수';
COMMENT ON COLUMN youth_policy.zip_cd IS '정책거주지역코드';
COMMENT ON COLUMN youth_policy.plcy_major_cd IS '정책전공요건코드';
COMMENT ON COLUMN youth_policy.job_cd IS '정책취업요건코드';
COMMENT ON COLUMN youth_policy.school_cd IS '정책학력요건코드';
COMMENT ON COLUMN youth_policy.s_biz_cd IS '정책특화요건코드';
COMMENT ON COLUMN youth_policy.aply_start_date IS '신청시작일자';
COMMENT ON COLUMN youth_policy.aply_end_date IS '신청종료일자';
COMMENT ON COLUMN youth_policy.frst_reg_dt IS '최초등록일시';
COMMENT ON COLUMN youth_policy.last_mdfcn_dt IS '최종수정일시';

-- 지역 테이블
CREATE TABLE youth_policy_region (
    region_id SERIAL PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL,   -- 예: 서울특별시, 구로구
    parent_id INT REFERENCES youth_policy_region(region_id)  -- NULL이면 최상위 (ex: 서울특별시)
);

-- 지역 테이블 코멘트 추가
COMMENT ON TABLE youth_policy_region IS '정책 지역 정보';
COMMENT ON COLUMN youth_policy_region.region_id IS '지역 ID (자동증가)';
COMMENT ON COLUMN youth_policy_region.region_name IS '지역명';
COMMENT ON COLUMN youth_policy_region.parent_id IS '상위 지역 ID (외래키, NULL이면 최상위 지역)';

-- 정책 조건 테이블 생성 SQL (PostgreSQL)
CREATE TABLE youth_policy_condition (
    condition_id SERIAL PRIMARY KEY,
    plcy_no VARCHAR(100) NOT NULL,
    condition_nm VARCHAR(100) NOT NULL,
    condition_cn TEXT,
    region_id INT REFERENCES youth_policy_region(region_id),
    FOREIGN KEY (plcy_no) REFERENCES youth_policy(plcy_no) ON DELETE CASCADE
);

-- 정책 조건 테이블 코멘트 추가
COMMENT ON TABLE youth_policy_condition IS '정책 조건 정보';
COMMENT ON COLUMN youth_policy_condition.condition_id IS '조건 ID (자동증가)';
COMMENT ON COLUMN youth_policy_condition.plcy_no IS '정책번호 (외래키)';
COMMENT ON COLUMN youth_policy_condition.condition_nm IS '조건명';
COMMENT ON COLUMN youth_policy_condition.condition_cn IS '조건내용';
COMMENT ON COLUMN youth_policy_condition.region_id IS '지역 ID (외래키, youth_policy_region 테이블 참조)';

