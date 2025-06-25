#!/usr/bin/env python3
"""
Lambda5: Database Maintenance
청년정책 데이터베이스 유지보수를 위한 Lambda 함수

기능:
- 만료된 정책 데이터 아카이브
- 고아 레코드 정리
- 데이터 품질 검사
- 성능 최적화 제안
- 유지보수 보고서 생성

작성일: 2025-06-25
"""

import json
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
import logging
from typing import Dict, Any, List
from dataclasses import dataclass

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MaintenanceResult:
    """유지보수 작업 결과"""
    total_policies: int
    active_policies: int
    expired_policies: int
    archived_policies: int
    cleaned_orphans: int
    data_quality_issues: int
    recommendations: List[str]
    execution_time_seconds: float

class DatabaseMaintenanceManager:
    """데이터베이스 유지보수 관리자"""
    
    def __init__(self):
        """유지보수 관리자 초기화"""
        self.db_config = {
            'host': os.environ['DB_HOST'],
            'port': int(os.environ.get('DB_PORT', 5432)),
            'database': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD']
        }
        
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ['S3_BUCKET_NAME']
        
        # SNS 알림 설정 (옵션)
        self.sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
        self.sns_client = boto3.client('sns') if self.sns_topic_arn else None
    
    def get_db_connection(self) -> psycopg2.extensions.connection:
        """PostgreSQL 연결 생성"""
        try:
            conn = psycopg2.connect(**self.db_config)
            conn.autocommit = False
            logger.info("PostgreSQL 연결 성공")
            return conn
        except Exception as e:
            logger.error(f"PostgreSQL 연결 실패: {str(e)}")
            raise
    
    def get_database_statistics(self, cursor) -> Dict[str, int]:
        """데이터베이스 통계 수집"""
        logger.info("데이터베이스 통계 수집 중...")
        
        stats = {
            'total_policies': 0,
            'active_policies': 0,
            'expired_policies': 0,
            'missing_data': 0,
            'duplicate_policies': 0
        }
        
        try:
            # 테이블 존재 확인
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('policies', 'youth_policies')
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                logger.warning("정책 테이블이 존재하지 않습니다.")
                return stats
            
            # 사용할 테이블명 결정
            table_name = 'policies' if 'policies' in tables else 'youth_policies'
            
            # 전체 정책 수
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            stats['total_policies'] = cursor.fetchone()[0]
            
            # 활성 정책 수 (만료일이 없거나 미래인 정책)
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE (aply_end_ymd IS NULL OR aply_end_ymd >= CURRENT_DATE)
                   OR (last_mdfcn_dt IS NULL OR last_mdfcn_dt >= CURRENT_DATE - INTERVAL '30 days')
            """)
            stats['active_policies'] = cursor.fetchone()[0]
            
            stats['expired_policies'] = stats['total_policies'] - stats['active_policies']
            
            # 데이터 품질 검사
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE plcy_nm IS NULL OR plcy_nm = '' 
                   OR plcy_expln_cn IS NULL OR plcy_expln_cn = ''
            """)
            stats['missing_data'] = cursor.fetchone()[0]
            
            # 중복 정책 검사
            cursor.execute(f"""
                SELECT COUNT(*) - COUNT(DISTINCT plcy_nm) FROM {table_name} 
                WHERE plcy_nm IS NOT NULL AND plcy_nm != ''
            """)
            stats['duplicate_policies'] = cursor.fetchone()[0]
            
            return stats
            
        except Exception as e:
            logger.error(f"통계 수집 실패: {e}")
            return stats
    
    def archive_expired_policies(self, cursor, grace_period_days: int = 60) -> int:
        """만료된 정책 아카이브"""
        logger.info(f"만료된 정책 아카이브 중... (유예기간: {grace_period_days}일)")
        
        try:
            # 테이블 존재 확인
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('policies', 'youth_policies')
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            if not tables:
                return 0
            
            table_name = 'policies' if 'policies' in tables else 'youth_policies'
            archive_table = f"{table_name}_archive"
            
            # 아카이브 테이블 생성 (존재하지 않으면)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {archive_table} (
                    LIKE {table_name} INCLUDING ALL
                );
            """)
            
            # 아카이브할 정책 찾기 (60일 이상 만료된 정책)
            cutoff_date = datetime.now() - timedelta(days=grace_period_days)
            
            cursor.execute(f"""
                SELECT plcy_no FROM {table_name} 
                WHERE aply_end_ymd IS NOT NULL 
                AND aply_end_ymd < %s
                LIMIT 100
            """, (cutoff_date.date(),))
            
            expired_policies = [row[0] for row in cursor.fetchall()]
            
            if not expired_policies:
                logger.info("아카이브할 만료 정책이 없습니다.")
                return 0
            
            # 아카이브 테이블로 복사
            placeholders = ','.join(['%s'] * len(expired_policies))
            cursor.execute(f"""
                INSERT INTO {archive_table} 
                SELECT * FROM {table_name} 
                WHERE plcy_no IN ({placeholders})
                ON CONFLICT (plcy_no) DO NOTHING
            """, expired_policies)
            
            archived_count = cursor.rowcount
            
            # 원본 테이블에서 삭제 (시뮬레이션 모드에서는 주석 처리)
            # cursor.execute(f"DELETE FROM {table_name} WHERE plcy_no IN ({placeholders})", expired_policies)
            
            logger.info(f"{archived_count}개 정책 아카이브 완료 (삭제는 시뮬레이션)")
            return archived_count
            
        except Exception as e:
            logger.error(f"정책 아카이브 실패: {e}")
            return 0
    
    def clean_orphan_records(self, cursor) -> int:
        """고아 레코드 정리"""
        logger.info("고아 레코드 정리 중...")
        
        try:
            # 임베딩 테이블 존재 확인
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'policy_embeddings'
            """)
            
            if not cursor.fetchone():
                logger.info("임베딩 테이블이 존재하지 않습니다.")
                return 0
            
            # 정책 테이블 확인
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN ('policies', 'youth_policies')
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            if not tables:
                return 0
            
            table_name = 'policies' if 'policies' in tables else 'youth_policies'
            
            # 고아 임베딩 찾기
            cursor.execute(f"""
                SELECT pe.plcy_no FROM policy_embeddings pe 
                LEFT JOIN {table_name} p ON pe.plcy_no = p.plcy_no 
                WHERE p.plcy_no IS NULL
                LIMIT 50
            """)
            
            orphan_embeddings = [row[0] for row in cursor.fetchall()]
            
            if not orphan_embeddings:
                logger.info("고아 임베딩이 없습니다.")
                return 0
            
            # 고아 임베딩 삭제 (시뮬레이션 모드에서는 카운트만)
            # placeholders = ','.join(['%s'] * len(orphan_embeddings))
            # cursor.execute(f"DELETE FROM policy_embeddings WHERE plcy_no IN ({placeholders})", orphan_embeddings)
            
            logger.info(f"{len(orphan_embeddings)}개 고아 임베딩 정리 (시뮬레이션)")
            return len(orphan_embeddings)
            
        except Exception as e:
            logger.error(f"고아 레코드 정리 실패: {e}")
            return 0
    
    def generate_recommendations(self, stats: Dict[str, int]) -> List[str]:
        """유지보수 권장사항 생성"""
        recommendations = []
        
        if stats['expired_policies'] > 100:
            recommendations.append(f"만료된 정책 {stats['expired_policies']}개 아카이브 권장")
        
        if stats['missing_data'] > 0:
            recommendations.append(f"누락 데이터 {stats['missing_data']}건 보완 필요")
        
        if stats['duplicate_policies'] > 0:
            recommendations.append(f"중복 정책 {stats['duplicate_policies']}건 정리 권장")
        
        if stats['total_policies'] > 5000:
            recommendations.append("인덱스 최적화 및 VACUUM 작업 권장")
        
        recommendations.append("정기적인 백업 정책 점검")
        recommendations.append("성능 모니터링 강화")
        
        return recommendations
    
    def send_notification(self, result: MaintenanceResult):
        """유지보수 결과 알림 발송"""
        if not self.sns_client or not self.sns_topic_arn:
            return
        
        try:
            message = f"""
청년정책 DB 유지보수 완료 보고

📊 통계:
• 전체 정책: {result.total_policies:,}개
• 활성 정책: {result.active_policies:,}개  
• 만료 정책: {result.expired_policies:,}개

🔧 작업 결과:
• 아카이브된 정책: {result.archived_policies}개
• 정리된 고아 레코드: {result.cleaned_orphans}개
• 데이터 품질 이슈: {result.data_quality_issues}건

📋 권장사항:
{chr(10).join(f"• {rec}" for rec in result.recommendations[:3])}

⏱️ 실행 시간: {result.execution_time_seconds:.1f}초
🕐 실행 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            self.sns_client.publish(
                TopicArn=self.sns_topic_arn,
                Subject="청년정책 DB 유지보수 완료",
                Message=message
            )
            
            logger.info("유지보수 완료 알림 발송")
            
        except Exception as e:
            logger.error(f"알림 발송 실패: {e}")
    
    def run_maintenance(self, maintenance_type: str = "weekly") -> MaintenanceResult:
        """유지보수 작업 실행"""
        start_time = datetime.now()
        logger.info(f"DB 유지보수 시작: {maintenance_type}")
        
        conn = self.get_db_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # 1. 통계 수집
                stats = self.get_database_statistics(cursor)
                
                # 2. 만료된 정책 아카이브
                archived_policies = 0
                if maintenance_type in ["weekly", "monthly"]:
                    grace_period = 30 if maintenance_type == "weekly" else 60
                    archived_policies = self.archive_expired_policies(cursor, grace_period)
                
                # 3. 고아 레코드 정리
                cleaned_orphans = 0
                if maintenance_type in ["weekly", "monthly"]:
                    cleaned_orphans = self.clean_orphan_records(cursor)
                
                # 4. 권장사항 생성
                recommendations = self.generate_recommendations(stats)
                
                # 트랜잭션 커밋
                conn.commit()
                
                # 5. 결과 객체 생성
                execution_time = (datetime.now() - start_time).total_seconds()
                
                result = MaintenanceResult(
                    total_policies=stats['total_policies'],
                    active_policies=stats['active_policies'],
                    expired_policies=stats['expired_policies'],
                    archived_policies=archived_policies,
                    cleaned_orphans=cleaned_orphans,
                    data_quality_issues=stats['missing_data'] + stats['duplicate_policies'],
                    recommendations=recommendations,
                    execution_time_seconds=execution_time
                )
                
                # 6. 알림 발송
                self.send_notification(result)
                
                return result
                
        except Exception as e:
            conn.rollback()
            logger.error(f"유지보수 실행 실패: {e}")
            raise
        finally:
            conn.close()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda 핸들러: DB 유지보수 실행
    
    Args:
        event: Lambda 이벤트 (maintenance_type 포함 가능)
        context: Lambda 컨텍스트
        
    Returns:
        유지보수 결과
    """
    try:
        logger.info("Lambda5 DB 유지보수 시작")
        
        # 유지보수 타입 결정
        maintenance_type = event.get('maintenance_type', 'weekly')
        
        # 유지보수 관리자 생성 및 실행
        manager = DatabaseMaintenanceManager()
        result = manager.run_maintenance(maintenance_type)
        
        # 응답 생성
        response_body = {
            'message': 'Database maintenance completed successfully',
            'maintenance_type': maintenance_type,
            'statistics': {
                'total_policies': result.total_policies,
                'active_policies': result.active_policies,
                'expired_policies': result.expired_policies
            },
            'operations': {
                'archived_policies': result.archived_policies,
                'cleaned_orphans': result.cleaned_orphans,
                'data_quality_issues': result.data_quality_issues
            },
            'recommendations': result.recommendations,
            'execution_time_seconds': result.execution_time_seconds,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"DB 유지보수 완료: {maintenance_type}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"DB 유지보수 실패: {str(e)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Database maintenance failed: {str(e)}',
                'maintenance_type': event.get('maintenance_type', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False)
        } 