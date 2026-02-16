"""
벡터DB 구축 파이프라인 실행 스크립트.

사용법:
  cd backend
  python -m scripts.build_vector_db           # 전체 실행
  python -m scripts.build_vector_db --step 1  # 영상 수집만
  python -m scripts.build_vector_db --step 2  # 자막 추출만
  python -m scripts.build_vector_db --step 3  # 자막 정제만
  python -m scripts.build_vector_db --step 4  # FAQ 생성만
  python -m scripts.build_vector_db --step 5  # 임베딩만
"""
import argparse
from services.youtube_service import (
    fetch_all_channels,
    extract_all_transcripts,
    refine_all_transcripts,
    generate_all_faqs,
    embed_all_faqs,
)
from services.supabase_client import get_supabase


def print_stats():
    db = get_supabase()

    print(f"\n{'=' * 50}")
    print(f"  벡터DB 구축 최종 통계")
    print(f"{'=' * 50}")

    for category, label in [
        ("dermatology", "피부과"),
        ("plastic_surgery", "성형외과"),
    ]:
        sources = (
            db.table("youtube_sources")
            .select("*", count="exact")
            .eq("category", category)
            .execute()
        )
        embedded = (
            db.table("youtube_sources")
            .select("*", count="exact")
            .eq("category", category)
            .eq("status", "embedded")
            .execute()
        )
        skipped = (
            db.table("youtube_sources")
            .select("*", count="exact")
            .eq("category", category)
            .eq("status", "skipped")
            .execute()
        )
        faqs = (
            db.table("faq_vectors")
            .select("*", count="exact")
            .eq("category", category)
            .execute()
        )

        print(f"\n  [{label}]")
        print(f"    전체 영상: {sources.count}")
        print(f"    임베딩 완료: {embedded.count}")
        print(f"    스킵 (자막 없음): {skipped.count}")
        print(f"    생성된 FAQ: {faqs.count}")

    total_faqs = db.table("faq_vectors").select("*", count="exact").execute()
    print(f"\n  총 FAQ 벡터: {total_faqs.count}개")
    print(f"{'=' * 50}\n")


def run_pipeline(step=None):
    steps = {
        1: ("영상 수집 (YouTube API)", fetch_all_channels),
        2: ("자막 추출 (youtube-transcript-api)", extract_all_transcripts),
        3: ("자막 정제 (Gemini LLM)", refine_all_transcripts),
        4: ("FAQ 변환 (Gemini LLM)", generate_all_faqs),
        5: ("임베딩 + 벡터 저장 (Gemini Embedding)", embed_all_faqs),
    }

    if step:
        name, func = steps[step]
        print(f"\n{'=' * 50}")
        print(f"  STEP {step}: {name}")
        print(f"{'=' * 50}\n")
        func()
    else:
        for step_num, (name, func) in steps.items():
            print(f"\n{'=' * 50}")
            print(f"  STEP {step_num}/5: {name}")
            print(f"{'=' * 50}\n")
            func()
            print(f"\n  STEP {step_num} 완료!\n")

        print_stats()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="벡터DB 구축 파이프라인")
    parser.add_argument(
        "--step", type=int, choices=[1, 2, 3, 4, 5], help="실행할 단계 (1-5)"
    )
    parser.add_argument(
        "--stats", action="store_true", help="현재 통계만 출력"
    )
    args = parser.parse_args()

    if args.stats:
        print_stats()
    else:
        run_pipeline(args.step)
