import pandas as pd
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yourproject.settings")
django.setup()

from Web.Chatbot.models import YouthPolicy
from Web.Chatbot.graph_models import PolicyNode

# CSV 파일 경로
csv_path = '청년정책목록_2025-06-01_v9.csv'

df = pd.read_csv(csv_path, dtype=str).fillna('')

for _, row in df.iterrows():
    # PostgreSQL 저장
    policy, created = YouthPolicy.objects.get_or_create(
        policy_id=row['정책번호'],
        defaults={
            'delivery_method': row['정책제공방법코드'],
            'name': row['정책명'],
            'keywords': row['정책키워드명'],
            'description': row['정책설명내용'],
            'main_category': row['정책대분류명'],
            'sub_category': row['정책중분류명'],
            'support_content': row['정책지원내용'],
            'agency': row['주관기관코드명'],
            'operating_agency': row['운영기관코드명'],
            'application_period_type': row['신청기간구분코드'],
            'business_period_type': row['사업기간구분코드'],
            'business_start_date': row['사업기간시작일자'],
            'business_end_date': row['사업기간종료일자'],
            'etc_business_period': row['사업기간기타내용'],
            'application_method': row['정책신청방법내용'],
            'review_method': row['심사방법내용'],
            'application_url': row['신청URL주소'],
            'required_documents': row['제출서류내용'],
            'etc': row['기타사항내용'],
            'reference_url1': row['참고URL주소1'],
            'reference_url2': row['참고URL주소2'],
            'first_come_first_served': row['지원도착순서여부'],
            'min_age': row['지원대상최소연령'],
            'max_age': row['지원대상최대연령'],
            'marital_status': row['결혼상태코드'],
            'income_condition': row['소득조건구분코드'],
            'etc_income_condition': row['소득기타내용'],
            'additional_qualification': row['추가신청자격조건내용'],
            'proposal_target': row['참여제안대상내용'],
            'view_count': int(row['조회수']) if row['조회수'] else None,
            'region': row['정책거주지역코드'],
            'major_condition': row['정책전공요건코드'],
            'employment_condition': row['정책취업요건코드'],
            'education_condition': row['정책학력요건코드'],
            'application_start_date': row['신청시작일자'],
            'application_end_date': row['신청종료일자'],
            'specialized_condition': row['정책특화요건코드'],
        }
    )

    # Neo4j 저장
    node = PolicyNode.nodes.get_or_none(policy_id=row['정책번호'])
    if not node:
        PolicyNode(
            policy_id=row['정책번호'],
            name=row['정책명'],
            keywords=row['정책키워드명'],
            description=row['정책설명내용'],
            main_category=row['정책대분류명'],
            sub_category=row['정책중분류명'],
            region=row['정책거주지역코드'],
            min_age=row['지원대상최소연령'],
            max_age=row['지원대상최대연령'],
        ).save()