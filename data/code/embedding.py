import os
import pandas as pd
import pickle
import tiktoken
from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.docstore.document import Document

load_dotenv()

# 데이터 불러오기
df = pd.read_csv("../청년정책목록_전처리완료_2025-06-20.csv")

# 임베딩할 텍스트 구성
df["통합본문"] = df[
    ["정책명", "정책설명내용", "정책지원내용", "사업기간기타내용", "정책신청방법내용", "심사방법내용",
     "제출서류내용", "기타사항내용", "소득기타내용", "추가신청자격조건내용", "참여제안대상내용"]
].fillna("").agg("\n".join, axis=1)

# LangChain 문서 객체
documents = [
    Document(
        page_content=row["통합본문"],
        metadata={key: row[key] for key in [
            "정책번호", "정책명", "정책제공방법코드", "정책대분류명", "정책중분류명", "주관기관코드명",
            "운영기관코드명", "신청시작일자", "신청종료일자", "신청기간구분코드", "사업기간구분코드",
            "사업기간시작일자", "사업기간종료일자", "지원대상최소연령", "지원대상최대연령", "결혼상태코드",
            "소득조건구분코드", "정책거주지역코드", "정책전공요건코드", "정책취업요건코드", "정책학력요건코드",
            "정책특화요건코드"
        ]}
    )
    for _, row in df.iterrows()
]

# 토큰 계산
tokenizer = tiktoken.get_encoding("cl100k_base")
token_counts = [len(tokenizer.encode(doc.page_content)) for doc in documents]

# 30만 토큰 이하로 배치
MAX_TOKENS = 300_000
batches, current_batch, current_tokens = [], [], 0
for doc, tokens in zip(documents, token_counts):
    if current_tokens + tokens > MAX_TOKENS:
        batches.append(current_batch)
        current_batch = [doc]
        current_tokens = tokens
    else:
        current_batch.append(doc)
        current_tokens += tokens
if current_batch:
    batches.append(current_batch)

# OpenAI Embedding (large)
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

# FAISS 인덱스 생성 및 병합
vector_db = FAISS.from_documents(batches[0], embedding_model)
for batch in batches[1:]:
    vector_db.add_documents(batch)

# 저장
output_dir = "vector_db_openai_large_combined"
os.makedirs(output_dir, exist_ok=True)
vector_db.save_local(output_dir)
with open(os.path.join(output_dir, "documents.pkl"), "wb") as f:
    pickle.dump(documents, f)
with open(os.path.join(output_dir, "metadata.pkl"), "wb") as f:
    pickle.dump([doc.metadata for doc in documents], f)
