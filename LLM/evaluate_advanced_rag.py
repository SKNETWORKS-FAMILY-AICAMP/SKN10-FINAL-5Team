# evaluate_advanced_rag.py
import argparse, pandas as pd, traceback, sys
from tqdm import tqdm

# ── RAG 시스템 모듈 로드 ─────────────────────────────────────────────────────────
import advanced_rag as rag
from langchain_core.messages import HumanMessage

graph     = rag.graph                      # LangGraph 파이프라인
QA_FIELDS = ["lclsf_nm", "age", "school_cd",
             "job_cd", "mrg_stts_cd", "zip_cd", "plcy_major_cd"]

# ── 평가 함수들 ──────────────────────────────────────────────────────────────────
def evaluate_row(row, k):
    """한 개 질의에 대한 분석 정확도 · Hit@k · RR을 반환"""
    # ① 그래프 실행
    init_state = {"messages": [HumanMessage(content=row.query_text)]}
    try:
        result_state = graph.invoke(init_state)   # 2분 제한
    except Exception:
        traceback.print_exc()
        return {f"{f}_correct": 0 for f in QA_FIELDS} | {"hit": 0, "rr": 0}

    # ② 질의 분석 정확도
    qa_result = getattr(result_state.get("query_analysis", None), "__dict__", {})
    field_correct = {f"{f}_correct": int(str(qa_result.get(f, "")).strip() ==
                                         str(row[f]).strip())
                     for f in QA_FIELDS}

    # ③ 추천 Hit / RR
    preds = [p.plcy_no for p in (result_state.get("selected_policies") or [])][:k]
    gts   = [p.strip() for p in str(row.ground_truth_policies).split(";") if p.strip()]
    hit   = int(any(gt in preds for gt in gts))
    rr    = 0
    for rank, p in enumerate(preds, 1):
        if p in gts:
            rr = 1 / rank
            break

    return field_correct | {"hit": hit, "rr": rr}

def aggregate(results):
    """평가 결과 리스트를 집계해 지표 산출"""
    df = pd.DataFrame(results)
    metrics = {
        "accuracy":  df[[c for c in df.columns if c.endswith("_correct")]].mean().mean(),
        "hit@k":     df["hit"].mean(),
        "mrr":       df["rr"].mean(),
    }
    per_field = {c.replace("_correct", ""): df[c].mean()
                 for c in df.columns if c.endswith("_correct")}
    return metrics, per_field

# ── main ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="평가용 CSV 경로")
    ap.add_argument("--k", type=int, default=5, help="Hit@k / MRR k값")
    args = ap.parse_args()

    data = pd.read_csv(args.csv)
    all_results = [evaluate_row(r, args.k) for _, r in tqdm(data.iterrows(),
                                                            total=len(data))]
    metrics, per_field = aggregate(all_results)

    print("\n=== 전체 지표 ===")
    for k, v in metrics.items():
        print(f"{k:<10}: {v:.4f}")

    print("\n=== 질의 분석 필드별 정확도 ===")
    for f, v in per_field.items():
        print(f"{f:<12}: {v:.4f}")
