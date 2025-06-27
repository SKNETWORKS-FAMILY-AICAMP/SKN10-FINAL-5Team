"""
평가 결과 수집 및 저장 모듈
"""
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any

from config.evaluation_config import evaluation_config
from utils.logging import setup_logging

logger = setup_logging()


class ResultsCollector:
    """평가 결과를 수집하고 저장하는 클래스"""
    
    def __init__(self):
        self.results_dir = evaluation_config.results_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.collected_results = []
    
    def add_result(self, query_id: int, query: str, model_results: Dict[str, Any], evaluation_results: Dict[str, Any]):
        """
        단일 질문에 대한 결과 추가
        
        Args:
            query_id: 질문 ID
            query: 원본 질문
            model_results: {모델명: (응답, 응답시간, 추가정보)} 형태
            evaluation_results: {모델명: (점수, 이유, 추가정보)} 형태
        """
        for model_name in model_results.keys():
            response, response_time, model_info = model_results[model_name]
            score, reason, eval_info = evaluation_results.get(model_name, (0, "평가 안됨", {}))
            
            result_entry = {
                'query_id': query_id,
                'query': query,
                'model': model_name,
                'response': response,
                'response_time': response_time,
                'quality_score': score,
                'evaluation_reason': reason,
                'success': model_info.get('success', False),
                'selected_policies_count': model_info.get('selected_policies_count', 0),
                'error': model_info.get('error', ''),
                'evaluation_success': eval_info.get('success', False),
                'evaluation_error': eval_info.get('error', '')
            }
            
            self.collected_results.append(result_entry)
            logger.debug(f"결과 추가: Query {query_id}, Model {model_name}, Score {score}")
    
    def save_detailed_results(self) -> str:
        """상세 결과를 CSV 파일로 저장"""
        if not self.collected_results:
            logger.warning("저장할 결과가 없습니다.")
            return ""
        
        # DataFrame 생성
        df = pd.DataFrame(self.collected_results)
        
        # CSV 파일 저장
        csv_filename = f"evaluation_results_{self.timestamp}.csv"
        csv_path = os.path.join(self.results_dir, csv_filename)
        
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"상세 결과 저장 완료: {csv_path}")
        
        return csv_path
    
    def save_summary_report(self) -> str:
        """요약 리포트를 JSON 파일로 저장"""
        if not self.collected_results:
            logger.warning("분석할 결과가 없습니다.")
            return ""
        
        df = pd.DataFrame(self.collected_results)
        
        # 모델별 통계 계산
        model_stats = {}
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            
            model_stats[model] = {
                'total_queries': len(model_data),
                'successful_responses': len(model_data[model_data['success'] == True]),
                'average_response_time': float(model_data['response_time'].mean()),
                'average_quality_score': float(model_data['quality_score'].mean()),
                'quality_score_distribution': {
                    '5점': int((model_data['quality_score'] == 5).sum()),
                    '4점': int((model_data['quality_score'] == 4).sum()),
                    '3점': int((model_data['quality_score'] == 3).sum()),
                    '2점': int((model_data['quality_score'] == 2).sum()),
                    '1점': int((model_data['quality_score'] == 1).sum())
                },
                'error_count': len(model_data[model_data['success'] == False])
            }
        
        # 전체 통계
        overall_stats = {
            'total_queries_evaluated': len(df['query'].unique()),
            'total_model_responses': len(df),
            'evaluation_timestamp': self.timestamp,
            'average_scores_by_model': {
                model: float(df[df['model'] == model]['quality_score'].mean())
                for model in df['model'].unique()
            },
            'average_response_times_by_model': {
                model: float(df[df['model'] == model]['response_time'].mean())
                for model in df['model'].unique()
            }
        }
        
        # 리포트 구성
        summary_report = {
            'evaluation_metadata': {
                'timestamp': self.timestamp,
                'evaluated_models': list(df['model'].unique()),
                'total_queries': len(df['query'].unique())
            },
            'overall_statistics': overall_stats,
            'model_statistics': model_stats,
            'top_performing_models': {
                'by_quality': self._get_top_models_by_quality(df),
                'by_speed': self._get_top_models_by_speed(df)
            }
        }
        
        # JSON 파일 저장
        json_filename = f"model_comparison_report_{self.timestamp}.json"
        json_path = os.path.join(self.results_dir, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"요약 리포트 저장 완료: {json_path}")
        
        return json_path
    
    def save_markdown_summary(self) -> str:
        """마크다운 형태의 요약 보고서 생성"""
        if not self.collected_results:
            return ""
        
        df = pd.DataFrame(self.collected_results)
        
        markdown_content = f"""# 청년정책 RAG 시스템 평가 보고서

## 평가 개요
- **평가 일시**: {datetime.now().strftime("%Y년 %m월 %d일 %H:%M:%S")}
- **평가 대상 모델**: {', '.join(df['model'].unique())}
- **총 질문 수**: {len(df['query'].unique())}
- **총 응답 수**: {len(df)}

## 모델별 성능 요약

"""
        
        # 모델별 통계 테이블
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            
            markdown_content += f"""### {model}
- **평균 응답 시간**: {model_data['response_time'].mean():.2f}초
- **평균 품질 점수**: {model_data['quality_score'].mean():.2f}/5.0
- **성공률**: {(model_data['success'].sum() / len(model_data) * 100):.1f}%

"""
        
        # 품질 점수 분포
        markdown_content += """## 품질 점수 분포

| 모델 | 5점 | 4점 | 3점 | 2점 | 1점 | 평균 |
|------|-----|-----|-----|-----|-----|------|
"""
        
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            scores = [
                (model_data['quality_score'] == i).sum() for i in range(5, 0, -1)
            ]
            avg_score = model_data['quality_score'].mean()
            
            markdown_content += f"| {model} | {scores[0]} | {scores[1]} | {scores[2]} | {scores[3]} | {scores[4]} | {avg_score:.2f} |\n"
        
        # 응답 시간 비교
        markdown_content += """
## 응답 시간 비교

| 모델 | 평균 응답 시간 | 최소 시간 | 최대 시간 |
|------|---------------|----------|----------|
"""
        
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            avg_time = model_data['response_time'].mean()
            min_time = model_data['response_time'].min()
            max_time = model_data['response_time'].max()
            
            markdown_content += f"| {model} | {avg_time:.2f}초 | {min_time:.2f}초 | {max_time:.2f}초 |\n"
        
        markdown_content += f"""
## 결론 및 추천

{self._generate_recommendations(df)}

---
*이 보고서는 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}에 자동 생성되었습니다.*
"""
        
        # 마크다운 파일 저장
        md_filename = f"evaluation_summary_{self.timestamp}.md"
        md_path = os.path.join(self.results_dir, md_filename)
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"마크다운 요약 저장 완료: {md_path}")
        
        return md_path
    
    def _get_top_models_by_quality(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """품질 점수 기준으로 모델 순위 반환"""
        quality_ranking = df.groupby('model')['quality_score'].mean().sort_values(ascending=False)
        
        return [
            {
                'model': model,
                'average_quality_score': float(score)
            }
            for model, score in quality_ranking.items()
        ]
    
    def _get_top_models_by_speed(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """응답 속도 기준으로 모델 순위 반환 (빠른 순)"""
        speed_ranking = df.groupby('model')['response_time'].mean().sort_values(ascending=True)
        
        return [
            {
                'model': model,
                'average_response_time': float(time)
            }
            for model, time in speed_ranking.items()
        ]
    
    def _generate_recommendations(self, df: pd.DataFrame) -> str:
        """분석 결과를 바탕으로 추천사항 생성"""
        quality_best = df.groupby('model')['quality_score'].mean().idxmax()
        speed_best = df.groupby('model')['response_time'].mean().idxmin()
        
        recommendations = f"""
### 추천사항

1. **최고 품질**: {quality_best} 모델이 가장 높은 품질 점수를 기록했습니다.
2. **최고 속도**: {speed_best} 모델이 가장 빠른 응답 시간을 보였습니다.

### 사용 시나리오별 추천
- **품질 우선**: 정확한 답변이 중요한 경우 → {quality_best}
- **속도 우선**: 빠른 응답이 중요한 경우 → {speed_best}
"""
        
        return recommendations
