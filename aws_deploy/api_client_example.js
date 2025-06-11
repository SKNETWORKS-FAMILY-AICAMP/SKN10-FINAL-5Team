const axios = require('axios');

// API 베이스 URL
const BASE_URL = 'http://youth-policy-api-alb-2064094151.ap-northeast-2.elb.amazonaws.com';

class YouthPolicyAPIClient {
  constructor(baseUrl = BASE_URL) {
    this.baseUrl = baseUrl;
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  async healthCheck() {
    try {
      const response = await this.client.get('/health');
      return response.data;
    } catch (error) {
      throw new Error(`헬스 체크 실패: ${error.message}`);
    }
  }

  async getStats() {
    try {
      const response = await this.client.get('/stats');
      return response.data;
    } catch (error) {
      throw new Error(`통계 조회 실패: ${error.message}`);
    }
  }

  async recommendPolicy(message, userProfile) {
    try {
      const response = await this.client.post('/recommend', {
        message,
        user_profile: userProfile
      });
      return response.data;
    } catch (error) {
      throw new Error(`정책 추천 실패: ${error.message}`);
    }
  }

  async searchHousingPolicies(message, userProfile) {
    try {
      const response = await this.client.post('/search/housing', {
        message,
        user_profile: userProfile
      });
      return response.data;
    } catch (error) {
      throw new Error(`주거 정책 검색 실패: ${error.message}`);
    }
  }

  async searchJobPolicies(message, userProfile) {
    try {
      const response = await this.client.post('/search/job', {
        message,
        user_profile: userProfile
      });
      return response.data;
    } catch (error) {
      throw new Error(`취업 정책 검색 실패: ${error.message}`);
    }
  }
}

// 사용 예시
async function main() {
  const client = new YouthPolicyAPIClient();

  // 헬스 체크
  console.log('=== 헬스 체크 ===');
  try {
    const health = await client.healthCheck();
    console.log(JSON.stringify(health, null, 2));
  } catch (error) {
    console.error(error.message);
  }

  // 통계 정보
  console.log('\n=== 통계 정보 ===');
  try {
    const stats = await client.getStats();
    console.log(JSON.stringify(stats, null, 2));
  } catch (error) {
    console.error(error.message);
  }

  // 정책 추천 테스트
  console.log('\n=== 정책 추천 테스트 ===');
  const userProfile = {
    age: 25,
    income_code: 'middle',
    region: '서울',
    marital_status: '미혼',
    job_code: 'unemployed',
    edu_code: 'university',
    special_code: null
  };

  try {
    const result = await client.recommendPolicy(
      '청년을 위한 주거 정책을 추천해주세요',
      userProfile
    );
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    console.error(error.message);
  }

  // 주거 정책 검색 테스트
  console.log('\n=== 주거 정책 검색 테스트 ===');
  try {
    const result = await client.searchHousingPolicies(
      '전세 자금 대출',
      userProfile
    );
    console.log(JSON.stringify(result, null, 2));
  } catch (error) {
    console.error(error.message);
  }
}

// 실행
if (require.main === module) {
  main().catch(console.error);
}

module.exports = YouthPolicyAPIClient; 