"""
청년 정책 검색 시스템 테스트 스크립트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LLM.langgraph_agents import (
    db_manager, run_graph, DatabaseManager
)
from langchain_core.messages import HumanMessage
import logging

# 로깅 설정 (UTF-8 인코딩 추가)
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Windows에서 콘솔 출력 인코딩 설정
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def test_database_connection():
    """데이터베이스 연결 테스트"""
    try:
        conn = db_manager.get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM policies")
        count = cur.fetchone()[0]
        cur.close()
        print(f"✅ PostgreSQL 연결 성공! 정책 데이터 수: {count}개")
        return True, count
    except Exception as e:
        print(f"❌ PostgreSQL 연결 실패: {str(e)}")
        return False, 0

def test_vector_db():
    """Vector DB 로드 테스트"""
    try:
        db_manager.load_vector_db()
        print("✅ Vector DB 로드 성공!")
        return True
    except Exception as e:
        print(f"❌ Vector DB 로드 실패: {str(e)}")
        print("💡 Vector DB 파일이 없어도 PostgreSQL 검색은 정상 작동합니다.")
        return False

def test_sample_policies():
    """샘플 정책 데이터 확인"""
    try:
        conn = db_manager.get_pg_connection()
        cur = conn.cursor()
        
        # 주거 관련 정책 확인
        cur.execute("""
            SELECT 정책명, 정책키워드명, 정책거주지역코드 
            FROM policies 
            WHERE 정책키워드명 LIKE '%주거%' OR 정책지원내용 LIKE '%주거%'
            LIMIT 3
        """)
        housing_policies = cur.fetchall()
        
        # 취업 관련 정책 확인
        cur.execute("""
            SELECT 정책명, 정책키워드명, 정책거주지역코드 
            FROM policies 
            WHERE 정책키워드명 LIKE '%취업%' OR 정책지원내용 LIKE '%취업%'
            LIMIT 3
        """)
        job_policies = cur.fetchall()
        
        cur.close()
        
        print(f"✅ 주거 관련 정책 샘플 ({len(housing_policies)}개):")
        for policy in housing_policies:
            print(f"  - {policy[0]} ({policy[2]})")
            
        print(f"✅ 취업 관련 정책 샘플 ({len(job_policies)}개):")
        for policy in job_policies:
            print(f"  - {policy[0]} ({policy[2]})")
            
        return True
    except Exception as e:
        print(f"❌ 정책 데이터 확인 실패: {str(e)}")
        return False

def create_sample_user_profiles():
    # todo: 사용자 프로필 생성 방법 찾아보기. 정보 되묻는 에이전트.
    """다양한 샘플 사용자 프로필 생성"""
    profiles = {
        "서울_대학생": {
            "age": 25,
            "income_code": "기타",
            "region": "서울특별시",
            "marital_status": "미혼",
            "job_code": "제한없음",
            "edu_code": "대학 재학",
            "special_code": "제한없음"
        },
        "부산_취업준비생": {
            "age": 28,
            "income_code": "기타",
            "region": "부산광역시",
            "marital_status": "미혼",
            "job_code": "제한없음",
            "edu_code": "제한없음",
            "special_code": "제한없음"
        },
        "경북_청년근로자": {
            "age": 23,
            "income_code": "기타",
            "region": "경상북도",
            "marital_status": "미혼",
            "job_code": "재직자",
            "edu_code": "제한없음",
            "special_code": "제한없음"
        }
    }
    return profiles

def create_test_queries():
    """테스트용 질문들 생성"""
    queries = {
        "주거지원": [
            "25살 대학생인데 주거비 지원받을 수 있는 정책이 있을까요?",
            "서울에 사는 청년을 위한 주거 지원 정책을 알려주세요",
            "월세나 전세 지원하는 청년 정책이 궁금합니다"
        ],
        "취업지원": [
            "취업 준비하는 청년을 위한 지원 정책이 있나요?",
            "면접비나 취업 성공 시 받을 수 있는 수당이 있을까요?",
            "직업 훈련이나 교육 지원 정책을 찾고 있습니다"
        ],
        "지역별": [
            "부산에 사는 청년을 위한 지원 정책이 궁금합니다",
            "경북 지역 청년 취업 지원 정책을 알려주세요",
            "서울 청년 마음건강 지원 사업에 대해 알고 싶어요"
        ]
    }
    return queries

def run_test_scenario(scenario_name, user_profile, query):
    """개별 테스트 시나리오 실행"""
    print(f"\n🔍 테스트 시나리오: {scenario_name}")
    print(f"📋 사용자 정보: {user_profile['region']}, {user_profile['age']}세")
    print(f"❓ 질문: {query}")
    print("-" * 80)
    
    try:
        messages = [HumanMessage(content=query)]
        all_policies = []  # PostgreSQL에서 직접 조회하므로 빈 리스트
        
        result = run_graph(messages, user_profile, all_policies)
        
        print(f"💬 응답:\n{result}")
        print("-" * 80)
        return True
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        print("-" * 80)
        return False

def quick_test():
    """빠른 테스트 (필수 기능만)"""
    print("🚀 빠른 테스트 시작")
    print("=" * 60)
    
    # 데이터베이스 연결 테스트
    db_success, count = test_database_connection()
    if not db_success:
        print("❌ 데이터베이스 연결이 필요합니다.")
        return False
        
    if count == 0:
        print("❌ 정책 데이터가 없습니다. CSV import를 먼저 진행하세요.")
        return False
    
    # 샘플 정책 확인
    test_sample_policies()
    
    # 간단한 시나리오 테스트
    profile = create_sample_user_profiles()["서울_대학생"]
    query = "서울 청년 주거 지원 정책을 알려주세요"
    
    success = run_test_scenario("빠른 테스트", profile, query)
    
    if success:
        print("✅ 빠른 테스트 완료!")
    else:
        print("❌ 빠른 테스트 실패")
        
    return success

def full_test():
    """전체 테스트 실행"""
    print("🚀 전체 테스트 시작")
    print("=" * 80)
    
    # 1. 시스템 확인
    print("\n1️⃣ 시스템 확인")
    db_success, count = test_database_connection()
    vector_success = test_vector_db()
    
    if not db_success:
        print("❌ 데이터베이스가 필요합니다. 테스트를 중단합니다.")
        return
        
    if count == 0:
        print("❌ 정책 데이터가 없습니다. CSV import를 먼저 진행하세요.")
        return
    
    # 2. 샘플 데이터 확인
    print("\n2️⃣ 샘플 데이터 확인")
    test_sample_policies()
    
    # 3. 시나리오 테스트
    print("\n3️⃣ 시나리오 테스트")
    profiles = create_sample_user_profiles()
    queries = create_test_queries()
    
    test_results = []
    
    # 주거 지원 테스트
    print(f"\n{'='*20} 주거 지원 정책 테스트 {'='*20}")
    for i, query in enumerate(queries["주거지원"]):
        profile_name = list(profiles.keys())[i % len(profiles)]
        profile = profiles[profile_name]
        scenario_name = f"주거지원_{profile_name}"
        success = run_test_scenario(scenario_name, profile, query)
        test_results.append((scenario_name, success))
    
    # 취업 지원 테스트
    print(f"\n{'='*20} 취업 지원 정책 테스트 {'='*20}")
    for i, query in enumerate(queries["취업지원"]):
        profile_name = list(profiles.keys())[i % len(profiles)]
        profile = profiles[profile_name]
        scenario_name = f"취업지원_{profile_name}"
        success = run_test_scenario(scenario_name, profile, query)
        test_results.append((scenario_name, success))
    
    # 지역별 테스트
    print(f"\n{'='*20} 지역별 정책 테스트 {'='*20}")
    for i, query in enumerate(queries["지역별"]):
        profile_name = list(profiles.keys())[i % len(profiles)]
        profile = profiles[profile_name]
        scenario_name = f"지역별_{profile_name}"
        success = run_test_scenario(scenario_name, profile, query)
        test_results.append((scenario_name, success))
    
    # 4. 결과 요약
    print("\n4️⃣ 테스트 결과 요약")
    print("=" * 80)
    
    success_count = sum(1 for _, success in test_results if success)
    total_count = len(test_results)
    
    print(f"📊 전체 테스트: {success_count}/{total_count} 성공")
    print(f"📈 성공률: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️  일부 테스트가 실패했습니다. 로그를 확인해주세요.")
        
        print("\n실패한 테스트:")
        for scenario, success in test_results:
            if not success:
                print(f"  ❌ {scenario}")

def debug_rag_pipeline():
    """RAG 파이프라인 디버깅 테스트"""
    print("🔍 RAG 파이프라인 디버깅 시작")
    print("=" * 60)
    
    # 1. 데이터베이스 연결 확인
    print("\n1️⃣ 데이터베이스 연결 확인")
    try:
        conn = db_manager.get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM policies")
        count = cur.fetchone()[0]
        print(f"✅ PostgreSQL 연결 성공! 정책 수: {count}개")
        
        # 샘플 정책 확인
        cur.execute("SELECT 정책명, 정책키워드명, 정책거주지역코드 FROM policies LIMIT 3")
        samples = cur.fetchall()
        print("📋 샘플 정책:")
        for sample in samples:
            print(f"  - {sample[0]} ({sample[2]})")
        cur.close()
    except Exception as e:
        print(f"❌ 데이터베이스 오류: {str(e)}")
        return False
    
    # 2. Vector DB 확인
    print("\n2️⃣ Vector DB 확인")
    try:
        db_manager.load_vector_db()
        print("✅ Vector DB 로드 성공!")
    except Exception as e:
        print(f"⚠️  Vector DB 로드 실패: {str(e)}")
        print("💡 PostgreSQL 검색으로 진행됩니다.")
    
    # 3. 검색 기능 테스트
    print("\n3️⃣ 검색 기능 테스트")
    test_profile = {
        "age": 25,
        "income_code": "기타",
        "region": "서울특별시",
        "marital_status": "미혼",
        "job_code": "제한없음",
        "edu_code": "대학 재학",
        "special_code": "제한없음"
    }
    
    test_query = "서울 청년 주거 지원 정책을 알려주세요"
    print(f"테스트 쿼리: {test_query}")
    print(f"사용자 프로필: {test_profile}")
    
    # 4. 단계별 실행
    print("\n4️⃣ 단계별 실행")
    try:
        from LLM.langgraph_agents import (
            enhanced_intent_classifier_node, 
            housing_agent_node,
            postgres_search_tool,
            context_builder_node,
            llm_node
        )
        from langchain_core.messages import HumanMessage
        
        # 초기 상태 설정
        initial_state = {
            "messages": [HumanMessage(content=test_query)],
            "all_policies": [],
            "filtered_policies": [],
            "user_profile": test_profile,
            "current_intent": "",
            "search_results": [],
            "final_response": "",
            "use_structured_search": False,
            "error": None
        }
        
        # 1단계: 인텐트 분류
        print("  📌 1단계: 인텐트 분류")
        state = enhanced_intent_classifier_node(initial_state)
        print(f"     인텐트: {state['current_intent']}")
        print(f"     구조화된 검색: {state['use_structured_search']}")
        
        # 2단계: PostgreSQL 검색 직접 테스트
        print("  📌 2단계: PostgreSQL 검색")
        state = postgres_search_tool(state)
        print(f"     검색 결과: {len(state['search_results'])}개")
        print(f"     오류: {state.get('error', 'None')}")
        
        if state['search_results']:
            print(f"     첫 번째 결과: {state['search_results'][0].get('정책명', 'N/A')}")
            print(f"     지원내용 미리보기: {state['search_results'][0].get('정책지원내용', 'N/A')[:100]}...")
        
        # 3단계: 컨텍스트 빌더
        print("  📌 3단계: 컨텍스트 빌더")
        state = context_builder_node(state)
        context_length = len(state.get('context', ''))
        print(f"     컨텍스트 길이: {context_length}자")
        if context_length > 0:
            print(f"     컨텍스트 미리보기: {state['context'][:200]}...")
        
        # 4단계: LLM 응답
        print("  📌 4단계: LLM 응답 생성")
        state = llm_node(state)
        response_length = len(state.get('final_response', ''))
        print(f"     응답 길이: {response_length}자")
        if response_length > 0:
            print(f"     응답 미리보기: {state['final_response'][:200]}...")
            print(f"\n🎯 최종 응답:\n{state['final_response']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 파이프라인 실행 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def debug_search_only():
    """검색 기능만 단독 테스트"""
    print("🔍 검색 기능 단독 테스트")
    print("=" * 40)
    
    try:
        conn = db_manager.get_pg_connection()
        cur = conn.cursor()
        
        # 간단한 검색 테스트
        test_queries = [
            "SELECT COUNT(*) FROM policies WHERE 정책키워드명 ILIKE '%주거%'",
            "SELECT COUNT(*) FROM policies WHERE 정책키워드명 ILIKE '%취업%'",
            "SELECT 정책명 FROM policies WHERE 정책키워드명 ILIKE '%주거%' LIMIT 3"
        ]
        
        for query in test_queries:
            print(f"\n쿼리: {query}")
            cur.execute(query)
            result = cur.fetchall()
            print(f"결과: {result}")
        
        cur.close()
        return True
        
    except Exception as e:
        print(f"❌ 검색 테스트 오류: {str(e)}")
        return False

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="청년 정책 검색 시스템 테스트")
    parser.add_argument("--quick", action="store_true", help="빠른 테스트만 실행")
    parser.add_argument("--db-only", action="store_true", help="데이터베이스 연결 테스트만 실행")
    parser.add_argument("--debug", action="store_true", help="RAG 파이프라인 디버깅 실행")
    parser.add_argument("--debug-search", action="store_true", help="검색 기능 단독 테스트")
    
    args = parser.parse_args()
    
    if args.db_only:
        print("🔍 데이터베이스 연결 테스트")
        test_database_connection()
        test_sample_policies()
    elif args.debug:
        debug_rag_pipeline()
    elif args.debug_search:
        debug_search_only()
    elif args.quick:
        quick_test()
    else:
        full_test()

if __name__ == "__main__":
    main() 