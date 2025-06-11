import requests
import json
from datetime import datetime

# API 베이스 URL
BASE_URL = "http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com"

class YouthPolicyAPIClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        
    def health_check(self):
        """헬스 체크"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()
    
    def get_stats(self):
        """통계 정보 조회"""
        response = requests.get(f"{self.base_url}/stats")
        return response.json()
    
    def recommend_policy(self, message, user_profile):
        """정책 추천"""
        payload = {
            "message": message,
            "user_profile": user_profile
        }
        
        response = requests.post(
            f"{self.base_url}/recommend",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API 호출 실패: {response.status_code} - {response.text}")
    
    def search_housing_policies(self, message, user_profile):
        """주거 정책 검색"""
        payload = {
            "message": message,
            "user_profile": user_profile
        }
        
        response = requests.post(
            f"{self.base_url}/search/housing",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API 호출 실패: {response.status_code} - {response.text}")
    
    def search_job_policies(self, message, user_profile):
        """취업 정책 검색"""
        payload = {
            "message": message,
            "user_profile": user_profile
        }
        
        response = requests.post(
            f"{self.base_url}/search/job",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API 호출 실패: {response.status_code} - {response.text}")

# 사용 예시
if __name__ == "__main__":
    client = YouthPolicyAPIClient()
    
    # 헬스 체크
    print("=== 헬스 체크 ===")
    try:
        health = client.health_check()
        print(json.dumps(health, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"헬스 체크 실패: {e}")
    
    # 통계 정보
    print("\n=== 통계 정보 ===")
    try:
        stats = client.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"통계 조회 실패: {e}")
    
    # 정책 추천 테스트
    print("\n=== 정책 추천 테스트 ===")
    user_profile = {
        "age": 25,
        "income_code": "middle",
        "region": "서울",
        "marital_status": "미혼",
        "job_code": "unemployed",
        "edu_code": "university",
        "special_code": None
    }
    
    try:
        result = client.recommend_policy(
            "청년을 위한 주거 정책을 추천해주세요",
            user_profile
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"정책 추천 실패: {e}")
    
    # 주거 정책 검색 테스트
    print("\n=== 주거 정책 검색 테스트 ===")
    try:
        result = client.search_housing_policies(
            "전세 자금 대출",
            user_profile
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"주거 정책 검색 실패: {e}") 