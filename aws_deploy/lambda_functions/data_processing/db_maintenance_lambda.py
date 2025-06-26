import json
import os
import logging
from datetime import datetime
from policy_db_manager import PolicyDBManager

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def lambda_handler(event, context):
    """
    정책 DB 유지보수를 위한 Lambda 함수
    EventBridge 스케줄러에 의해 정기적으로 실행됨
    
    예상 스케줄:
    - 매일 새벽 2시: 만료 예정 알림 체크
    - 주 1회 일요일: 만료된 정책 아카이브
    - 월 1회: 전체 유지보수 작업
    """
    try:
        logger.info("정책 DB 유지보수 Lambda 함수 시작")
        
        # 이벤트에서 작업 유형 확인
        maintenance_type = event.get('maintenance_type', 'daily')
        
        # PostgreSQL 연결 설정
        db_config = {
            'host': os.environ['DB_HOST'],
            'port': os.environ['DB_PORT'],
            'database': os.environ['DB_NAME'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD']
        }
        
        # 알림 설정
        notification_config = {
            'sns_topic_arn': os.environ.get('SNS_TOPIC_ARN')
        }
        
        # DB 관리자 생성
        manager = PolicyDBManager(db_config, notification_config)
        
        # 작업 유형에 따른 다른 유지보수 실행
        if maintenance_type == 'daily':
            # 매일: 만료 예정 알림만
            result = manager.run_maintenance(
                delete_expired=False,
                archive_expired=False,
                grace_period_days=30,
                clean_orphans=False,
                notify_expiring=True
            )
            operation = "일일 점검"
            
        elif maintenance_type == 'weekly':
            # 주간: 만료된 정책 아카이브 + 고아 임베딩 정리
            result = manager.run_maintenance(
                delete_expired=False,
                archive_expired=True,
                grace_period_days=30,
                clean_orphans=True,
                notify_expiring=True
            )
            operation = "주간 정리"
            
        elif maintenance_type == 'monthly':
            # 월간: 전체 유지보수 (유예기간 60일)
            result = manager.run_maintenance(
                delete_expired=False,
                archive_expired=True,
                grace_period_days=60,
                clean_orphans=True,
                notify_expiring=True
            )
            operation = "월간 유지보수"
            
        else:
            # 기본: 일일 점검
            result = manager.run_maintenance(
                delete_expired=False,
                archive_expired=False,
                grace_period_days=30,
                clean_orphans=False,
                notify_expiring=True
            )
            operation = "기본 점검"
        
        # 결과 로깅
        logger.info(f"{operation} 완료:")
        logger.info(f"- 아카이브된 정책: {result.archived_policies}개")
        logger.info(f"- 정리된 고아 임베딩: {result.cleaned_orphan_embeddings}개")
        
        if result.errors:
            logger.warning(f"- 오류 {len(result.errors)}개 발생: {result.errors}")
        
        # 응답 반환
        response_body = {
            'message': f'{operation} 완료',
            'maintenance_type': maintenance_type,
            'result': {
                'archived_policies': result.archived_policies,
                'cleaned_orphan_embeddings': result.cleaned_orphan_embeddings,
                'errors_count': len(result.errors),
                'errors': result.errors
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"정책 DB 유지보수 중 오류 발생: {str(e)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'유지보수 실패: {str(e)}',
                'maintenance_type': event.get('maintenance_type', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False)
        } 