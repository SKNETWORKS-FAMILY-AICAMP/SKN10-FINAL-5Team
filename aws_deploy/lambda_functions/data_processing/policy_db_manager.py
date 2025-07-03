"""
정책 DB 관리 파이프라인
- 정책 생명주기 관리 (만료, 삭제, 아카이브)
- 데이터 품질 관리 및 정합성 검증
- 성능 최적화 및 유지보수
- 모니터링 및 알림
작성일: 2025-06-18
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import logging
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import boto3
from dataclasses import dataclass

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PolicyStats:
    """정책 통계 정보"""
    total_policies: int
    active_policies: int
    expired_policies: int
    expiring_soon: int
    missing_data_policies: int
    duplicate_policies: int

@dataclass
class MaintenanceResult:
    """유지보수 작업 결과"""
    deleted_policies: int
    archived_policies: int
    cleaned_orphan_embeddings: int
    fixed_data_issues: int
    errors: List[str]

class PolicyDBManager:
    def __init__(self, db_config, notification_config=None):
        """
        정책 DB 관리자 초기화
        
        Args:
            db_config: 데이터베이스 연결 설정
            notification_config: 알림 설정 (SNS, 이메일 등)
        """
        self.db_config = db_config
        self.notification_config = notification_config or {}
        self.conn = None
        self.cursor = None
        
        # SNS 클라이언트 초기화 (알림용)
        if self.notification_config.get('sns_topic_arn'):
            self.sns_client = boto3.client('sns')
        else:
            self.sns_client = None
    
    def connect_db(self):
        """DB 연결"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor()
            logger.info("데이터베이스 연결 성공")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
    
    def close_db(self):
        """DB 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("데이터베이스 연결 종료")
    
    def send_notification(self, message: str, subject: str = "정책 DB 관리 알림"):
        """알림 발송"""
        if self.sns_client and self.notification_config.get('sns_topic_arn'):
            try:
                self.sns_client.publish(
                    TopicArn=self.notification_config['sns_topic_arn'],
                    Message=message,
                    Subject=subject
                )
                logger.info(f"알림 발송 완료: {subject}")
            except Exception as e:
                logger.error(f"알림 발송 실패: {e}")
    
    def get_policy_statistics(self) -> PolicyStats:
        """정책 통계 정보 조회"""
        try:
            # 테이블 존재 확인
            self.cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'policies'
            """)
            
            if not self.cursor.fetchone():
                logger.error("⚠️ policies 테이블이 존재하지 않습니다!")
                raise ValueError("policies 테이블을 찾을 수 없습니다. 데이터베이스 스키마를 확인하세요.")
            
            # 전체 정책 수
            self.cursor.execute("SELECT COUNT(*) FROM policies")
            total_policies = self.cursor.fetchone()[0]
            
            # 활성 정책 수 (신청 종료일이 오늘 이후)
            self.cursor.execute("""
                SELECT COUNT(*) FROM policies 
                WHERE aply_end_ymd IS NULL OR aply_end_ymd >= CURRENT_DATE
            """)
            active_policies = self.cursor.fetchone()[0]
            
            # 만료된 정책 수
            self.cursor.execute("""
                SELECT COUNT(*) FROM policies 
                WHERE aply_end_ymd IS NOT NULL AND aply_end_ymd < CURRENT_DATE
            """)
            expired_policies = self.cursor.fetchone()[0]
            
            # 7일 내 만료 예정 정책 수
            self.cursor.execute("""
                SELECT COUNT(*) FROM policies 
                WHERE aply_end_ymd IS NOT NULL 
                AND aply_end_ymd BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
            """)
            expiring_soon = self.cursor.fetchone()[0]
            
            # 필수 데이터 누락 정책 수
            self.cursor.execute("""
                SELECT COUNT(*) FROM policies 
                WHERE plcy_nm IS NULL OR plcy_expln_cn IS NULL OR plcy_sprt_cn IS NULL
            """)
            missing_data_policies = self.cursor.fetchone()[0]
            
            # 중복 정책 수 (정책명 기준)
            self.cursor.execute("""
                SELECT COUNT(*) - COUNT(DISTINCT plcy_nm) FROM policies 
                WHERE plcy_nm IS NOT NULL
            """)
            duplicate_policies = self.cursor.fetchone()[0]
            
            return PolicyStats(
                total_policies=total_policies,
                active_policies=active_policies,
                expired_policies=expired_policies,
                expiring_soon=expiring_soon,
                missing_data_policies=missing_data_policies,
                duplicate_policies=duplicate_policies
            )
            
        except Exception as e:
            logger.error(f"정책 통계 조회 실패: {e}")
            raise
    
    def find_expired_policies(self, grace_period_days: int = 30) -> List[str]:
        """
        만료된 정책 조회
        
        Args:
            grace_period_days: 만료 후 유예 기간 (일)
        
        Returns:
            만료된 정책 번호 리스트
        """
        try:
            # 테이블 존재 확인
            self.cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'policies'
            """)
            
            if not self.cursor.fetchone():
                logger.error("⚠️ policies 테이블이 존재하지 않습니다!")
                raise ValueError("policies 테이블을 찾을 수 없습니다.")
            
            # 현재 날짜에서 유예기간을 뺀 날짜 (예: 오늘이 2025-01-01이고 grace_period_days=30이면 2024-12-02)
            grace_date = datetime.now() - timedelta(days=grace_period_days)
            
            # 수정된 쿼리: 현재 날짜 기준으로 이미 만료되고 유예기간도 지난 정책만 조회
            query = """
                SELECT plcy_no FROM policies 
                WHERE aply_end_ymd IS NOT NULL 
                AND aply_end_ymd < CURRENT_DATE  -- 현재 날짜 기준으로 이미 만료된 정책
                AND aply_end_ymd < %s            -- 유예기간도 지난 정책
                ORDER BY aply_end_ymd
                LIMIT 100                        -- 안전을 위해 한 번에 최대 100개만 처리
            """
            
            self.cursor.execute(query, (grace_date.date(),))
            expired_policies = [row[0] for row in self.cursor.fetchall()]
            
            logger.info(f"현재 날짜 기준 만료 + {grace_period_days}일 유예기간 초과 정책 {len(expired_policies)}개 발견")
            
            # 디버깅을 위한 로깅 추가
            if expired_policies:
                logger.info(f"만료된 정책 예시 (처음 5개): {expired_policies[:5]}")
                
            return expired_policies
            
        except Exception as e:
            logger.error(f"만료 정책 조회 실패: {e}")
            raise
    
    def find_expiring_soon_policies(self, days_ahead: int = 7) -> List[Dict]:
        """
        곧 만료될 정책 조회
        
        Args:
            days_ahead: 몇 일 후까지 확인할지
        
        Returns:
            만료 예정 정책 정보 리스트
        """
        try:
            future_date = datetime.now() + timedelta(days=days_ahead)
            
            query = """
                SELECT plcy_no, plcy_nm, aply_end_ymd 
                FROM policies 
                WHERE aply_end_ymd IS NOT NULL 
                AND aply_end_ymd BETWEEN CURRENT_DATE AND %s
                ORDER BY aply_end_ymd
            """
            
            self.cursor.execute(query, (future_date.date(),))
            results = self.cursor.fetchall()
            
            expiring_policies = []
            for plcy_no, plcy_nm, end_date in results:
                days_remaining = (end_date - datetime.now().date()).days
                expiring_policies.append({
                    'policy_no': plcy_no,
                    'policy_name': plcy_nm,
                    'end_date': end_date,
                    'days_remaining': days_remaining
                })
            
            logger.info(f"{days_ahead}일 내 만료 예정 정책 {len(expiring_policies)}개 발견")
            return expiring_policies
            
        except Exception as e:
            logger.error(f"만료 예정 정책 조회 실패: {e}")
            raise
    
    def archive_expired_policies(self, policy_numbers: List[str]) -> int:
        """
        만료된 정책을 아카이브 테이블로 이동
        
        Args:
            policy_numbers: 아카이브할 정책 번호 리스트
        
        Returns:
            아카이브된 정책 수
        """
        if not policy_numbers:
            return 0
        
        # 안전장치: 한 번에 너무 많은 정책을 삭제하는 것을 방지
        MAX_ARCHIVE_COUNT = 500
        if len(policy_numbers) > MAX_ARCHIVE_COUNT:
            logger.error(f"⚠️ 위험: {len(policy_numbers)}개 정책 아카이브 요청됨 (최대 {MAX_ARCHIVE_COUNT}개 허용)")
            logger.error(f"⚠️ 대량 삭제 방지를 위해 아카이브 작업을 중단합니다")
            raise ValueError(f"아카이브 요청 정책 수가 너무 많습니다: {len(policy_numbers)}개 (최대 {MAX_ARCHIVE_COUNT}개)")
        
        try:
            # 아카이브할 정책들의 세부 정보 로깅
            logger.info(f"아카이브 대상 정책 수: {len(policy_numbers)}")
            if policy_numbers:
                logger.info(f"아카이브 대상 정책 번호 예시: {policy_numbers[:10]}")
            
            # 아카이브 테이블 존재 확인 및 생성
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS policies_archive (
                    LIKE policies INCLUDING ALL
                );
            """)
            
            # 아카이브 테이블에 만료된 정책 복사
            archive_query = """
                INSERT INTO policies_archive 
                SELECT * FROM policies 
                WHERE plcy_no = ANY(%s)
                ON CONFLICT (plcy_no) DO NOTHING
            """
            
            self.cursor.execute(archive_query, (policy_numbers,))
            archived_count = self.cursor.rowcount
            
            logger.info(f"✅ {archived_count}개 정책을 아카이브 테이블에 복사 완료")
            
            # 원본 테이블에서 삭제 (추가 확인)
            if archived_count > 0:
                delete_query = "DELETE FROM policies WHERE plcy_no = ANY(%s)"
                self.cursor.execute(delete_query, (policy_numbers,))
                deleted_count = self.cursor.rowcount
                
                # 관련 임베딩도 삭제
                delete_embeddings_query = "DELETE FROM policy_embeddings WHERE plcy_no = ANY(%s)"
                self.cursor.execute(delete_embeddings_query, (policy_numbers,))
                embedding_deleted_count = self.cursor.rowcount
                
                self.conn.commit()
                
                logger.info(f"✅ 원본 테이블에서 {deleted_count}개 정책 삭제 완료")
                logger.info(f"✅ 관련 임베딩 {embedding_deleted_count}개 삭제 완료")
                
                return archived_count
            else:
                logger.warning("⚠️ 아카이브된 정책이 없어 원본 삭제를 건너뜁니다")
                return 0
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"❌ 정책 아카이브 실패: {e}")
            raise
    
    def clean_orphan_embeddings(self) -> int:
        """고아 임베딩 정리"""
        try:
            # 고아 임베딩 찾기
            query = """
                SELECT pe.plcy_no 
                FROM policy_embeddings pe 
                LEFT JOIN policies p ON pe.plcy_no = p.plcy_no 
                WHERE p.plcy_no IS NULL
            """
            
            self.cursor.execute(query)
            orphan_embeddings = [row[0] for row in self.cursor.fetchall()]
            
            if orphan_embeddings:
                delete_query = "DELETE FROM policy_embeddings WHERE plcy_no = ANY(%s)"
                self.cursor.execute(delete_query, (orphan_embeddings,))
                deleted_count = self.cursor.rowcount
                
                self.conn.commit()
                logger.info(f"{deleted_count}개 고아 임베딩 삭제 완료")
                return deleted_count
            else:
                logger.info("고아 임베딩 없음")
                return 0
                
        except Exception as e:
            self.conn.rollback()
            logger.error(f"고아 임베딩 정리 실패: {e}")
            raise
    
    def run_maintenance(self, 
                       delete_expired: bool = False,
                       archive_expired: bool = True,
                       grace_period_days: int = 30,
                       clean_orphans: bool = True,
                       notify_expiring: bool = True) -> MaintenanceResult:
        """
        종합 유지보수 작업 실행
        
        Args:
            delete_expired: 만료된 정책 삭제 여부
            archive_expired: 만료된 정책 아카이브 여부
            grace_period_days: 유예 기간
            clean_orphans: 고아 임베딩 정리 여부
            notify_expiring: 만료 예정 알림 여부
        
        Returns:
            유지보수 작업 결과
        """
        errors = []
        deleted_policies = 0
        archived_policies = 0
        cleaned_orphan_embeddings = 0
        fixed_data_issues = 0
        
        try:
            self.connect_db()
            
            # 만료된 정책 처리
            expired_policies = self.find_expired_policies(grace_period_days)
            
            if expired_policies and archive_expired:
                try:
                    archived_policies = self.archive_expired_policies(expired_policies)
                except Exception as e:
                    errors.append(f"정책 아카이브 실패: {str(e)}")
            
            # 고아 임베딩 정리
            if clean_orphans:
                try:
                    cleaned_orphan_embeddings = self.clean_orphan_embeddings()
                except Exception as e:
                    errors.append(f"고아 임베딩 정리 실패: {str(e)}")
            
            # 만료 예정 정책 알림
            if notify_expiring:
                try:
                    expiring_policies = self.find_expiring_soon_policies(7)
                    if expiring_policies:
                        message = f"만료 예정 정책 {len(expiring_policies)}개가 있습니다."
                        self.send_notification(message, "정책 만료 예정 알림")
                except Exception as e:
                    errors.append(f"만료 예정 알림 실패: {str(e)}")
            
            # 통계 정보 수집 및 알림
            try:
                stats = self.get_policy_statistics()
                summary_message = f"""정책 DB 유지보수 완료
전체: {stats.total_policies}, 활성: {stats.active_policies}, 만료: {stats.expired_policies}
아카이브: {archived_policies}개, 정리된 임베딩: {cleaned_orphan_embeddings}개"""
                
                self.send_notification(summary_message, "정책 DB 유지보수 완료 보고")
                
            except Exception as e:
                errors.append(f"통계 수집 실패: {str(e)}")
            
            return MaintenanceResult(
                deleted_policies=deleted_policies,
                archived_policies=archived_policies,
                cleaned_orphan_embeddings=cleaned_orphan_embeddings,
                fixed_data_issues=fixed_data_issues,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"유지보수 작업 중 치명적 오류: {e}")
            errors.append(f"치명적 오류: {str(e)}")
            
            return MaintenanceResult(
                deleted_policies=0,
                archived_policies=0,
                cleaned_orphan_embeddings=0,
                fixed_data_issues=0,
                errors=errors
            )
        
        finally:
            self.close_db()

def main():
    """메인 실행 함수"""
    # DB 연결 설정
    db_config = {
        'host': os.getenv("DB_HOST", 'localhost'),
        'database': os.getenv("DB_NAME", 'youth_policy_db'),
        'user': os.getenv("DB_USER", 'postgres'),
        'password': os.getenv("DB_PASSWORD", 'your_password'),
        'port': os.getenv("DB_PORT", 5432)
    }
    
    # 알림 설정
    notification_config = {
        'sns_topic_arn': os.getenv('SNS_TOPIC_ARN')
    }
    
    # DB 관리자 생성 및 유지보수 실행
    manager = PolicyDBManager(db_config, notification_config)
    
    result = manager.run_maintenance(
        delete_expired=False,      # 삭제 대신 아카이브
        archive_expired=True,      # 만료된 정책 아카이브
        grace_period_days=30,      # 30일 유예기간
        clean_orphans=True,        # 고아 임베딩 정리
        notify_expiring=True       # 만료 예정 알림
    )
    
    logger.info(f"유지보수 완료: {result}")

if __name__ == "__main__":
    main() 