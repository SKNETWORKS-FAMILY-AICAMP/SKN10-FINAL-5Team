# syntax=docker/dockerfile:1
FROM --platform=linux/amd64 python:3.13-slim

# 작업 디렉토리
WORKDIR /app

# zip 설치
RUN apt-get update && apt-get install -y zip

# 라이브러리 설치 경로 생성
RUN mkdir -p /app/python

# 라이브러리 설치
RUN pip install --upgrade pip && \
    pip install openai tqdm pandas requests certifi --target=/app/python

# zip 파일 생성
RUN zip -r /app/lambda_layer.zip python
