# base image
FROM python:3.13-slim

# OS 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 생성 및 설정
WORKDIR /app

# requirements.txt, .env 복사
#COPY ./requirements.txt /app/
#COPY ./.env /app/

# 프로젝트 코드 복사
#COPY ./Web /app/Web
COPY . /app

# 필요한 라이브러리 설치
RUN pip install --upgrade pip && pip install -r ./requirements.txt

# 포트 오픈 (Django 기본 8000)
EXPOSE 8000

# ALLOWED_HOSTS 설정
ENV DJANGO_ALLOWED_HOSTS="*"

# 마이그레이션 및 서버 실행
CMD ["sh", "-c", "cd Web && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
