from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from .models import PolicyRaw

# 중분류명에 따른 색상 매핑
CATEGORY_COLORS = {
    '건강': {'bg': 'bg-red-100', 'text': 'text-red-700'},
    '창업': {'bg': 'bg-yellow-100', 'text': 'text-yellow-700'},
    '취업 전후 지원': {'bg': 'bg-blue-100', 'text': 'text-blue-700'},
    '대출,이자, 전월세 등 금융지원': {'bg': 'bg-indigo-100', 'text': 'text-indigo-700'},
    '이사비, 부동산 중개비, 가전 지원': {'bg': 'bg-purple-100', 'text': 'text-purple-700'},
    '권익보호': {'bg': 'bg-pink-100', 'text': 'text-pink-700'},
    '문화활동': {'bg': 'bg-green-100', 'text': 'text-green-700'},
    '청년참여': {'bg': 'bg-emerald-100', 'text': 'text-emerald-700'},
    '취약계층 및 금융지원': {'bg': 'bg-cyan-100', 'text': 'text-cyan-700'},
    '취약계층 및 금융지원,건강': {'bg': 'bg-cyan-100', 'text': 'text-cyan-700'},
    '임대주택, 기숙사': {'bg': 'bg-violet-100', 'text': 'text-violet-700'},
    '청년참여,정책인프라구축': {'bg': 'bg-emerald-100', 'text': 'text-emerald-700'},
    '교육비지원': {'bg': 'bg-teal-100', 'text': 'text-teal-700'},
    '예술인지원': {'bg': 'bg-orange-100', 'text': 'text-orange-700'},
    '청년국제교류': {'bg': 'bg-sky-100', 'text': 'text-sky-700'},
    '전문인력양성, 훈련': {'bg': 'bg-amber-100', 'text': 'text-amber-700'},
    '정책인프라구축': {'bg': 'bg-lime-100', 'text': 'text-lime-700'},
    '기타': {'bg': 'bg-gray-100', 'text': 'text-gray-700'},
}

def get_category_color(category):
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS['기타'])

# Create your views here.
def home(request):
    # 현재 날짜 기준으로 신청 가능한 정책 중 조회수 상위 7개 가져오기
    today = timezone.now().date()
    popular_policies = PolicyRaw.objects.filter(
        Q(신청종료일자__gte=today) | Q(신청종료일자__isnull=True),  # 신청 종료일이 오늘 이후이거나 없는 경우
        신청시작일자__lte=today   # 신청 시작일이 오늘 이전인 것
    ).order_by('-조회수')[:7]  # 조회수 내림차순 정렬 후 7개만 가져오기

    # 각 정책에 색상 정보 추가
    for policy in popular_policies:
        policy.category_color = get_category_color(policy.정책중분류명)

    context = {
        'popular_policies': popular_policies
    }
    return render(request, 'home/home.html', context)