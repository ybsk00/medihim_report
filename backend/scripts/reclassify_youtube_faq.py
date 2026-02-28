"""
YouTube FAQ 벡터 분류 정제 스크립트.

CLAUDE.md의 분류 가이드라인에 따라 YouTube FAQ 벡터의 category를 재분류한다.
- 명확 키워드 매칭 → 즉시 분류
- 경계 시술(보톡스/필러) → 동반 키워드로 분류
- 애매한 경우 → Gemini LLM 분류

사용법:
  cd backend
  python -m scripts.reclassify_youtube_faq             # 전체 실행
  python -m scripts.reclassify_youtube_faq --dry-run    # 변경 없이 분석만
"""
import sys
import time
import argparse
import asyncio
import json

sys.stdout.reconfigure(encoding="utf-8")

from services.supabase_client import get_supabase
from services.gemini_client import generate_json

# ── 분류 키워드 (CLAUDE.md 기준) ──────────────────────────

# 성형외과 명확 키워드
PS_KEYWORDS = [
    "쌍꺼풀", "코 성형", "코성형", "코끝", "코등", "콧대",
    "지방흡입", "안면윤곽", "양악", "이마 리프팅", "이마거상",
    "눈 재수술", "눈재수술", "가슴 수술", "가슴수술", "가슴성형",
    "턱 수술", "턱수술", "사각턱", "턱끝", "V라인", "v라인",
    "리프팅 실", "실리프팅", "코 재수술", "코재수술",
    "눈성형", "눈매교정", "눈매 교정", "안면거상",
    "지방이식", "지방 이식", "안면골", "윤곽수술",
    "매부리코", "들창코", "코높이", "코 높이",
    "눈밑지방", "눈밑 지방", "하안검", "상안검",
    "이중턱", "이중 턱", "인중축소", "입술축소",
    "페이스리프트", "안면리프팅", "풀페이스", "미니리프팅",
    "광대축소", "광대 축소", "사각턱축소", "턱끝수술",
    "눈앞트임", "눈뒤트임", "앞트임", "뒤트임",
    "코연골", "귀연골", "자가연골", "실리콘 보형물",
    "보형물", "임플란트", "유방", "가슴확대",
]

# 피부과 명확 키워드
DERM_KEYWORDS = [
    "여드름", "기미", "색소", "모공", "탈모",
    "레이저", "하이푸", "울쎄라", "울세라",
    "피부결", "주름 개선", "탄력", "리쥬란", "스킨 부스터",
    "피부과", "피부톤", "피부관리", "피부 관리",
    "필링", "흉터", "점제거", "점 제거",
    "화이트닝", "미백", "다크서클", "제모",
    "아토피", "습진", "건선", "두피",
    "모낭", "홍조", "주사피부염", "주사비",
    "피코레이저", "프락셀", "CO2레이저",
    "제네시스", "IPL", "BBL", "토닝",
    "스킨보톡스", "물광주사", "수분주사",
    "인모드", "써마지", "슈링크",
]

# 경계 시술
BOUNDARY_KEYWORDS = ["보톡스", "필러"]

# 경계 시술의 동반 키워드
BOUNDARY_PS_CONTEXT = [
    "코 높이기", "코높이", "턱 끝", "턱끝", "윤곽", "이마 볼륨",
    "이마볼륨", "리프팅 실", "실리프팅", "광대", "코끝", "코등",
    "안면", "성형", "수술", "볼륨", "이마", "관자놀이",
]
BOUNDARY_DERM_CONTEXT = [
    "레이저", "하이푸", "울쎄라", "울세라", "피부결", "주름 개선",
    "탄력", "리쥬란", "피부", "모공", "주름", "토닝",
    "여드름", "기미", "색소", "탈모", "인모드", "써마지",
]


