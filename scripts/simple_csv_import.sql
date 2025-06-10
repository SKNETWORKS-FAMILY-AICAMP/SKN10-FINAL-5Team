-- PostgreSQL에서 CSV 파일 직접 import하는 SQL 스크립트
-- pgAdmin이나 다른 PostgreSQL 클라이언트에서 실행

-- 1. 데이터베이스 생성 (이미 존재하면 주석 처리)
-- CREATE DATABASE youth_policy;

-- 2. youth_policy 데이터베이스에 연결한 후 실행

-- 3. 테이블 생성
CREATE TABLE IF NOT EXISTS policies (
    정책명 TEXT,
    정책키워드명 TEXT,
    정책지원내용 TEXT,
    추가신청자격조건내용 TEXT,
    정책지원금액 INTEGER,
    지원대상최소연령 INTEGER,
    지원대상최대연령 INTEGER,
    소득조건구분코드 TEXT,
    정책거주지역코드 TEXT,
    결혼상태코드 TEXT,
    정책취업요건코드 TEXT,
    정책학력요건코드 TEXT,
    정책특화요건코드 TEXT,
    사업기간시작일자 DATE,
    사업기간종료일자 DATE,
    신청기간시작일자 DATE,
    신청기간종료일자 DATE
);

-- 4. CSV 파일 import (경로를 실제 파일 경로로 수정하세요)
-- Windows 경로 예시:
COPY policies FROM 'C:/dev/SKN10-FINAL-5Team/data/청년정책목록_전처리완료_2025-06-09.csv' 
DELIMITER ',' CSV HEADER ENCODING 'UTF8';

-- 5. 검색 성능을 위한 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_policies_keywords ON policies USING gin (to_tsvector('korean', 정책키워드명));
CREATE INDEX IF NOT EXISTS idx_policies_support ON policies USING gin (to_tsvector('korean', 정책지원내용));
CREATE INDEX IF NOT EXISTS idx_policies_qualification ON policies USING gin (to_tsvector('korean', 추가신청자격조건내용));

-- 6. 데이터 확인
SELECT COUNT(*) FROM policies;
SELECT * FROM policies LIMIT 5; 