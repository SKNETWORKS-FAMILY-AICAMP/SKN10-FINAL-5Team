# 1. 공식 Python 이미지 사용 (버전은 프로젝트에 맞게 수정)
FROM python:3.13-slim

# 2. 작업 디렉토리 생성 및 이동
WORKDIR /app

# 3. 필요한 파일 복사 (코드, requirements.txt 등)
COPY requirements.txt ./
COPY . .

# 4. 패키지 설치 (필요시 빌드툴 추가)
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 5. (선택) 포트 오픈 (예: FastAPI/Flask/Streamlit)
# EXPOSE 8000

# 6. 컨테이너 시작 시 실행할 명령 (아래는 main.py 예시)
CMD ["python", "chatbot.py"]