def keyword_classify(question: str, answer: str, procedure_name: str) -> str | None:
    """키워드 매칭으로 분류. 확실하지 않으면 None 반환."""
    text = f"{question} {answer} {procedure_name or ''}".lower()

    ps_hits = [k for k in PS_KEYWORDS if k.lower() in text]
    derm_hits = [k for k in DERM_KEYWORDS if k.lower() in text]
    boundary_hits = [k for k in BOUNDARY_KEYWORDS if k.lower() in text]

    # 명확 키워드만 있는 경우
    if ps_hits and not derm_hits and not boundary_hits:
        return "plastic_surgery"
    if derm_hits and not ps_hits and not boundary_hits:
        return "dermatology"

    # 경계 시술만 있는 경우 → 동반 키워드로 판단
    if boundary_hits and not ps_hits and not derm_hits:
        ps_ctx = [k for k in BOUNDARY_PS_CONTEXT if k.lower() in text]
        derm_ctx = [k for k in BOUNDARY_DERM_CONTEXT if k.lower() in text]
        if ps_ctx and not derm_ctx:
            return "plastic_surgery"
        if derm_ctx and not ps_ctx:
            return "dermatology"
        # 둘 다 있거나 둘 다 없으면 → LLM에 맡김
        return None

    # 양쪽 키워드 모두 있는 경우 → LLM에 맡김
    if ps_hits and derm_hits:
        return None

    # 키워드 없는 경우 → 현재 분류 유지 (별도 표시)
    return "keep"


LLM_SYSTEM = """당신은 한국 의료 분류 전문가입니다.
주어진 의료 FAQ가 피부과(dermatology)인지 성형외과(plastic_surgery)인지 분류해주세요.

분류 기준:
- 성형외과: 쌍꺼풀, 코 성형/재수술, 지방흡입, 안면윤곽, 양악, 이마리프팅, 눈재수술, 가슴수술, 턱수술, V라인, 실리프팅, 안면거상, 눈매교정, 지방이식
- 피부과: 여드름, 기미, 색소, 모공, 탈모, 레이저, 하이푸, 울쎄라, 피부결, 주름개선, 탄력, 리쥬란, 스킨부스터, 필링, 써마지, 인모드, 슈링크
- 경계 시술(보톡스/필러): 성형 맥락(코높이기, 턱끝, 윤곽, 이마볼륨) → 성형외과, 피부 맥락(레이저, 하이푸, 피부결, 주름) → 피부과

핵심 의도가 기준입니다. 반드시 하나만 선택하세요."""


