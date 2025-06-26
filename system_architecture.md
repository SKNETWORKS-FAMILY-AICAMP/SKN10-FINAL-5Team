# 시스템 아키텍처

## 프로젝트 개요
청년정책 정보를 제공하는 AI 챗봇 시스템으로, Django 웹 애플리케이션과 LLM 기반 RAG(Retrieval-Augmented Generation) 시스템을 통합한 플랫폼입니다.

## 컴포넌트 다이어그램

### 구성요소

#### 1. Web Layer (Django 애플리케이션)
- **Home 앱**: 메인 페이지, 정책 목록 조회 및 상세정보 API
- **User 앱**: 네이버 OAuth 기반 사용자 인증, JWT 토큰 관리
- **Chatbot 앱**: 챗봇 인터페이스, 세션 관리, 메시지 처리

#### 2. Authentication & Security
- **JWT 미들웨어**: 액세스/리프레시 토큰 검증
- **네이버 OAuth**: 소셜 로그인 통합
- **CORS 처리**: 크로스 도메인 요청 관리

#### 3. Data Layer
- **PostgreSQL 데이터베이스**: 
  - 사용자 정보 (User, RefreshToken, NotificationStatus)
  - 정책 데이터 (Policies)
  - 챗봇 세션 (ChatSession, Message, SearchHistory, RecommendInterest)
- **벡터 임베딩**: 정책 검색을 위한 임베딩 데이터

#### 4. AI/LLM Layer
- **Advanced RAG 시스템**: LangGraph 기반 고급 검색 시스템
- **Naive RAG 시스템**: 기본 유사도 기반 검색
- **OpenAI API**: GPT 모델을 활용한 자연어 처리

#### 5. Data Processing
- **전처리 파이프라인**: 청년정책 데이터 정제 및 변환
- **임베딩 생성**: 텍스트 데이터의 벡터 변환
- **코드 매핑**: 정책 분류 체계 정규화

#### 6. Infrastructure (AWS)
- **Lambda Functions**: 데이터 처리 자동화
- **CloudFormation**: 인프라 관리
- **S3**: 파일 저장소

### 설명

#### 시스템 아키텍처 특징
1. **모듈화된 Django 앱 구조**: 각 기능별로 독립적인 앱으로 분리
2. **RESTful API**: 프론트엔드와 백엔드 간 JSON 기반 통신
3. **RAG 기반 AI 시스템**: 정책 데이터베이스와 LLM을 결합한 지능형 검색
4. **실시간 세션 관리**: 사용자별 챗봇 대화 세션 유지
5. **클라우드 네이티브**: AWS 서비스를 활용한 확장 가능한 구조

## 시퀀스 다이어그램

### 참여자
- **사용자 (User)**
- **Web 브라우저 (Browser)**
- **Django 웹서버 (Web Server)**
- **JWT 미들웨어 (JWT Middleware)**
- **네이버 OAuth API (Naver OAuth)**
- **PostgreSQL DB (Database)**
- **RAG 시스템 (LLM/RAG)**
- **OpenAI API (OpenAI)**

### 주요흐름

#### 1. 사용자 인증 흐름
```
사용자 → 브라우저: 로그인 요청
브라우저 → Web Server: GET /user/login/
Web Server → 브라우저: 로그인 페이지 반환
사용자 → 브라우저: 네이버 로그인 클릭
브라우저 → Naver OAuth: 인증 요청
Naver OAuth → 브라우저: 인증 코드 반환
브라우저 → Web Server: POST /user/naver/callback/
Web Server → Naver OAuth: 토큰 교환 요청
Naver OAuth → Web Server: 액세스 토큰 반환
Web Server → Naver OAuth: 사용자 정보 요청
Naver OAuth → Web Server: 사용자 정보 반환
Web Server → Database: 사용자 생성/조회
Database → Web Server: 사용자 정보
Web Server → Web Server: JWT 토큰 생성
Web Server → 브라우저: 쿠키 설정 + 메인페이지 리다이렉트
```

