from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from .models import PolicyRaw
from static.utils.category_colors import get_category_color

# 메인 페이지 뷰 함수
def home(request):
    # 현재 날짜 기준으로 신청 가능한 정책 중 조회수 상위 8개 가져오기
    today = timezone.now().date()
    popular_policies = PolicyRaw.objects.filter(
        ~Q(정책대분류명='기타'),    # 정책 대분류명이 '기타'가 아닌 경우
        ~Q(정책중분류명='기타'),    # 정책 중분류명이 '기타'가 아닌 경우
        신청시작일자__lte=today,    # 신청 시작일이 오늘 이전인 것
    ).filter(
        Q(신청종료일자__gte=today) | Q(신청종료일자__isnull=True)  # 신청 종료일이 오늘 이후이거나 없는 경우
    ).order_by('-조회수')[:8]  # 조회수 내림차순 정렬 후 8개만 가져오기

    # 각 정책에 색상 정보 추가
    for policy in popular_policies:
        policy.category_color = get_category_color(policy.정책중분류명)

    context = {
        'popular_policies': popular_policies
    }
    return render(request, 'home/home.html', context)

# 정책 상세 정보를 JSON으로 반환하는 API 뷰 함수
def get_policy_detail(request, policy_id):
    try:
        # 해당 ID의 정책 존재 여부 확인
        policy = PolicyRaw.objects.get(정책번호=policy_id)
        # 중분류명에 따른 색상 정보 추가
        category_color = get_category_color(policy.정책중분류명)
        # 정책 상세 정보를 JSON 형식으로 반환
        data = {
            '정책명': policy.정책명,
            '정책중분류명': policy.정책중분류명,
            '정책설명내용': policy.정책설명내용,
            '정책지원내용': policy.정책지원내용,
            '정책신청방법내용': policy.정책신청방법내용,
            '제출서류내용': policy.제출서류내용,
            '조회수': policy.조회수,
            '신청시작일자': policy.신청시작일자,
            '신청종료일자': policy.신청종료일자,
            '신청url주소': policy.신청url주소,
            '참고url주소1': policy.참고url주소1,
            '참고url주소2': policy.참고url주소2,
            'category_color': category_color,
        }
        return JsonResponse(data)
    except PolicyRaw.DoesNotExist:
        return JsonResponse({'error': '정책을 찾을 수 없습니다.'}, status=404)