import os
import pandas as pd
import json
import ast
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 환경변수 로드
load_dotenv()

# CSV 데이터 로드
#csv_path = "/home/bbing/dev/project/SKN10-FINAL-5Team/data/청년정책_전처리완료_v2.csv"
csv_path = "C:/dev/project/SKN10-FINAL-5Team/data/청년정책목록_전처리완료_2025-06-09.csv"
try:
    df_policies = pd.read_csv(csv_path)
    print(f"✅ CSV 데이터 로드 완료: {len(df_policies)}개의 청년정책 데이터")
    print(f"📊 CSV 컬럼: {list(df_policies.columns)}")
except Exception as e:
    print(f"❌ CSV 파일 로드 오류: {e}")
    df_policies = None

# 벡터 DB 로드
#db_path = "/home/bbing/dev/project/SKN10-FINAL-5Team/data/vector_db_openai_large_combined"
db_path = "C:/dev/project/SKN10-FINAL-5Team/data/vector_db_openai_large_combined"

embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
vector_db = FAISS.load_local(
    folder_path=db_path,
    embeddings=embedding_model,
    allow_dangerous_deserialization=True
)

# 여러 LLM 모델 초기화
models = {
    "GPT-3.5-turbo": ChatOpenAI(model="gpt-3.5-turbo", temperature=0),
    "GPT-4": ChatOpenAI(model="gpt-4", temperature=0),
    "GPT-4-turbo": ChatOpenAI(model="gpt-4-turbo", temperature=0),
    "GPT-4o": ChatOpenAI(model="gpt-4o", temperature=0),
    "GPT-4o-mini": ChatOpenAI(model="gpt-4o-mini", temperature=0)
}

# 기본 LLM (하위 호환성을 위해)
llm = models["GPT-4o-mini"]

# 시스템 프롬프트 정의
system_prompt = (
    "당신은 한국의 청년 정책에 대한 질문-답변 도우미입니다. "
    "검색된 다음 정보들을 사용하여 질문에 답변하세요. "
    "답을 모르면 모른다고 말하세요. "
    "\n\n"
    "{context}"
)

# 프롬프트 템플릿 생성
qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

# 리트리버 생성 (더 많은 문서 검색을 위해 k 값 증가)
retriever = vector_db.as_retriever(search_kwargs={"k": 5})

# 문서 결합 체인 생성
question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

# 최종 RAG 체인 생성 (최신 API 사용)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

def get_vector_db_count():
    """벡터 DB에 저장된 문서의 총 개수를 반환합니다."""
    try:
        # FAISS 인덱스의 벡터 개수 조회
        total_vectors = vector_db.index.ntotal
        return total_vectors
    except Exception as e:
        print(f"벡터 DB 개수 조회 중 오류 발생: {e}")
        return None

def get_csv_policy_count():
    """CSV 파일의 정책 개수를 반환합니다."""
    if df_policies is not None:
        return len(df_policies)
    return None

def search_policies_by_keyword(keyword):
    """CSV 데이터에서 키워드로 정책을 검색합니다."""
    if df_policies is None:
        return []
    
    # 여러 컬럼에서 키워드 검색
    search_columns = ['정책명', '정책키워드명', '정책설명내용', '정책대분류명', '정책중분류명', '정책지원내용']
    
    mask = pd.Series([False] * len(df_policies))
    for col in search_columns:
        if col in df_policies.columns:
            mask |= df_policies[col].astype(str).str.contains(keyword, case=False, na=False)
    
    filtered_policies = df_policies[mask]
    return filtered_policies

def get_policy_statistics():
    """정책 통계 정보를 반환합니다."""
    if df_policies is None:
        return {}
    
    stats = {
        "총_정책수": len(df_policies),
        "대분류별_통계": df_policies['정책대분류명'].value_counts().to_dict() if '정책대분류명' in df_policies.columns else {},
        "중분류별_통계": df_policies['정책중분류명'].value_counts().to_dict() if '정책중분류명' in df_policies.columns else {},
        "연령대별_통계": {
            "최소연령_평균": df_policies['지원대상최소연령'].mean() if '지원대상최소연령' in df_policies.columns else None,
            "최대연령_평균": df_policies['지원대상최대연령'].mean() if '지원대상최대연령' in df_policies.columns else None
        }
    }
    return stats

