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
csv_path = "/home/bbing/dev/project/SKN10-FINAL-5Team/data/청년정책_전처리완료_v2.csv"
try:
    df_policies = pd.read_csv(csv_path)
    print(f"✅ CSV 데이터 로드 완료: {len(df_policies)}개의 청년정책 데이터")
    print(f"📊 CSV 컬럼: {list(df_policies.columns)}")
except Exception as e:
    print(f"❌ CSV 파일 로드 오류: {e}")
    df_policies = None

# 벡터 DB 로드
db_path = "/home/bbing/dev/project/SKN10-FINAL-5Team/data/vector_db_openai_large_combined"

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
llm = models["GPT-4o"]

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
8. 여러 키워드로 검색할 때는 | (OR) 연산자를 사용하세요

예시:
질문: "일자리 관련 정책이 몇 개인가요?"
코드:
```python
job_related = df_policies[
    df_policies['정책명'].str.contains('일자리', case=False, na=False) |
    df_policies['정책키워드명'].str.contains('일자리', case=False, na=False) |
    df_policies['정책설명내용'].str.contains('일자리', case=False, na=False) |
    df_policies['정책지원내용'].str.contains('일자리', case=False, na=False)
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

데이터 조회 코드:
{generated_code}

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

if __name__ == "__main__":
    # 사용자 질문
    user_question = "주거정책 데이터 중에서 금전적으로 지원하는 정책은 몇개야?"
    
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
    
    # 통계 정보 출력
    vector_count = get_vector_db_count()
    csv_count = get_csv_policy_count()
    
    if vector_count:
        print(f"\n📊 벡터 DB 정보: 총 {vector_count}개의 청년정책 문서가 저장되어 있습니다.")
    
    if csv_count:
        print(f"📊 CSV 데이터 정보: 총 {csv_count}개의 청년정책이 있습니다.")
    
    print("\n" + "="*80)
    print("🔍 지능형 데이터 조회 및 모델별 답변 비교 완료")
    print("="*80)
