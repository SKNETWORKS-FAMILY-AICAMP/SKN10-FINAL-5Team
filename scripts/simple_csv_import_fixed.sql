-- PostgreSQL에서 CSV 파일 직접 import하는 수정된 SQL 스크립트
-- CSV 파일의 실제 구조에 맞춰 수정

-- 1. 데이터베이스 생성 (이미 존재하면 주석 처리)
-- CREATE DATABASE youth_policy;

-- 2. youth_policy 데이터베이스에 연결한 후 실행

-- 3. 기존 테이블 삭제 (필요시)
DROP TABLE IF EXISTS policies;

-- 4. CSV 구조에 맞춘 테이블 생성
CREATE TABLE policies (
    정책번호 TEXT,
    정책제공방법코드 TEXT,
    정책명 TEXT,
    정책키워드명 TEXT,
    정책설명내용 TEXT,
    정책대분류명 TEXT,
    정책중분류명 TEXT,
    정책지원내용 TEXT,
    주관기관코드명 TEXT,
    운영기관코드명 TEXT,
    신청기간구분코드 TEXT,
    사업기간구분코드 TEXT,
    사업기간시작일자 DATE,
    사업기간종료일자 DATE,
    사업기간기타내용 TEXT,
    정책신청방법내용 TEXT,
    심사방법내용 TEXT,
    신청URL주소 TEXT,
    제출서류내용 TEXT,
    기타사항내용 TEXT,
    참고URL주소1 TEXT,
    참고URL주소2 TEXT,
    지원도착순서여부 TEXT,
    지원대상최소연령 NUMERIC,
    지원대상최대연령 NUMERIC,
    결혼상태코드 TEXT,
    소득조건구분코드 TEXT,
    소득기타내용 TEXT,
    추가신청자격조건내용 TEXT,
    참여제안대상내용 TEXT,
    조회수 INTEGER,
    정책거주지역코드 TEXT,
    정책전공요건코드 TEXT,
    정책취업요건코드 TEXT,
    정책학력요건코드 TEXT,
    정책특화요건코드 TEXT,
    신청시작일자 DATE,
    신청종료일자 DATE
);

-- 5. CSV 파일 import
COPY policies FROM 'C:/dev/SKN10-FINAL-5Team/data/청년정책목록_전처리완료_2025-06-09.csv' 
DELIMITER ',' CSV HEADER ENCODING 'UTF8';

-- 6. 검색 성능을 위한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_policies_keywords ON policies USING gin (to_tsvector('korean', 정책키워드명));
CREATE INDEX IF NOT EXISTS idx_policies_support ON policies USING gin (to_tsvector('korean', 정책지원내용));
CREATE INDEX IF NOT EXISTS idx_policies_qualification ON policies USING gin (to_tsvector('korean', 추가신청자격조건내용));

-- 7. 정책지원금액 컬럼 추가 및 업데이트 (langgraph_agents.py에서 사용)
ALTER TABLE policies ADD COLUMN 정책지원금액 INTEGER;

-- 정책지원내용에서 금액 정보 추출 (간단한 패턴으로)
UPDATE policies SET 정책지원금액 = (
    CASE 
        WHEN 정책지원내용 LIKE '%만원%' THEN 
            CAST(REGEXP_REPLACE(
                SUBSTRING(정책지원내용 FROM '([0-9,]+)\s*만원'), 
                ',', '', 'g'
            ) AS INTEGER) * 10000
        WHEN 정책지원내용 LIKE '%원%' THEN 
            CAST(REGEXP_REPLACE(
                SUBSTRING(정책지원내용 FROM '([0-9,]+)\s*원'), 
                ',', '', 'g'
            ) AS INTEGER)
        ELSE NULL
    END
) WHERE 정책지원내용 IS NOT NULL;

-- 8. 데이터 확인
SELECT COUNT(*) AS total_policies FROM policies;
SELECT 정책명, 정책키워드명, 정책지원금액 FROM policies LIMIT 5; 