def execute_data_query_code(code_string):
    """생성된 데이터 조회 코드를 안전하게 실행합니다."""
    try:
        # 허용된 함수와 변수 정의
        safe_globals = {
            'df_policies': df_policies,
            'pd': pd,
            'len': len,
            'sum': sum,
            'max': max,
            'min': min,
            'list': list,
            'dict': dict,
            'str': str,
            'int': int,
            'float': float,
        }
        
        # 안전한 로컬 변수 공간
        safe_locals = {}
        
        # 코드 실행
        exec(code_string, safe_globals, safe_locals)
        
        # 결과 반환 (result 변수를 찾아서 반환)
        if 'result' in safe_locals:
            return safe_locals['result']
        else:
            return "코드 실행 완료, 하지만 result 변수를 찾을 수 없습니다."
            
    except Exception as e:
        return f"코드 실행 오류: {str(e)}"

def generate_data_query_code(user_question):
    """사용자 질문을 분석하여 데이터 조회 코드를 생성합니다."""
    
    # 데이터 구조 정보 생성
    data_info = ""
    if df_policies is not None:
        data_info = f"""
데이터프레임 정보:
- 변수명: df_policies
- 총 행 수: {len(df_policies)}
- 컬럼 목록: {list(df_policies.columns)}
- 주요 컬럼 설명:
  * 정책명: 정책의 이름
  * 정책키워드명: 정책 관련 키워드
  * 정책대분류명: 정책의 대분류 (예: 복지문화, 생활지원 등)
  * 정책중분류명: 정책의 중분류
  * 정책설명내용: 정책에 대한 상세 설명
  * 정책지원내용: 정책이 제공하는 지원 내용
  * 지원대상최소연령, 지원대상최대연령: 지원 대상 연령
  * 주관기관코드명, 운영기관코드명: 관련 기관 정보
"""
    
    code_generation_prompt = f"""
당신은 데이터 분석 전문가입니다. 사용자의 질문을 분석하여 pandas를 사용한 데이터 조회 코드를 생성해주세요.

{data_info}

사용자 질문: "{user_question}"

다음 규칙을 따라 코드를 생성하세요:
1. 결과는 반드시 'result' 변수에 저장하세요
2. pandas 함수만 사용하세요 (df_policies.method() 형태)
3. 검색할 때는 .str.contains()를 사용하고 case=False, na=False 옵션을 포함하세요
4. 개수를 구할 때는 len() 함수를 사용하세요
5. 통계를 구할 때는 .value_counts(), .mean(), .sum() 등을 사용하세요
6. 코드는 실행 가능한 Python 코드여야 합니다
7. import 문은 사용하지 마세요

예시:
질문: "일자리 관련 정책이 몇 개인가요?"
코드:
```python
job_related = df_policies[
    df_policies['정책명'].str.contains('일자리', case=False, na=False) |
    df_policies['정책키워드명'].str.contains('일자리', case=False, na=False) |
    df_policies['정책설명내용'].str.contains('일자리', case=False, na=False)
]
result = len(job_related)
```

코드만 생성하고 다른 설명은 하지 마세요:
"""

    try:
        # 코드 생성을 위한 LLM 호출
        code_llm = ChatOpenAI(model="gpt-4o", temperature=0)
        response = code_llm.invoke(code_generation_prompt)
        
        # 응답에서 코드 부분 추출
        code_content = response.content
        
        # 코드 블록에서 코드 추출
        if "```python" in code_content:
            code_start = code_content.find("```python") + 9
            code_end = code_content.find("```", code_start)
            if code_end != -1:
                code = code_content[code_start:code_end].strip()
            else:
                code = code_content[code_start:].strip()
        elif "```" in code_content:
            code_start = code_content.find("```") + 3
            code_end = code_content.find("```", code_start)
            if code_end != -1:
                code = code_content[code_start:code_end].strip()
            else:
                code = code_content[code_start:].strip()
        else:
            code = code_content.strip()
        
        return code
        
    except Exception as e:
        return f"# 코드 생성 오류: {str(e)}\nresult = '코드 생성에 실패했습니다.'"

