# DBeaver로 PostgreSQL 데이터베이스 설정하기

## 1. DBeaver 설치 및 연결

### 연결 설정:
- **Database Type**: PostgreSQL
- **Host**: localhost
- **Port**: 5432
- **Database**: postgres (기본)
- **Username**: postgres
- **Password**: postgres

## 2. 데이터베이스 생성

```sql
CREATE DATABASE youth_policy;
```

## 3. youth_policy 데이터베이스에 새 연결 생성

새로운 연결을 만들어서:
- **Database**: youth_policy

## 4. CSV Import 방법

### 방법 A: DBeaver UI 사용 (추천)
1. youth_policy 데이터베이스 우클릭
2. "Import Data" 선택
3. "CSV" 선택
4. 파일 경로: `C:/dev/SKN10-FINAL-5Team/data/청년정책목록_전처리완료_2025-06-09.csv`
5. 테이블명: `policies`
6. "Header row" 체크
7. 컬럼 타입 확인/수정
8. Import 실행

### 방법 B: SQL 스크립트 사용
`scripts/simple_csv_import.sql` 파일을 DBeaver에서 열고 실행

## 5. 데이터 확인

```sql
SELECT COUNT(*) FROM policies;
SELECT * FROM policies LIMIT 10;
```

## 6. 인덱스 생성 (성능 향상)

```sql
CREATE INDEX idx_policies_keywords ON policies USING gin (to_tsvector('korean', 정책키워드명));
CREATE INDEX idx_policies_support ON policies USING gin (to_tsvector('korean', 정책지원내용));
```

## 참고사항

- DBeaver는 한글 인코딩을 자동으로 처리해줍니다
- CSV import 시 데이터 타입을 자동으로 감지합니다
- 에러가 발생하면 로그를 확인할 수 있습니다

## 트러블슈팅

### 한글 깨짐 문제
- File encoding을 UTF-8로 설정
- Database charset을 UTF8로 확인

### 날짜 형식 문제
- 날짜 컬럼의 형식을 확인하고 필요시 TEXT로 import 후 변환 