#### 2. 챗봇 대화 흐름
```
사용자 → 브라우저: 질문 입력
브라우저 → Web Server: POST /chatbot/api/chat/
Web Server → JWT Middleware: 토큰 검증
JWT Middleware → Web Server: 인증 완료
Web Server → Database: 세션 조회/생성
Database → Web Server: 세션 정보
Web Server → RAG System: 질문 분석 요청
RAG System → RAG System: 질의 분류 (주거/일자리/기타)
RAG System → Database: 관련 정책 검색
Database → RAG System: 정책 데이터
RAG System → OpenAI API: LLM 응답 생성 요청
OpenAI API → RAG System: 응답 생성
RAG System → Web Server: 최종 응답
Web Server → Database: 메시지 저장
Database → Web Server: 저장 완료
Web Server → 브라우저: JSON 응답 반환
브라우저 → 사용자: 답변 표시
```

#### 3. 정책 조회 흐름
```
사용자 → 브라우저: 메인페이지 접근
브라우저 → Web Server: GET /
Web Server → Database: 정책 목록 조회
Database → Web Server: 정책 데이터
Web Server → 브라우저: 메인페이지 + 정책 목록
사용자 → 브라우저: 정책 상세보기 클릭
브라우저 → Web Server: GET /api/policy/{id}/
Web Server → Database: 정책 상세정보 조회
Database → Web Server: 상세 정책 데이터
Web Server → 브라우저: JSON 형태 정책 상세정보
브라우저 → 사용자: 상세정보 모달 표시
```

## 액티비티 다이어그램

### 구성

#### 1. 데이터 처리 파이프라인
- **데이터 수집**: 청년정책 원본 데이터 로드
- **전처리**: 코드 매핑, 지역정보 변환, 중복 제거
- **임베딩 생성**: OpenAI API를 통한 텍스트 벡터화
- **데이터베이스 저장**: PostgreSQL에 정책 데이터 및 임베딩 저장

#### 2. RAG 시스템 처리
- **질의 수신**: 사용자 질문 입력
- **질의 분석**: LLM을 통한 질문 분류 (주거/일자리/기타)
- **정책 검색**: 임베딩 유사도 기반 관련 정책 검색
- **컨텍스트 구성**: 검색된 정책들을 컨텍스트로 구성
- **응답 생성**: LLM을 통한 자연어 응답 생성
- **후처리**: 응답 검증 및 포맷팅

#### 3. 세션 관리
- **세션 생성**: 새로운 대화 시작 시 세션 생성
- **메시지 저장**: 사용자 질문과 챗봇 응답 저장
- **세션 이력 관리**: 사용자별 대화 이력 유지
- **검색 기록**: 사용자 질의 패턴 분석을 위한 검색 이력 저장

### 주요 액션 노드

#### 인증 관련
- **네이버 OAuth 인증**
- **JWT 토큰 생성/검증**
- **사용자 세션 관리**
- **권한 검사**

#### 데이터 처리
- **정책 데이터 전처리**
- **임베딩 벡터 생성**
- **데이터베이스 CRUD 작업**
- **검색 인덱스 관리**

#### AI/ML 처리
- **자연어 질의 분석**
- **유사도 기반 검색**
- **LLM 응답 생성**
- **결과 후처리**

#### 사용자 인터페이스
- **웹페이지 렌더링**
- **AJAX 통신 처리**
- **실시간 챗봇 인터페이스**
- **정책 상세정보 표시**

## 기술 스택

### Backend
- **Django 5.2.1**: 웹 프레임워크
- **PostgreSQL**: 관계형 데이터베이스
- **Django REST Framework**: API 개발

### AI/ML
- **LangChain**: LLM 애플리케이션 프레임워크
- **LangGraph**: 복잡한 LLM 워크플로우 관리
- **OpenAI API**: GPT 모델 활용
- **pgvector**: PostgreSQL 벡터 검색

### Authentication
- **JWT (JSON Web Token)**: 토큰 기반 인증
- **네이버 OAuth 2.0**: 소셜 로그인

### Infrastructure
- **AWS Lambda**: 서버리스 컴퓨팅
- **AWS CloudFormation**: 인프라 코드화
- **AWS S3**: 객체 스토리지

### Frontend
- **HTML/CSS/JavaScript**: 기본 웹 기술
- **Bootstrap**: CSS 프레임워크
- **AJAX**: 비동기 통신