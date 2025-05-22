import requests
import pandas as pd
import time 


url = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
api_key = "d90d3d08-b51d-4c22-b3e3-269e1016e33c"


all_items = []
page = 1
page_size = 100

while True:
    params = {
        "apiKeyNm": api_key,
        "pageNum": page,
        "pageSize": page_size,
        "rtnType": "json"
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"요청 실패 (status {response.status_code}) - page {page}")
        break

    try:
        data = response.json()
        items = data["result"]["youthPolicyList"]

        if not items:
            print(f"전체 수집 완료: {page - 1} 페이지")
            break

        all_items.extend(items)
        print(f"{page} 페이지 수집 완료 (누적: {len(all_items)})")
        page += 1

        time.sleep(0.3)  

    except Exception as e:
        print("JSON 파싱 오류:", e)
        print("응답 내용:", response.text)
        break


if all_items:
    df = pd.DataFrame(all_items)
    df.to_csv("청년정책목록_전체.csv", index=False, encoding="utf-8-sig")
    print("전체 CSV 저장 완료")
else:
    print("수집된 데이터가 없습니다.")
