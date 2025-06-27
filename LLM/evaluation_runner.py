"""
청년정책 RAG 시스템 평가 실행 스크립트

사용법:
    python evaluation_runner.py               # 전체 평가 실행
    python evaluation_runner.py --test        # 빠른 테스트
    python evaluation_runner.py --query "질문"  # 특정 질문 테스트
"""
import sys
import argparse
import os

# 현재 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from evaluation.evaluation_manager import EvaluationManager
from utils.logging import setup_logging

logger = setup_logging()


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='청년정책 RAG 시스템 평가')
    parser.add_argument('--test', action='store_true', help='빠른 테스트 실행')
    parser.add_argument('--query', type=str, help='특정 질문으로 테스트')
    
    args = parser.parse_args()
    
    try:
        # 평가 매니저 초기화
        logger.info("평가 시스템 초기화 중...")
        evaluation_manager = EvaluationManager()
        
        if args.test or args.query:
            # 빠른 테스트 모드
            test_query = args.query if args.query else None
            result = evaluation_manager.run_quick_test(test_query)
            
        else:
            # 전체 평가 모드
            print("전체 평가를 시작합니다...")
            print("이 과정은 시간이 걸릴 수 있습니다.")
            
            results = evaluation_manager.run_full_evaluation()
            
            print("\n=== 평가 완료 ===")
            print(f"총 {results['total_queries']}개 질문 평가")
            print(f"상세 결과: {results['detailed_results']}")
            print(f"요약 리포트: {results['summary_report']}")
            print(f"마크다운 요약: {results['markdown_summary']}")
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 평가가 중단되었습니다.")
        print("\n평가가 중단되었습니다.")
        
    except Exception as e:
        logger.error(f"평가 실행 중 오류 발생: {e}")
        print(f"오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
