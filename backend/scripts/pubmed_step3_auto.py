"""
PubMed Step 2 완료 대기 후 자동으로 Step 3(임베딩) 실행.
"""
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.supabase_client import get_supabase


def wait_and_run_step3():
    db = get_supabase()
    print("Waiting for PubMed Step 2 to complete...")
    print("Checking every 60s for new PubMed FAQs with dummy embeddings...\n")

    last_count = 0
    stable_checks = 0

    while True:
        try:
            result = db.table("faq_vectors") \
                .select("id", count="exact") \
                .like("youtube_url", "%pubmed.ncbi.nlm.nih.gov%") \
                .execute()
            current = result.count or 0
            print(f"  PubMed FAQs in DB: {current} (last: {last_count})", flush=True)

            if current > 0 and current == last_count:
                stable_checks += 1
                if stable_checks >= 3:  # 3분간 변화 없으면 완료로 판단
                    print(f"\n  Step 2 appears complete ({current} FAQs). Starting Step 3...")
                    break
            else:
                stable_checks = 0

            last_count = current
        except Exception as e:
            print(f"  DB check error: {str(e)[:80]}")

        time.sleep(60)

    # Step 3 실행
    from scripts.build_pubmed_vectors import embed_pubmed_faqs, print_stats
    print(f"\n{'=' * 50}")
    print(f"  STEP 3: 임베딩 (Gemini Embedding)")
    print(f"{'=' * 50}\n")
    embed_pubmed_faqs()
    print_stats()


if __name__ == "__main__":
    wait_and_run_step3()