def answer_with_db_info(user_question):
    """사용자 질문에 DB 정보를 포함해서 답변합니다."""
    
    # 청년정책 개수 관련 질문인지 확인
    count_keywords = ["개수", "갯수", "총", "전체", "몇 개", "몇개", "수량"]
    policy_keywords = ["청년정책", "정책", "청년"]
    
    is_count_question = any(keyword in user_question for keyword in count_keywords)
    is_policy_question = any(keyword in user_question for keyword in policy_keywords)
    
    if is_count_question and is_policy_question:
        # 벡터 DB의 실제 문서 개수 조회
        total_count = get_vector_db_count()
        
        if total_count is not None:
            # 개수 정보를 포함한 시스템 프롬프트 생성
            enhanced_system_prompt = (
                f"당신은 한국의 청년 정책에 대한 질문-답변 도우미입니다. "
                f"현재 벡터 데이터베이스에는 총 {total_count}개의 청년정책 문서가 저장되어 있습니다. "
                f"검색된 다음 정보들을 사용하여 질문에 답변하세요. "
                f"청년정책의 개수에 대한 질문이면 '{total_count}개'라고 정확히 답변하세요. "
                f"답을 모르면 모른다고 말하세요. "
                f"\n\n"
                f"{{context}}"
            )
            
            # 새로운 프롬프트 템플릿 생성
            enhanced_qa_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", enhanced_system_prompt),
                    ("human", "{input}"),
                ]
            )
            
            # 새로운 체인 생성
            enhanced_question_answer_chain = create_stuff_documents_chain(llm, enhanced_qa_prompt)
            enhanced_rag_chain = create_retrieval_chain(retriever, enhanced_question_answer_chain)
            
            # 질의 응답 수행
            result = enhanced_rag_chain.invoke({"input": user_question})
            
            return result
    
    # 일반적인 질문의 경우 기존 체인 사용
    result = rag_chain.invoke({"input": user_question})
    return result

def answer_with_intelligent_data_query(user_question):
    """사용자 질문을 분석하여 데이터 조회 코드를 생성하고 실행한 후 답변합니다."""
    
    print(f"\n🔍 질문 분석 중: {user_question}")
    
    # 1단계: 데이터 조회 코드 생성
    print("📝 1단계: 데이터 조회 코드 생성 중...")
    generated_code = generate_data_query_code(user_question)
    print(f"생성된 코드:\n{generated_code}")
    
    # 2단계: 생성된 코드 실행
    print("\n⚡ 2단계: 코드 실행 중...")
    query_result = execute_data_query_code(generated_code)
    print(f"쿼리 결과: {query_result}")
    
    # 3단계: 결과를 바탕으로 최종 답변 생성
    print("\n🤖 3단계: 최종 답변 생성 중...")
    
    final_answer_prompt = f"""
당신은 한국의 청년 정책에 대한 질문-답변 도우미입니다.

사용자 질문: "{user_question}"

데이터 조회 결과: {query_result}

위의 데이터 조회 결과를 바탕으로 사용자의 질문에 대해 정확하고 친절한 답변을 제공해주세요.
숫자 데이터가 있다면 구체적으로 언급하고, 추가적인 인사이트나 해석도 포함해주세요.
"""

    try:
        answer_llm = ChatOpenAI(model="gpt-4o", temperature=0)
        final_response = answer_llm.invoke(final_answer_prompt)
        return {
            'generated_code': generated_code,
            'query_result': query_result,
            'final_answer': final_response.content
        }
    except Exception as e:
        return {
            'generated_code': generated_code,
            'query_result': query_result,
            'final_answer': f"답변 생성 중 오류가 발생했습니다: {str(e)}"
        }

