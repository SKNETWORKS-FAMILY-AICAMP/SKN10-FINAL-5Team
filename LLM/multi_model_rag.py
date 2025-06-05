import os
import time
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

# 환경변수 로드
load_dotenv()

# 벡터 DB 로드
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "vector_db_openai_large_combined")

# 벡터 DB 경로 확인
if not os.path.exists(db_path):
    raise FileNotFoundError(f"Vector DB path does not exist: {db_path}")

embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")
vector_db = FAISS.load_local(
    folder_path=db_path,
    embeddings=embedding_model,
    allow_dangerous_deserialization=True
)

# 시스템 프롬프트 정의
system_prompt = (
    "당신은 한국의 청년 정책에 대한 질문-답변 도우미입니다. "
    "검색된 다음 정보들을 사용하여 질문에 답변하세요. "
    "답을 모르면 모른다고 말하세요. "
    "\n\n"
    "{context}"
)

# 프롬프트 템플릿 생성
qa_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

# 리트리버 생성
retriever = vector_db.as_retriever(search_kwargs={"k": 5})

# 문서 결합 체인 생성
def create_rag_chain(llm):
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    return create_retrieval_chain(retriever, question_answer_chain)

# 모델 초기화 함수
def initialize_models():
    models = {
        "ChatGPT 4.5": ChatOpenAI(model="gpt-4-0125-preview", temperature=0),
        "ChatGPT o4-mini": ChatOpenAI(model="gpt-4-1106-preview", temperature=0),
        "ChatGPT 4o": ChatOpenAI(model="gpt-4", temperature=0),
        "ChatGPT o3-mini": ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    }
    return models

def get_model_response(model_name, llm, question):
    try:
        start_time = time.time()
        rag_chain = create_rag_chain(llm)
        result = rag_chain.invoke({"input": question})
        end_time = time.time()
        
        return {
            "model_name": model_name,
            "answer": result['answer'],
            "response_time": end_time - start_time
        }
    except Exception as e:
        print(f"Error with {model_name}: {str(e)}")
        return {
            "model_name": model_name,
            "answer": f"Error: {str(e)}",
            "response_time": -1
        }

def main():
    # 질문 데이터셋 로드
    input_file = r"C:\dev\SKN10-FINAL-5Team\LLM\eval_qa_dataset.csv"
    questions_df = pd.read_csv(input_file)
    
    # 각 지표별로 10개씩 랜덤 샘플링
    sampled_questions = []
    for metric in questions_df['평가지표'].unique():
        metric_questions = questions_df[questions_df['평가지표'] == metric]
        sampled = metric_questions.sample(n=10, random_state=42)  # random_state로 재현성 보장
        sampled_questions.append(sampled)
    
    # 샘플링된 질문들을 하나의 DataFrame으로 합치기
    questions_df = pd.concat(sampled_questions, ignore_index=True)
    print(f"Selected {len(questions_df)} questions ({len(questions_df['평가지표'].unique())} metrics, 10 questions each)")
    
    # 모델 초기화
    models = initialize_models()
    
    # 결과 저장을 위한 리스트
    all_results = []
    
    # 각 질문에 대해 모든 모델의 응답 수집
    for _, row in questions_df.iterrows():
        question = row['자연스러운질문']
        policy_name = row['정책명']
        evaluation_metric = row['평가지표']
        
        print(f"\nProcessing question: {question}")
        
        for model_name, llm in models.items():
            print(f"Getting response from {model_name}...")
            result = get_model_response(model_name, llm, question)
            
            # 결과에 질문 정보 추가
            result.update({
                '평가지표': evaluation_metric,
                '정책명': policy_name,
                '질문': question
            })
            
            all_results.append(result)
            print(f"Completed {model_name} in {result['response_time']:.2f} seconds")
    
    # 결과를 DataFrame으로 변환
    df = pd.DataFrame(all_results)
    
    # 필요한 컬럼만 선택하고 순서 조정
    df = df[['평가지표', '정책명', '질문', 'model_name', 'answer']]
    df.columns = ['평가지표', '정책명', '질문', '모델', '대답']
    
    # CSV 파일로 저장
    output_file = r"C:\dev\SKN10-FINAL-5Team\LLM\models_qa_250625.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main() 