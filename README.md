# 청정봇

청년을 위한 맞춤형 정책 안내 및 상담 챗봇 서비스입니다.  
청정봇은 흩어진 청년 정책 정보를 통합하고, 사용자의 조건(나이, 거주지, 소득 등)에 기반한 맞춤형 추천을 제공하며, 자연어 질의를 통해 정책을 직관적으로 안내합니다.

---

## 👥 팀 소개 (Team ANDREW)

| 이름     | 역할                      | 세부 내용 |
|----------|---------------------------|-----------|
| 장윤홍   | PM                        | 기획 총괄, 협업 조율, 결과물 검토 |
| 이서영   | 웹 개발                   | 화면 설계, 프론트엔드, 백엔드 API |
| 이유호   | 인공지능 모델             | LLM 모델 선정, RAG 구성, 성능평가 |
| 정소열   | 데이터 처리 및 모델링     | 데이터 수집, 전처리, EDA, ML 개발 |
| 조현정   | 서비스 배포 및 파이프라인 | 컨테이너화, 파이프라인, CI/CD 구성 |

---

## 🎯 주요 기능

- **맞춤형 정책 추천**: 연령, 소득, 지역 등을 기반으로 사용자 맞춤형 정책 제안
- **정책 검색 챗봇**: 자연어 질문을 기반으로 정책 질의 응답
- **정책 정보 통합**: 다양한 정부/지자체 청년 정책 통합 제공
- **정책 알림 기능**: 신규 정책 발행 시 사용자에게 알림 제공
- **히스토리 기능(예정)**: 이전 상담 내역 저장 및 불러오기

---

## 🛠 사용 기술

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)

---

## 📊 데이터 처리

- **수집 출처**: 온통청년(OpenAPI)
- **원본 데이터**: 3,458개 정책, 60개 컬럼
- **전처리 결과**: 327개 정책, 38개 컬럼
- **전처리 주요 내용**:
  - 불필요 컬럼 삭제
  - 코드 → 의미 데이터 매핑
  - 만료 정책 제거
  - 정책 대분류 재정의 (`일자리`, `주거`, `기타`)

---

## 🧠 LLM & RAG 구조

- **모델 선정**: OpenAI GPT-4o (비용, 한국어 대응, 속도 고려)
- **기존 문제점**:
  - 단순 벡터 검색만으로 수치 질의 응답 불가
- **개선된 구조**:
  - DB 조회 Agent 추가
  - 질의 → DB 필터 → 벡터 검색 → 프롬프트 구성 → 응답 생성

---

## 🌐 웹 서비스 구조

- **서비스 소개 페이지**
  - 서비스 개요, 인기 정책 카드 (조회수 기반 Top 4)
- **로그인 페이지**
  - 네이버 소셜 로그인
- **챗봇 페이지**
  - 실시간 대화, 자동 입력 버튼, 추천 정책 카드
- **정책 상세 페이지**
  - 카드 클릭 시 외부 신청 URL 연결

---

## 🗓 프로젝트 일정

| 주차 | 주요 작업 |
|------|----------|
| 1주차 | 주제 선정, 시장조사 |
| 2주차 | 서비스 기획 및 설계 |
| 3주차 | 데이터 수집 및 전처리 |
| 4주차 | 모델링 및 LLM 체인 구성 |
| 5~8주차 | 모델 고도화, 웹서비스 구현 |

---

## 🔮 향후 계획

- LLM 체인 최적화 및 프롬프트 개선
- 성능 평가 지표 적용 (Precision, MRR, NDCG)
- 신규 정책 알림 기능 구현
- 챗봇 히스토리 저장 기능 구현
- 데이터 수집 파이프라인 구축 및 AWS 배포

---