def answer_with_multiple_models_intelligent(user_question):
    """여러 GPT 모델로 지능형 데이터 조회를 수행합니다."""
    
    print(f"\n🧠 지능형 데이터 조회 시작")
    print("="*80)
    
    # 공통 데이터 조회 수행
    intelligent_result = answer_with_intelligent_data_query(user_question)
    
    print("\n" + "="*80)
    print("🤖 여러 모델로 최종 답변 생성")
    print("="*80)
    
    results = {}
    
    # 각 모델별로 최종 답변만 생성 (동일한 데이터 조회 결과 사용)
    final_answer_prompt = f"""
당신은 한국의 청년 정책에 대한 질문-답변 도우미입니다.

사용자 질문: "{user_question}"

데이터 조회 코드:
{intelligent_result['generated_code']}

데이터 조회 결과: {intelligent_result['query_result']}

위의 데이터 조회 결과를 바탕으로 사용자의 질문에 대해 정확하고 친절한 답변을 제공해주세요.
숫자 데이터가 있다면 구체적으로 언급하고, 추가적인 인사이트나 해석도 포함해주세요.
"""

    for model_name, llm_model in models.items():
        print(f"\n🔄 {model_name} 모델로 답변 생성 중...")
        
        try:
            response = llm_model.invoke(final_answer_prompt)
            results[model_name] = response.content
        except Exception as e:
            results[model_name] = f"❌ 오류 발생: {str(e)}"
    
    # 지능형 조회 결과도 포함
    results['intelligent_query'] = intelligent_result
    
    return results
    """여러 GPT 모델로 동일한 질문에 답변합니다."""
    
    # 청년정책 개수 관련 질문인지 확인
    count_keywords = ["개수", "갯수", "총", "전체", "몇 개", "몇개", "수량"]
    policy_keywords = ["청년정책", "정책", "청년"]
    job_keywords = ["일자리", "취업", "고용", "직업", "직장"]
    
    is_count_question = any(keyword in user_question for keyword in count_keywords)
    is_policy_question = any(keyword in user_question for keyword in policy_keywords)
    is_job_question = any(keyword in user_question for keyword in job_keywords)
    
    # CSV 데이터 기반 정보 수집
    csv_info = ""
    if df_policies is not None:
        csv_count = get_csv_policy_count()
        stats = get_policy_statistics()
        
        if is_count_question and is_policy_question:
            csv_info = f"CSV 데이터에 따르면 총 {csv_count}개의 청년정책이 있습니다.\n"
            
            if is_job_question:
                # 일자리 관련 정책 검색
                job_policies = search_policies_by_keyword("일자리")
                employment_policies = search_policies_by_keyword("취업")
                work_policies = search_policies_by_keyword("고용")
                
                job_count = len(job_policies) + len(employment_policies) + len(work_policies)
                job_count = len(pd.concat([job_policies, employment_policies, work_policies]).drop_duplicates())
                
                csv_info += f"이 중 일자리/취업/고용 관련 정책은 약 {job_count}개입니다.\n"
            
            if stats.get("대분류별_통계"):
                csv_info += f"대분류별 통계: {stats['대분류별_통계']}\n"
    
    results = {}
    
    for model_name, llm_model in models.items():
        print(f"\n🔄 {model_name} 모델로 답변 생성 중...")
        
        try:
            if is_count_question and is_policy_question:
                # 개수 질문의 경우 DB 정보와 CSV 정보 포함
                vector_count = get_vector_db_count()
                csv_count = get_csv_policy_count()
                
                enhanced_system_prompt = (
                    f"당신은 한국의 청년 정책에 대한 질문-답변 도우미입니다. "
                    f"다음 정보를 참고하여 질문에 답변하세요:\n"
                    f"- 벡터 데이터베이스: {vector_count}개의 문서\n"
                    f"- CSV 데이터: {csv_count}개의 정책\n"
                    f"{csv_info}"
                    f"검색된 다음 정보들을 사용하여 질문에 답변하세요. "
                    f"정확한 수치가 있다면 그것을 우선 사용하세요. "
                    f"답을 모르면 모른다고 말하세요. "
                    f"\n\n"
                    f"{{context}}"
                )
                
                qa_prompt_model = ChatPromptTemplate.from_messages(
                    [
                        ("system", enhanced_system_prompt),
                        ("human", "{input}"),
                    ]
                )
            else:
                # 일반 질문의 경우 기본 프롬프트에 CSV 정보 추가
                enhanced_system_prompt = (
                    f"당신은 한국의 청년 정책에 대한 질문-답변 도우미입니다. "
                    f"현재 {get_csv_policy_count()}개의 청년정책 데이터를 보유하고 있습니다. "
                    f"검색된 다음 정보들을 사용하여 질문에 답변하세요. "
                    f"답을 모르면 모른다고 말하세요. "
                    f"\n\n"
                    f"{{context}}"
                )
                
                qa_prompt_model = ChatPromptTemplate.from_messages(
                    [
                        ("system", enhanced_system_prompt),
                        ("human", "{input}"),
                    ]
                )
            
            # 각 모델별 체인 생성
            question_answer_chain_model = create_stuff_documents_chain(llm_model, qa_prompt_model)
            rag_chain_model = create_retrieval_chain(retriever, question_answer_chain_model)
            
            # 질의 응답 수행
            result = rag_chain_model.invoke({"input": user_question})
            results[model_name] = result['answer']
            
        except Exception as e:
            results[model_name] = f"❌ 오류 발생: {str(e)}"
    
    return results

