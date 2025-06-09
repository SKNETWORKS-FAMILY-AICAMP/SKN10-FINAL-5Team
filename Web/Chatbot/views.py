
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views import View
from .models import YouthPolicy
import openai
from django.shortcuts import render


@csrf_exempt
def chatbot_query(request):
    if request.method == 'POST':
        user_msg = request.POST.get('message')
        # 정책 DB에서 정책명/키워드/설명 등 검색
        policies = YouthPolicy.objects.filter(
            description__icontains=user_msg
        )[:3]
        policy_summaries = '\n'.join([f"{p.name}: {p.description[:100]}" for p in policies])
        prompt = f"""사용자 질문: {user_msg}
아래는 청년정책 데이터 일부입니다.
{policy_summaries}
위 정책 중에서 사용자 질문에 가장 적합한 정보를 요약해서 답변하세요."""

        # OpenAI API 호출 (예시)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "너는 청년정책 상담 챗봇이다."},
                      {"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message['content']
        return JsonResponse({'answer': answer})
    

def chatbot_page(request):
    return render(request, 'chat.html')