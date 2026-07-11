"""치과 end-to-end + 회귀 테스트. 브랜치 DB 대상.

전제 (환경변수 주입 방식 — .env 파일은 건드리지 않음):
  - SUPABASE_URL / SUPABASE_SERVICE_KEY = 브랜치 값 (backend/.env.branch 참조)
  - IPPEO_WEBHOOK_URL = "" (PROD 라이브 유입 금지)
  - IPPEO_WEBHOOK_URL_DEV = 설정 유지 (DEV 콜백 검증)

실행:
  cd backend && SUPABASE_URL=<branch> SUPABASE_SERVICE_KEY=<branch> IPPEO_WEBHOOK_URL= \
    python ../test_dentistry_e2e.py
"""
import asyncio
import sys
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

from services.supabase_client import get_supabase
from agents.pipeline import run_pipeline

DENTAL_STT = """カウンセラー: こんにちは、本日のご相談内容をお聞かせください。
お客様: 奥歯が虫歯でだいぶ削れていて、インプラントを考えています。
カウンセラー: インプラントですね。骨の状態にもよりますが、治療期間は3〜6ヶ月ほどです。
お客様: 費用はどのくらいですか？何回くらい通院が必要ですか？
カウンセラー: 1本あたりの目安と通院回数は診察後にご案内します。まずは口腔内の検査が必要です。
お客様: 来月から始めたいです。セラミックの被せ物も気になっています。"""

DERMA_STT = """カウンセラー: 本日はどのようなご相談ですか？
お客様: 最近シミが増えてきて、ピコレーザーを考えています。毛穴も気になります。
カウンセラー: レーザートーニングが効果的です。3〜5回のコースが一般的です。"""

PLASTIC_STT = """カウンセラー: ご相談内容をお聞かせください。
お客様: 鼻が低くて、プロテーゼで高くしたいです。横顔のラインが気になります。
カウンセラー: 鼻筋を通す隆鼻術ですね。軟骨移植との組み合わせもご提案できます。"""


async def _run_case(name, stt, expected_class):
    db = get_supabase()
    ins = db.table("consultations").insert({
        "customer_name": f"E2E {name}",
        "customer_email": "e2e@example.com",
        "original_text": stt,
        "status": "registered",
        "consultation_round": 3,
        "ippeo_consultation_id": f"e2e_{name}_r3",
    }).execute()
    cid = ins.data[0]["id"]
    await run_pipeline(cid)

    row = db.table("consultations").select("classification, status").eq("id", cid).single().execute().data
    print(f"[{name}] classification={row['classification']} status={row['status']} (expected {expected_class})")
    assert row["classification"] == expected_class, f"{name} 분류 실패: {row['classification']}"

    reports = db.table("reports").select("report_type, report_data, access_token").eq("consultation_id", cid).execute().data
    types = {r["report_type"] for r in reports}
    assert "r3" in types and "r4" in types, f"{name} R3/R4 누락: {types}"

    r4 = next(r for r in reports if r["report_type"] == "r4")
    for k in ("section1_key_summary", "section8_cost_estimate", "section10_ippeo_message"):
        assert k in r4["report_data"], f"{name} R4 키 누락: {k}"
    print(f"[{name}] R3+R4 OK, R4 keys intact, token={r4['access_token'][:8]}")
    return cid


async def _check_rag_isolation():
    from agents.rag_agent import search_relevant_faq
    res = await search_relevant_faq(["임플란트", "신경치료", "치아교정"], "dentistry")
    assert res, "치과 RAG 결과 0건 — 벡터 구축/카테고리 확인 필요"
    print(f"[RAG] dentistry 검색 {len(res)}건, 첫 시술명={res[0].get('procedure_name')}")


async def main():
    await _check_rag_isolation()
    dental_cid = await _run_case("dental", DENTAL_STT, "dentistry")
    await _run_case("derma", DERMA_STT, "dermatology")
    await _run_case("plastic", PLASTIC_STT, "plastic_surgery")

    # DEV 콜백 실전송 (dental 케이스)
    from services.ippeo_callback import notify_report_ready
    await notify_report_ready(dental_cid)
    print("[Callback] dental DEV 콜백 전송 완료 (로그에서 200 확인)")
    print("\nOK: 치과 E2E + 회귀 통과")


if __name__ == "__main__":
    asyncio.run(main())
