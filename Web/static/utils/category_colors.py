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
    '기타': {'bg': 'bg-fuchsia-100', 'text': 'text-fuchsia-700'},
}

def get_category_color(category):
    """
    중분류명에 따른 색상 매핑 함수
    존재하지 않는 중분류명에 대해서는 '기타'색상으로 처리
    
    Args:
        category (str): 정책 중분류명
        
    Returns:
        dict: 배경색과 텍스트 색상 정보를 담은 딕셔너리
    """
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS['기타']) 