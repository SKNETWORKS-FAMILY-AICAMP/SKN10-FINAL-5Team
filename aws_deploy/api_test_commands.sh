#!/bin/bash

# AWS에 배포된 청년 정책 추천 API 테스트 스크립트
API_URL="http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com"

echo "=== AWS 배포 API 테스트 ==="
echo "API URL: $API_URL"
echo ""

# 1. 헬스 체크
echo "1. 헬스 체크"
curl -X GET "$API_URL/health" \
  -H "Content-Type: application/json" \
  | jq '.'
echo ""

# 2. 기본 정보
echo "2. 기본 정보"
curl -X GET "$API_URL/" \
  -H "Content-Type: application/json" \
  | jq '.'
echo ""

# 3. 통계 정보
echo "3. 통계 정보"
curl -X GET "$API_URL/stats" \
  -H "Content-Type: application/json" \
  | jq '.'
echo ""

# 4. 정책 추천 테스트
echo "4. 정책 추천 테스트"
curl -X POST "$API_URL/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "청년을 위한 주거 정책을 추천해주세요",
    "user_profile": {
      "age": 25,
      "income_code": "middle",
      "region": "서울",
      "marital_status": "미혼",
      "job_code": "unemployed",
      "edu_code": "university",
      "special_code": null
    }
  }' \
  | jq '.'
echo ""

# 5. 주거 정책 검색
echo "5. 주거 정책 검색"
curl -X POST "$API_URL/search/housing" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "전세 자금 대출",
    "user_profile": {
      "age": 28,
      "income_code": "low",
      "region": "경기도",
      "marital_status": "미혼",
      "job_code": "employed",
      "edu_code": "university",
      "special_code": null
    }
  }' \
  | jq '.'
echo ""

# 6. 취업 정책 검색
echo "6. 취업 정책 검색"
curl -X POST "$API_URL/search/job" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "취업 지원 프로그램",
    "user_profile": {
      "age": 23,
      "income_code": null,
      "region": "부산",
      "marital_status": "미혼",
      "job_code": "unemployed",
      "edu_code": "highschool",
      "special_code": null
    }
  }' \
  | jq '.'
echo ""

echo "=== 테스트 완료 ===" 