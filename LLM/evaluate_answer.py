import pandas as pd
import os
from openai import OpenAI
import time
from typing import Dict, List
import json

class AnswerEvaluator:
    def __init__(self, api_key: str = None):
        """
        답변 평가기 초기화
        
        Args:
            api_key: OpenAI API 키. None이면 환경변수에서 가져옴
        """
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = OpenAI()  # 환경변수 OPENAI_API_KEY 사용
    
    def create_evaluation_prompt(self, query: str, answer: str) -> str:
        """
        평가용 프롬프트 생성
        
        Args:
            query: 사용자 질문
            answer: RAG 시스템의 답변
            
        Returns:
            평가용 프롬프트
        """
        prompt = f"""
당신은 청년정책 관련 질의응답 시스템의 답변을 평가하는 전문가입니다.

다음 기준으로 답변을 10점 만점으로 평가해주세요:

**평가 기준:**
1. **정확성 (2점)**: 답변이 질문에 정확하게 대답하는가?
2. **완성도 (1점)**: 답변이 충분히 상세하고 도움이 되는가?
3. **관련성 (1점)**: 답변이 질문과 관련이 있는가?
4. **실용성 (1점)**: 답변이 실제로 도움이 되는 정보를 제공하는가?

**질문:** {query}

**답변:** {answer}

위 답변을 평가하여 1-10점 사이의 점수를 매기고, 점수만 숫자로 답해주세요.
예시: 7
"""
        return prompt
    
    def evaluate_single_answer(self, query: str, answer: str, max_retries: int = 3) -> int:
        """
        단일 답변 평가
        
        Args:
            query: 사용자 질문
            answer: RAG 시스템의 답변
            max_retries: 최대 재시도 횟수
            
        Returns:
            평가 점수 (1-5)
        """
        for attempt in range(max_retries):
            try:
                prompt = self.create_evaluation_prompt(query, answer)
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=10,
                    temperature=0.1
                )
                
                # 응답에서 숫자 추출
                score_text = response.choices[0].message.content.strip()
                
                # 점수 파싱
                try:
                    score = int(score_text)
                    if 1 <= score <= 10:
                        return score
                    else:
                        print(f"점수가 범위를 벗어남: {score}, 기본값 5 반환")
                        return 5
                except ValueError:
                    print(f"점수 파싱 실패: {score_text}, 기본값 5 반환")
                    return 5
                    
            except Exception as e:
                print(f"평가 중 오류 발생 (시도 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"{5 * (attempt + 1)}초 후 재시도...")
                    time.sleep(5 * (attempt + 1))  # 지수적 백오프
                else:
                    print("최대 재시도 횟수 초과, 기본값 5 반환")
                    return 5  # 기본값
    
    def evaluate_csv_file(self, csv_path: str, output_path: str = None, delay: float = 1.0):
        """
        CSV 파일의 모든 답변을 평가
        
        Args:
            csv_path: 입력 CSV 파일 경로
            output_path: 출력 CSV 파일 경로 (None이면 원본 파일 덮어쓰기)
            delay: API 호출 간 지연 시간 (초)
        """
        # CSV 파일 읽기
        df = pd.read_csv(csv_path)
        print(f"총 {len(df)}개의 행을 처리합니다.")
        
        # o3_naive_evaluation, o3_advanced_evaluation 컬럼이 없으면 생성
        if 'o3_naive_evaluation' not in df.columns:
            df['o3_naive_evaluation'] = None
        if 'o3_advanced_evaluation' not in df.columns:
            df['o3_advanced_evaluation'] = None
        
        # 각 행에 대해 평가 수행
        for idx, row in df.iterrows():
            print(f"행 {idx + 1}/{len(df)} 처리 중...")
            
            query = row['query']
            naive_answer = row['naive_rag_answer']
            advanced_answer = row['advanced_rag_answer']
            
            # Naive RAG 답변 평가 (항상 수행)
            print(f"  - Naive RAG 답변 평가 중...")
            naive_score = self.evaluate_single_answer(query, naive_answer)
            df.at[idx, 'o3_naive_evaluation'] = naive_score
            print(f"  - Naive RAG 점수: {naive_score}")
            time.sleep(delay)
            
            # Advanced RAG 답변 평가 (항상 수행)
            print(f"  - Advanced RAG 답변 평가 중...")
            advanced_score = self.evaluate_single_answer(query, advanced_answer)
            df.at[idx, 'o3_advanced_evaluation'] = advanced_score
            print(f"  - Advanced RAG 점수: {advanced_score}")
            time.sleep(delay)
            
            # 중간 저장 (10개마다)
            if (idx + 1) % 10 == 0:
                output_file = output_path if output_path else csv_path
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                print(f"중간 저장 완료: {idx + 1}개 처리됨")
        
        # 최종 저장
        output_file = output_path if output_path else csv_path
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"평가 완료! 결과가 {output_file}에 저장되었습니다.")
        
        return df
    
    def print_evaluation_summary(self, df: pd.DataFrame):
        """
        평가 결과 요약 출력
        
        Args:
            df: 평가가 완료된 DataFrame
        """
        print("\n" + "="*50)
        print("평가 결과 요약")
        print("="*50)
        
        # 평가 점수가 있는 행만 필터링
        evaluated_df = df[df['o3_naive_evaluation'].notna() & df['o3_advanced_evaluation'].notna()]
        
        if len(evaluated_df) == 0:
            print("평가된 데이터가 없습니다.")
            return
        
        naive_scores = evaluated_df['o3_naive_evaluation'].astype(int)
        advanced_scores = evaluated_df['o3_advanced_evaluation'].astype(int)
        
        print(f"평가된 질문 수: {len(evaluated_df)}")
        print(f"\nNaive RAG 평균 점수: {naive_scores.mean():.2f}")
        print(f"Advanced RAG 평균 점수: {advanced_scores.mean():.2f}")
        
        print(f"\nNaive RAG 점수 분포:")
        for score in range(1, 11):
            count = (naive_scores == score).sum()
            print(f"  {score}점: {count}개 ({count/len(naive_scores)*100:.1f}%)")
        
        print(f"\nAdvanced RAG 점수 분포:")
        for score in range(1, 11):
            count = (advanced_scores == score).sum()
            print(f"  {score}점: {count}개 ({count/len(advanced_scores)*100:.1f}%)")
        
        # Advanced가 더 좋은 경우
        better_advanced = (advanced_scores > naive_scores).sum()
        better_naive = (naive_scores > advanced_scores).sum()
        same_score = (naive_scores == advanced_scores).sum()
        
        print(f"\n성능 비교:")
        print(f"  Advanced RAG가 더 좋음: {better_advanced}개 ({better_advanced/len(evaluated_df)*100:.1f}%)")
        print(f"  Naive RAG가 더 좋음: {better_naive}개 ({better_naive/len(evaluated_df)*100:.1f}%)")
        print(f"  동일한 점수: {same_score}개 ({same_score/len(evaluated_df)*100:.1f}%)")


def main():
    """
    메인 실행 함수
    """
    # 파일 경로 설정
    csv_path = r"c:\dev\SKN10-FINAL-5Team\data\query_testset.csv"
    
    # 평가기 초기화
    evaluator = AnswerEvaluator()
    
    try:
        # CSV 파일 평가
        print("답변 평가를 시작합니다...")
        df = evaluator.evaluate_csv_file(csv_path, delay=1.0)
        
        # 결과 요약 출력
        evaluator.print_evaluation_summary(df)
        
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {csv_path}")
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    main()