async def llm_classify_batch(items: list[dict]) -> list[str]:
    """Gemini LLM으로 배치 분류. items는 [{id, question, answer, procedure_name}, ...]"""
    if not items:
        return []

    prompt = "다음 의료 FAQ들을 각각 dermatology 또는 plastic_surgery로 분류해주세요.\nJSON 배열로 반환: [{\"id\": \"...\", \"category\": \"dermatology\" or \"plastic_surgery\"}]\n\n"
    for item in items:
        prompt += f"ID: {item['id']}\nQ: {item['question']}\nA: {item['answer'][:200]}\n시술명: {item.get('procedure_name', 'N/A')}\n\n"

    try:
        result = await generate_json(prompt, LLM_SYSTEM)
        parsed = json.loads(result)
        return {r["id"]: r["category"] for r in parsed}
    except Exception as e:
        print(f"  [LLM ERROR] {e}")
        return {}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="변경 없이 분석만")
    args = parser.parse_args()

    db = get_supabase()

    # 1) 전체 YouTube FAQ 가져오기 (PubMed 제외)
    print("YouTube FAQ 벡터 전체 로딩 중...")
    all_rows = []
    offset = 0
    while True:
        batch = (
            db.table("faq_vectors")
            .select("id,category,question,answer,procedure_name,youtube_url,youtube_video_id")
            .range(offset, offset + 999)
            .execute()
        )
        if not batch.data:
            break
        all_rows.extend(batch.data)
        if len(batch.data) < 1000:
            break
        offset += 1000

    youtube_rows = [
        r for r in all_rows
        if not (r.get("youtube_url") or "").startswith("https://pubmed")
    ]
    print(f"총 YouTube FAQ: {len(youtube_rows)}건")

    # 2) 키워드 기반 1차 분류
    print("\n키워드 기반 1차 분류 중...")
    keyword_results = {}  # id → new_category
    need_llm = []  # LLM 분류 필요한 항목
    keep_count = 0

    for row in youtube_rows:
        result = keyword_classify(
            row["question"], row["answer"], row.get("procedure_name", "")
        )
        if result == "keep":
            keep_count += 1
        elif result is None:
            need_llm.append(row)
        else:
            keyword_results[row["id"]] = result

    print(f"  키워드로 분류됨: {len(keyword_results)}건")
    print(f"  키워드 없음(유지): {keep_count}건")
    print(f"  LLM 분류 필요: {len(need_llm)}건")

    # 3) LLM 배치 분류 (20건씩)
    llm_results = {}
    if need_llm:
        print(f"\nLLM 배치 분류 시작 ({len(need_llm)}건)...")
        batch_size = 15
        for i in range(0, len(need_llm), batch_size):
            batch = need_llm[i : i + batch_size]
            print(f"  배치 {i // batch_size + 1}/{(len(need_llm) + batch_size - 1) // batch_size} ({len(batch)}건)...")
            batch_result = await llm_classify_batch(batch)
            llm_results.update(batch_result)
            time.sleep(1)  # rate limit

    print(f"  LLM 분류 완료: {len(llm_results)}건")

    # 4) 결과 합산 및 변경 건수 산출
    all_results = {**keyword_results, **llm_results}

    changes = []
    for row in youtube_rows:
        new_cat = all_results.get(row["id"])
        if new_cat and new_cat != row["category"]:
            changes.append({
                "id": row["id"],
                "old": row["category"],
                "new": new_cat,
                "question": row["question"][:60],
                "procedure": row.get("procedure_name", ""),
            })

    # 5) 변경 요약 출력
    derm_to_ps = [c for c in changes if c["old"] == "dermatology"]
    ps_to_derm = [c for c in changes if c["old"] == "plastic_surgery"]

    print(f"\n{'=' * 60}")
    print(f"  분류 변경 요약")
    print(f"{'=' * 60}")
    print(f"  피부과 → 성형외과: {len(derm_to_ps)}건")
    print(f"  성형외과 → 피부과: {len(ps_to_derm)}건")
    print(f"  총 변경: {len(changes)}건 / {len(youtube_rows)}건")

    if derm_to_ps:
        print(f"\n  [피부과 → 성형외과 샘플]")
        for c in derm_to_ps[:10]:
            print(f"    [{c['procedure']}] {c['question']}")

    if ps_to_derm:
        print(f"\n  [성형외과 → 피부과 샘플]")
        for c in ps_to_derm[:10]:
            print(f"    [{c['procedure']}] {c['question']}")

    # 6) 실제 DB 업데이트
    if args.dry_run:
        print(f"\n[DRY RUN] 실제 변경하지 않았습니다.")
        return

    if not changes:
        print("\n변경할 항목이 없습니다.")
        return

    print(f"\nDB 업데이트 중 ({len(changes)}건)...")
    success = 0
    fail = 0
    for c in changes:
        try:
            db.table("faq_vectors").update({"category": c["new"]}).eq("id", c["id"]).execute()
            success += 1
        except Exception as e:
            fail += 1
            print(f"  [ERROR] {c['id']}: {e}")

    print(f"\n완료! 성공: {success}건, 실패: {fail}건")

    # 7) 최종 통계
    derm_count = (
        db.table("faq_vectors")
        .select("*", count="exact")
        .eq("category", "dermatology")
        .execute()
    )
    ps_count = (
        db.table("faq_vectors")
        .select("*", count="exact")
        .eq("category", "plastic_surgery")
        .execute()
    )
    print(f"\n최종 벡터 분포:")
    print(f"  피부과: {derm_count.count}건")
    print(f"  성형외과: {ps_count.count}건")


if __name__ == "__main__":
    asyncio.run(main())
