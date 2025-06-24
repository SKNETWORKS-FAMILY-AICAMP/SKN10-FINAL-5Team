from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from .models import Policies
from static.utils.category_colors import get_category_color

# 메인 페이지 뷰 함수
def home(request):
    # 현재 날짜 기준으로 신청 가능한 정책 중 조회수 상위 8개 가져오기
    today = timezone.now().date()
    popular_policies = Policies.objects.filter(
        ~Q(lclsf_nm='기타'),    # 정책 대분류명이 '기타'가 아닌 경우
        ~Q(mclsf_nm='기타'),    # 정책 중분류명이 '기타'가 아닌 경우
        aply_bgng_ymd__lte=today,    # 신청 시작일이 오늘 이전인 것
    ).filter(
        Q(aply_end_ymd__gte=today) | Q(aply_end_ymd__isnull=True)  # 신청 종료일이 오늘 이후이거나 없는 경우
    ).order_by('-inq_cnt')[:8]  # 조회수 내림차순 정렬 후 8개만 가져오기

    # 각 정책에 색상 정보 추가
    for policy in popular_policies:
        policy.category_color = get_category_color(policy.mclsf_nm)

    context = {
        'popular_policies': popular_policies
    }
    return render(request, 'home/home.html', context)

# 정책 상세 정보를 JSON으로 반환하는 API 뷰 함수
def get_policy_detail(request, policy_id):
    try:
        # 해당 ID의 정책 존재 여부 확인
        policy = Policies.objects.get(plcy_no=policy_id)
        # 중분류명에 따른 색상 정보 추가
        category_color = get_category_color(policy.mclsf_nm)
        # 정책 상세 정보를 JSON 형식으로 반환
        data = {
            'plcy_nm': policy.plcy_nm,
            'mclsf_nm': policy.mclsf_nm,
            'plcy_expln_cn': policy.plcy_expln_cn,
            'plcy_sprt_cn': policy.plcy_sprt_cn,
            'plcy_aply_mthd_cn': policy.plcy_aply_mthd_cn,
            'sbmsn_dcmnt_cn': policy.sbmsn_dcmnt_cn,
            'inq_cnt': policy.inq_cnt,
            'aply_bgng_ymd': policy.aply_bgng_ymd,
            'aply_end_ymd': policy.aply_end_ymd,
            'aply_url_addr': policy.aply_url_addr,
            'ref_url_addr1': policy.ref_url_addr1,
            'ref_url_addr2': policy.ref_url_addr2,
            'category_color': category_color,
            'zip_cd': policy.zip_cd,
        }
        return JsonResponse(data)
    except Policies.DoesNotExist:
        return JsonResponse({'error': '정책을 찾을 수 없습니다.'}, status=404)