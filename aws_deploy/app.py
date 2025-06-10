from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sys
import boto3
import logging
from datetime import datetime
import json

# 로컬 LangGraph 에이전트 임포트
from langgraph_agents import run_graph, db_manager
from langchain_core.messages import HumanMessage

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="청년 정책 추천 API",
    description="LangGraph 기반 청년 정책 추천 시스템",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic 모델들
class UserProfile(BaseModel):
    age: int
    income_code: Optional[str] = None
    region: Optional[str] = None
    marital_status: Optional[str] = None
    job_code: Optional[str] = None
    edu_code: Optional[str] = None
    special_code: Optional[str] = None

class PolicyRequest(BaseModel):
    message: str
    user_profile: UserProfile

class PolicyResponse(BaseModel):
    response: str
    timestamp: str
    user_profile: UserProfile
    
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database_status: str
    vector_db_status: str

# AWS S3에서 Vector DB 다운로드
def download_vector_db_from_s3():
    """S3에서 Vector DB를 다운로드하여 로컬에 저장"""
    try:
        s3_bucket = os.getenv('S3_BUCKET_NAME', 'youth-policy-vectordb')
        s3_key = os.getenv('S3_VECTORDB_KEY', 'vector_db_openai_large_combined')
        local_path = '/tmp/vector_db_openai_large_combined'
        
        if not os.path.exists(local_path):
            logger.info("S3에서 Vector DB 다운로드 중...")
            s3_client = boto3.client('s3')
            
            # S3에서 모든 파일 다운로드
            paginator = s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=s3_bucket, Prefix=s3_key):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        local_file_path = os.path.join('/tmp', key)
                        
                        # 디렉토리 생성
                        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                        
                        # 파일 다운로드
                        s3_client.download_file(s3_bucket, key, local_file_path)
                        
            logger.info("Vector DB 다운로드 완료!")
        
        return local_path
        
    except Exception as e:
        logger.error(f"Vector DB 다운로드 실패: {str(e)}")
        return None

# 시스템 초기화
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 초기화"""
    logger.info("시스템 초기화 중...")
    
    try:
        # Vector DB 다운로드 (S3에서)
        if os.getenv('AWS_ENVIRONMENT') == 'true':
            download_vector_db_from_s3()
        
        # 데이터베이스 연결 테스트
        conn = db_manager.get_pg_connection()
        if conn:
            logger.info("PostgreSQL 연결 성공!")
        
        # Vector DB 로드
        db_manager.load_vector_db()
        logger.info("Vector DB 로드 성공!")
        
    except Exception as e:
        logger.error(f"시스템 초기화 실패: {str(e)}")

# API 엔드포인트들
@app.get("/", response_model=Dict[str, str])
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "청년 정책 추천 API", 
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크 엔드포인트"""
    db_status = "connected"
    vector_status = "loaded"
    
    try:
        # PostgreSQL 연결 확인
        conn = db_manager.get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    try:
        # Vector DB 확인
        if not hasattr(db_manager, 'retriever') or db_manager.retriever is None:
            vector_status = "not_loaded"
    except Exception as e:
        vector_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy" if db_status == "connected" and vector_status == "loaded" else "unhealthy",
        timestamp=datetime.now().isoformat(),
        database_status=db_status,
        vector_db_status=vector_status
    )

@app.post("/recommend", response_model=PolicyResponse)
async def recommend_policy(request: PolicyRequest):
    """정책 추천 메인 엔드포인트"""
    try:
        logger.info(f"정책 추천 요청: {request.message}")
        
        # 메시지 변환
        messages = [HumanMessage(content=request.message)]
        
        # 사용자 프로필 변환
        user_profile = request.user_profile.dict()
        
        # 빈 정책 리스트 (실제로는 DB에서 로드하지만 여기서는 간소화)
        all_policies = []
        
        # LangGraph 실행
        response = run_graph(
            messages=messages,
            user_profile=user_profile,
            all_policies=all_policies
        )
        
        return PolicyResponse(
            response=response,
            timestamp=datetime.now().isoformat(),
            user_profile=request.user_profile
        )
        
    except Exception as e:
        logger.error(f"정책 추천 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"처리 중 오류가 발생했습니다: {str(e)}")

@app.post("/search/housing")
async def search_housing_policies(request: PolicyRequest):
    """주거 정책 전용 검색"""
    # 주거 키워드 강제 추가
    enhanced_message = f"주거 {request.message}"
    request.message = enhanced_message
    return await recommend_policy(request)

@app.post("/search/job")
async def search_job_policies(request: PolicyRequest):
    """취업 정책 전용 검색"""
    # 취업 키워드 강제 추가
    enhanced_message = f"취업 {request.message}"
    request.message = enhanced_message
    return await recommend_policy(request)

@app.get("/stats")
async def get_stats():
    """시스템 통계 정보"""
    try:
        conn = db_manager.get_pg_connection()
        cur = conn.cursor()
        
        # 전체 정책 수
        cur.execute("SELECT COUNT(*) FROM policies")
        total_policies = cur.fetchone()[0]
        
        # 주거 관련 정책 수
        cur.execute("""
            SELECT COUNT(*) FROM policies 
            WHERE 정책키워드명 ILIKE '%주거%' OR 정책지원내용 ILIKE '%주거%'
        """)
        housing_policies = cur.fetchone()[0]
        
        # 취업 관련 정책 수
        cur.execute("""
            SELECT COUNT(*) FROM policies 
            WHERE 정책키워드명 ILIKE '%취업%' OR 정책지원내용 ILIKE '%취업%'
        """)
        job_policies = cur.fetchone()[0]
        
        cur.close()
        
        return {
            "total_policies": total_policies,
            "housing_policies": housing_policies,
            "job_policies": job_policies,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"통계 조회 중 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="통계 조회 실패")

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    ) 