# 사용자 질문
#user_question = "청년정책에서 일자리 정책 데이터 갯수를 말해줘"
user_question = input("🧑 사용자 질문을 입력하세요: ")

# 지능형 데이터 조회 및 여러 모델 답변 수행
print("🧑 사용자 질문:")
print(user_question)

# 지능형 쿼리 시스템 사용
multi_results = answer_with_multiple_models_intelligent(user_question)

# 지능형 조회 결과 출력
if 'intelligent_query' in multi_results:
    intelligent_result = multi_results['intelligent_query']
    print(f"\n📝 생성된 데이터 조회 코드:")
    print("-" * 50)
    print(intelligent_result['generated_code'])
    print("-" * 50)
    print(f"\n📊 쿼리 실행 결과: {intelligent_result['query_result']}")

print("\n" + "="*80)
print("🤖 각 모델별 최종 답변:")
print("="*80)

# 각 모델별 답변 출력 (intelligent_query 제외)
for model_name, answer in multi_results.items():
    if model_name != 'intelligent_query':
        print(f"\n🤖 [{model_name}] 답변:")
        print("-" * 50)
        print(answer)
        print("-" * 50)

# 벡터 DB 정보 출력 (디버깅용)
vector_count = get_vector_db_count()
csv_count = get_csv_policy_count()

if vector_count:
    print(f"\n📊 벡터 DB 정보: 총 {vector_count}개의 청년정책 문서가 저장되어 있습니다.")

if csv_count:
    print(f"📊 CSV 데이터 정보: 총 {csv_count}개의 청년정책이 있습니다.")
    
    # 정책 통계 정보 출력
    stats = get_policy_statistics()
    if stats.get("대분류별_통계"):
        print(f"📊 대분류별 정책 수:")
        for category, count in list(stats["대분류별_통계"].items())[:5]:  # 상위 5개만 출력
            print(f"   - {category}: {count}개")

print("\n" + "="*80)
print("🔍 지능형 데이터 조회 및 모델별 답변 비교 완료")
print("="*80)


