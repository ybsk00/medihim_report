"""
PubMed -> 벡터DB 구축 파이프라인.

PubMed API로 논문 수집 -> Gemini로 한국어 FAQ 변환 -> Gemini Embedding -> pgvector 저장.
기존 YouTube FAQ와 같은 faq_vectors 테이블에 저장, youtube_url로 PubMed 소스 구분.

사용법:
  cd backend
  python -m scripts.build_pubmed_vectors              # 전체 실행
  python -m scripts.build_pubmed_vectors --step 1      # 수집만
  python -m scripts.build_pubmed_vectors --step 2      # FAQ 변환만
  python -m scripts.build_pubmed_vectors --step 3      # 임베딩만
  python -m scripts.build_pubmed_vectors --stats        # 통계
"""
import argparse
import json
import os
import sys
import time
import re
from typing import Any

from Bio import Entrez
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, NCBI_API_KEY, NCBI_EMAIL, NCBI_TOOL
from services.supabase_client import get_supabase


# ============================================
# 유틸
# ============================================
def _safe_print(msg: str):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"), flush=True)


def _db_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                _safe_print(f"    -> DB error (retry {attempt+1}), wait {wait}s...")
                time.sleep(wait)
            else:
                raise


# ============================================
# Entrez (PubMed API) 설정
# ============================================
Entrez.email = NCBI_EMAIL
Entrez.tool = NCBI_TOOL
if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY

# API 키 있으면 10req/sec, 없으면 3req/sec
_REQ_DELAY = 0.15 if NCBI_API_KEY else 0.4


# ============================================
# Gemini Client (새 SDK)
# ============================================
_gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def _gemini_call(prompt: str, max_retries: int = 5) -> str:
    """Gemini 호출 + 429 자동 재시도. 무료 15RPM 고려하여 sleep(5) 포함."""
    for attempt in range(max_retries):
        try:
            response = _gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response and response.text:
                return response.text.strip()
            return ""
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = 30 * (attempt + 1)
                _safe_print(f"    -> Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif "500" in err_str or "503" in err_str:
                wait = 15 * (attempt + 1)
                _safe_print(f"    -> Server error, retrying in {wait}s...")
                time.sleep(wait)
            else:
                _safe_print(f"    -> Gemini error: {err_str[:120]}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    return ""
    return ""


# ============================================
# 검색 쿼리 정의 (34개)
# ============================================
DERMATOLOGY_QUERIES = [
    {
        "name": "보톡스(주름)",
        "query": "(botulinum toxin[Title/Abstract]) AND (forehead OR glabellar OR crow's feet[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "보톡스(주름)",
        "category": "dermatology",
    },
    {
        "name": "보톡스(사각턱)",
        "query": "(botulinum toxin[Title/Abstract]) AND (masseter OR jaw reduction OR facial slimming[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "보톡스(사각턱)",
        "category": "dermatology",
    },
    {
        "name": "보톡스(목주름)",
        "query": "(botulinum toxin[Title/Abstract]) AND (platysma OR neck band OR nefertiti[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "보톡스(목주름)",
        "category": "dermatology",
    },
    {
        "name": "필러(팔자주름)",
        "query": "(hyaluronic acid filler[Title/Abstract]) AND (nasolabial OR marionette[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "필러(팔자주름)",
        "category": "dermatology",
    },
    {
        "name": "필러(볼/턱)",
        "query": "(dermal filler[Title/Abstract]) AND (cheek OR chin augmentation OR midface volume[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "필러(볼/턱)",
        "category": "dermatology",
    },
    {
        "name": "필러(입술)",
        "query": "(lip filler OR lip augmentation[Title/Abstract]) AND (hyaluronic acid[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "필러(입술)",
        "category": "dermatology",
    },
    {
        "name": "필러(눈밑)",
        "query": "(tear trough OR under eye filler OR infraorbital hollow[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "필러(눈밑)",
        "category": "dermatology",
    },
    {
        "name": "울쎄라(HIFU)",
        "query": "(HIFU OR Ultherapy[Title/Abstract]) AND (face lift OR skin tightening[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "울쎄라(HIFU)",
        "category": "dermatology",
    },
    {
        "name": "써마지(RF)",
        "query": "(radiofrequency OR Thermage[Title/Abstract]) AND (skin tightening[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "써마지(RF)",
        "category": "dermatology",
    },
    {
        "name": "실리프팅",
        "query": "(thread lift OR PDO thread[Title/Abstract]) AND (facial rejuvenation[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "실리프팅",
        "category": "dermatology",
    },
    {
        "name": "피코레이저(색소)",
        "query": "(picosecond laser[Title/Abstract]) AND (pigmentation OR melasma[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "피코레이저",
        "category": "dermatology",
    },
    {
        "name": "프락셀(흉터)",
        "query": "(fractional laser OR CO2 laser[Title/Abstract]) AND (acne scar OR resurfacing[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "프락셀(흉터치료)",
        "category": "dermatology",
    },
    {
        "name": "IPL(홍조)",
        "query": "(IPL OR intense pulsed light[Title/Abstract]) AND (rosacea OR facial redness[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "IPL",
        "category": "dermatology",
    },
    {
        "name": "레이저토닝(기미)",
        "query": "(laser toning OR low-fluence Nd:YAG[Title/Abstract]) AND (melasma[Title/Abstract]) AND (Asian[Title/Abstract])",
        "procedure": "레이저토닝",
        "category": "dermatology",
    },
    {
        "name": "스킨부스터(리쥬란)",
        "query": "(skin booster OR polynucleotide OR PDRN OR Rejuran[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "스킨부스터/리쥬란",
        "category": "dermatology",
    },
    {
        "name": "스컬트라",
        "query": "(poly-L-lactic acid OR Sculptra OR collagen stimulator[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "스컬트라",
        "category": "dermatology",
    },
    {
        "name": "엑소좀/PRP",
        "query": "(exosome OR growth factor OR PRP[Title/Abstract]) AND (skin rejuvenation[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "엑소좀/PRP",
        "category": "dermatology",
    },
    {
        "name": "레이저제모",
        "query": "(laser hair removal OR diode laser OR alexandrite[Title/Abstract]) AND (efficacy OR satisfaction[Title/Abstract])",
        "procedure": "레이저제모",
        "category": "dermatology",
    },
]

PLASTIC_SURGERY_QUERIES = [
    {
        "name": "쌍꺼풀",
        "query": "(double eyelid OR blepharoplasty[Title/Abstract]) AND (Asian[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "쌍꺼풀수술",
        "category": "plastic_surgery",
    },
    {
        "name": "눈매교정",
        "query": "(ptosis correction OR levator[Title/Abstract]) AND (aesthetic[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "눈매교정",
        "category": "plastic_surgery",
    },
    {
        "name": "눈밑지방재배치",
        "query": "(lower blepharoplasty OR fat repositioning[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "눈밑지방재배치",
        "category": "plastic_surgery",
    },
    {
        "name": "트임(앞트임/뒤트임)",
        "query": "(epicanthoplasty OR canthoplasty[Title/Abstract]) AND (Asian[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "앞트임/뒤트임",
        "category": "plastic_surgery",
    },
    {
        "name": "코성형(아시안)",
        "query": "(rhinoplasty[Title/Abstract]) AND (Asian OR augmentation[Title/Abstract]) AND (silicone OR cartilage[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "코성형",
        "category": "plastic_surgery",
    },
    {
        "name": "코재수술",
        "query": "(revision rhinoplasty[Title/Abstract]) AND (complication OR outcome[Title/Abstract])",
        "procedure": "코재수술",
        "category": "plastic_surgery",
    },
    {
        "name": "코끝/콧볼",
        "query": "(nasal tip OR tip plasty OR alar reduction[Title/Abstract]) AND (Asian[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "코끝성형/콧볼축소",
        "category": "plastic_surgery",
    },
    {
        "name": "사각턱축소",
        "query": "(mandible reduction OR V-line[Title/Abstract]) AND (Korean OR Asian[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "사각턱축소",
        "category": "plastic_surgery",
    },
    {
        "name": "광대축소",
        "query": "(zygoma reduction OR malar reduction[Title/Abstract]) AND (Korean OR Asian[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "광대축소",
        "category": "plastic_surgery",
    },
    {
        "name": "턱끝수술",
        "query": "(genioplasty OR chin surgery OR sliding[Title/Abstract]) AND (aesthetic[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "턱끝수술",
        "category": "plastic_surgery",
    },
    {
        "name": "양악수술",
        "query": "(orthognathic OR bimaxillary OR two-jaw[Title/Abstract]) AND (aesthetic[Title/Abstract]) AND (Korean OR Asian[Title/Abstract])",
        "procedure": "양악수술",
        "category": "plastic_surgery",
    },
    {
        "name": "안면거상",
        "query": "(facelift OR rhytidectomy OR SMAS[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "안면거상(페이스리프트)",
        "category": "plastic_surgery",
    },
    {
        "name": "이마거상",
        "query": "(forehead lift OR brow lift OR endoscopic[Title/Abstract]) AND (aesthetic[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "이마거상(브로우리프트)",
        "category": "plastic_surgery",
    },
    {
        "name": "지방이식(얼굴)",
        "query": "(fat grafting OR lipofilling[Title/Abstract]) AND (face[Title/Abstract]) AND (survival rate OR satisfaction[Title/Abstract])",
        "procedure": "지방이식(얼굴)",
        "category": "plastic_surgery",
    },
    {
        "name": "지방흡입",
        "query": "(liposuction OR body contouring[Title/Abstract]) AND (aesthetic[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "지방흡입",
        "category": "plastic_surgery",
    },
    {
        "name": "가슴확대",
        "query": "(breast augmentation[Title/Abstract]) AND (implant[Title/Abstract]) AND (satisfaction OR QoL[Title/Abstract])",
        "procedure": "가슴확대",
        "category": "plastic_surgery",
    },
]

ALL_QUERIES = DERMATOLOGY_QUERIES + PLASTIC_SURGERY_QUERIES


# ============================================
# STEP 1: PubMed 논문 수집
# ============================================
def fetch_pubmed_articles():
    """PubMed에서 34개 카테고리 논문 수집 -> pubmed_articles 테이블에 저장."""
    db = get_supabase()

    # pubmed_articles 테이블 대신 기존 youtube_sources를 재사용하지 않고
    # 별도 임시 저장소(메모리)에 수집 후 바로 FAQ 변환
    # -> 실제로는 DB에 중간 저장하여 재시작 가능하게

    total_collected = 0
    all_articles = []
    seen_pmids = set()

    # 이미 DB에 있는 PubMed PMID 확인 (중복 방지)
    existing = _db_retry(lambda: db.table("faq_vectors")
        .select("youtube_video_id")
        .like("youtube_url", "%pubmed.ncbi.nlm.nih.gov%")
        .execute()
    )
    for row in existing.data:
        if row.get("youtube_video_id"):
            seen_pmids.add(row["youtube_video_id"])
    _safe_print(f"  Already in DB: {len(seen_pmids)} PubMed PMIDs\n")

    for qi, q in enumerate(ALL_QUERIES):
        _safe_print(f"  [{qi+1}/{len(ALL_QUERIES)}] {q['name']} ({q['category']})")

        try:
            # ESearch
            handle = Entrez.esearch(
                db="pubmed",
                term=q["query"],
                retmax=30,
                sort="relevance",
                mindate="2015",
                maxdate="2025",
                datetype="pdat",
            )
            search_results = Entrez.read(handle)
            handle.close()
            time.sleep(_REQ_DELAY)

            id_list = search_results.get("IdList", [])
            if not id_list:
                _safe_print(f"    -> 0 results")
                continue

            # 중복 제거
            new_ids = [pid for pid in id_list if pid not in seen_pmids]
            if not new_ids:
                _safe_print(f"    -> {len(id_list)} results, all duplicates")
                continue

            # EFetch (초록 포함)
            handle = Entrez.efetch(
                db="pubmed",
                id=",".join(new_ids),
                rettype="xml",
                retmode="xml",
            )
            records = Entrez.read(handle)
            handle.close()
            time.sleep(_REQ_DELAY)

            articles = records.get("PubmedArticle", [])
            count = 0

            for article in articles:
                try:
                    medline = article.get("MedlineCitation", {})
                    pmid = str(medline.get("PMID", ""))
                    if pmid in seen_pmids:
                        continue

                    art_data = medline.get("Article", {})
                    title = str(art_data.get("ArticleTitle", ""))

                    # 초록 추출
                    abstract_parts = art_data.get("Abstract", {}).get("AbstractText", [])
                    if not abstract_parts:
                        continue  # 초록 없으면 스킵

                    abstract = " ".join(str(p) for p in abstract_parts)
                    if len(abstract) < 50:
                        continue

                    # 저널명
                    journal_info = art_data.get("Journal", {})
                    journal = str(journal_info.get("Title", ""))
                    if not journal:
                        journal = str(journal_info.get("ISOAbbreviation", ""))

                    # 출판연도
                    pub_date = art_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
                    pub_year = str(pub_date.get("Year", ""))
                    if not pub_year:
                        medline_date = pub_date.get("MedlineDate", "")
                        if medline_date:
                            year_match = re.search(r"(\d{4})", str(medline_date))
                            if year_match:
                                pub_year = year_match.group(1)

                    seen_pmids.add(pmid)
                    all_articles.append({
                        "pmid": pmid,
                        "title": title,
                        "abstract": abstract,
                        "journal": journal,
                        "pub_year": pub_year,
                        "procedure": q["procedure"],
                        "category": q["category"],
                        "query_name": q["name"],
                    })
                    count += 1

                except Exception as e:
                    _safe_print(f"    -> parse error: {str(e)[:80]}")
                    continue

            total_collected += count
            _safe_print(f"    -> {count} new articles (total: {total_collected})")

        except Exception as e:
            _safe_print(f"    -> search error: {str(e)[:100]}")
            time.sleep(2)
            continue

        time.sleep(_REQ_DELAY * 2)

    _safe_print(f"\n  Total collected: {total_collected} articles (unique PMIDs)")

    # 로컬 JSON 파일로 저장 (재시작 시 사용)
    output_path = os.path.join(os.path.dirname(__file__), "pubmed_articles.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)
    _safe_print(f"  Saved to: {output_path}")

    return all_articles


# ============================================
# STEP 2: Gemini로 FAQ 변환
# ============================================
FAQ_PROMPT_TEMPLATE = """아래는 의료 논문의 제목과 초록입니다. 이 논문에서 한국어 FAQ(질문-답변)을 **2~4개** 생성해주세요.

**시술명**: {procedure}
**카테고리**: {category_kr}
**논문 제목**: {title}
**저널**: {journal} ({pub_year})

**초록**:
{abstract}

**FAQ 작성 규칙:**
1. 질문에 시술명을 포함하세요 (예: "보톡스 사각턱 치료 효과가 있나요?")
2. 답변에 구체적 수치를 반드시 포함하세요 (만족도 %, 효과 수치, 지속기간, 부작용률 등)
3. 답변 끝에 (출처: {journal}, {pub_year}) 형태로 출처를 표기하세요
4. 부작용/주의사항이 언급된 경우 반드시 포함하세요
5. 영어 시술명은 한국어로 변환하세요:
   - HIFU → 울쎄라
   - botulinum toxin → 보톡스
   - hyaluronic acid filler → 히알루론산 필러
   - radiofrequency → 고주파(써마지)
   - thread lift → 실리프팅
   - rhinoplasty → 코성형
   - blepharoplasty → 눈성형/쌍꺼풀수술
   - liposuction → 지방흡입
   - etc.
6. 답변은 2~3문장으로 간결하되 핵심 수치는 빠짐없이 포함

**출력 형식 (JSON 배열만, 마크다운 없이):**
[
  {{"question": "...", "answer": "..."}},
  {{"question": "...", "answer": "..."}}
]
"""

CATEGORY_KR = {
    "dermatology": "피부과 미용시술",
    "plastic_surgery": "성형외과 수술",
}


def generate_pubmed_faqs(articles: list[dict] | None = None):
    """수집된 논문을 Gemini로 한국어 FAQ 변환."""
    db = get_supabase()

    # articles가 없으면 JSON 파일에서 로드
    if articles is None:
        json_path = os.path.join(os.path.dirname(__file__), "pubmed_articles.json")
        if not os.path.exists(json_path):
            _safe_print("  No articles found. Run step 1 first.")
            return []
        with open(json_path, "r", encoding="utf-8") as f:
            articles = json.load(f)

    if not articles:
        _safe_print("  No articles to process.")
        return []

    # 이미 DB에 있는 PMID 확인
    existing = _db_retry(lambda: db.table("faq_vectors")
        .select("youtube_video_id")
        .like("youtube_url", "%pubmed.ncbi.nlm.nih.gov%")
        .execute()
    )
    existing_pmids = {row["youtube_video_id"] for row in existing.data if row.get("youtube_video_id")}

    # 미처리 논문만 필터
    pending = [a for a in articles if a["pmid"] not in existing_pmids]
    _safe_print(f"\n  FAQ generation: {len(pending)} articles pending (skipping {len(articles) - len(pending)} already done)")

    all_faqs = []
    success = 0
    failed = 0

    for i, article in enumerate(pending):
        pmid = article["pmid"]
        title_short = article["title"][:60]
        _safe_print(f"  [{i+1}/{len(pending)}] PMID:{pmid} {title_short}...")

        prompt = FAQ_PROMPT_TEMPLATE.format(
            procedure=article["procedure"],
            category_kr=CATEGORY_KR.get(article["category"], article["category"]),
            title=article["title"],
            journal=article["journal"],
            pub_year=article["pub_year"],
            abstract=article["abstract"][:3000],  # 토큰 제한 방지
        )

        # Gemini 호출
        time.sleep(5)  # 15RPM 제한 고려
        result = _gemini_call(prompt)

        if not result:
            _safe_print(f"    -> empty response")
            failed += 1
            continue

        # JSON 파싱
        try:
            # 마크다운 코드블록 제거
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            faqs = json.loads(cleaned)
            if not isinstance(faqs, list):
                raise ValueError("Not a list")

        except (json.JSONDecodeError, ValueError) as e:
            _safe_print(f"    -> JSON parse error: {str(e)[:60]}")
            # 재시도 1회
            time.sleep(5)
            result2 = _gemini_call(prompt + "\n\n반드시 순수 JSON 배열만 출력하세요. ```나 설명 없이.")
            if result2:
                try:
                    cleaned2 = result2.strip()
                    if cleaned2.startswith("```"):
                        cleaned2 = re.sub(r"^```(?:json)?\s*", "", cleaned2)
                        cleaned2 = re.sub(r"\s*```$", "", cleaned2)
                    faqs = json.loads(cleaned2)
                    if not isinstance(faqs, list):
                        raise ValueError("Not a list")
                except Exception:
                    _safe_print(f"    -> retry also failed, skipping")
                    failed += 1
                    continue
            else:
                failed += 1
                continue

        # FAQ를 faq_vectors에 저장 (임베딩은 step 3에서)
        valid_faqs = []
        for faq in faqs:
            q = faq.get("question", "").strip()
            a = faq.get("answer", "").strip()
            if q and a and len(q) > 5 and len(a) > 10:
                valid_faqs.append({
                    "question": q,
                    "answer": a,
                    "procedure_name": article["procedure"],
                    "category": article["category"],
                    "youtube_video_id": pmid,  # PMID 저장
                    "youtube_title": article["title"][:200],
                    "youtube_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                })

        if valid_faqs:
            try:
                # 임베딩 없이 저장 (step 3에서 처리)
                # faq_vectors는 embedding NOT NULL이므로 더미 벡터 넣기
                dummy_vec = [0.0] * 768
                for faq in valid_faqs:
                    faq["embedding"] = dummy_vec

                _db_retry(lambda vf=valid_faqs: db.table("faq_vectors").insert(vf).execute())
                success += 1
                all_faqs.extend(valid_faqs)
                _safe_print(f"    -> {len(valid_faqs)} FAQs saved")
            except Exception as e:
                _safe_print(f"    -> DB save error: {str(e)[:100]}")
                failed += 1
        else:
            _safe_print(f"    -> no valid FAQs extracted")
            failed += 1

    _safe_print(f"\n  FAQ done: {success} articles -> {len(all_faqs)} FAQs (failed: {failed})")
    return all_faqs


# ============================================
# STEP 3: 임베딩 생성 + 업데이트
# ============================================
def embed_pubmed_faqs():
    """PubMed FAQ의 더미 임베딩을 실제 Gemini Embedding으로 교체."""
    db = get_supabase()

    # 페이지네이션으로 전체 PubMed FAQ 가져오기 (Supabase 기본 1000행 제한 우회)
    faqs = []
    page_size = 1000
    offset = 0
    while True:
        page = _db_retry(lambda o=offset: db.table("faq_vectors")
            .select("id, question, answer, procedure_name")
            .like("youtube_url", "%pubmed.ncbi.nlm.nih.gov%")
            .range(o, o + page_size - 1)
            .execute()
        )
        if not page.data:
            break
        faqs.extend(page.data)
        if len(page.data) < page_size:
            break
        offset += page_size

    if not faqs:
        _safe_print("  No PubMed FAQs found.")
        return
    total = len(faqs)
    _safe_print(f"\n  Embedding {total} PubMed FAQs...")

    success = 0
    failed = 0

    # 배치 처리 (Gemini Embedding은 배치 가능)
    BATCH_SIZE = 20

    for batch_start in range(0, total, BATCH_SIZE):
        batch = faqs[batch_start:batch_start + BATCH_SIZE]
        texts = [f"{f['question']} {f['answer']}" for f in batch]

        try:
            time.sleep(2)  # Rate limit
            result = _gemini_client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=texts,
                config=types.EmbedContentConfig(
                    output_dimensionality=768,
                ),
            )

            embeddings = result.embeddings

            for j, faq in enumerate(batch):
                vec = embeddings[j].values
                try:
                    _db_retry(lambda fid=faq["id"], v=vec: (
                        db.table("faq_vectors")
                        .update({"embedding": v})
                        .eq("id", fid)
                        .execute()
                    ))
                    success += 1
                except Exception as e:
                    _safe_print(f"    -> DB update error: {str(e)[:80]}")
                    failed += 1

            _safe_print(f"    -> batch {batch_start+1}-{batch_start+len(batch)}/{total} done")

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                _safe_print(f"    -> Rate limited, waiting 60s...")
                time.sleep(60)
                # 재시도: 개별 처리
                for faq in batch:
                    try:
                        time.sleep(3)
                        text = f"{faq['question']} {faq['answer']}"
                        r = _gemini_client.models.embed_content(
                            model="models/gemini-embedding-001",
                            contents=[text],
                            config=types.EmbedContentConfig(
                                output_dimensionality=768,
                            ),
                        )
                        vec = r.embeddings[0].values
                        _db_retry(lambda fid=faq["id"], v=vec: (
                            db.table("faq_vectors")
                            .update({"embedding": v})
                            .eq("id", fid)
                            .execute()
                        ))
                        success += 1
                    except Exception as e2:
                        _safe_print(f"    -> embed error: {str(e2)[:60]}")
                        failed += 1
            else:
                _safe_print(f"    -> embed batch error: {err_str[:100]}")
                failed += len(batch)

    _safe_print(f"\n  Embedding done: {success} success / {failed} failed / {total} total")


# ============================================
# 통계
# ============================================
def print_stats():
    db = get_supabase()

    # YouTube FAQ 수
    yt_faqs = _db_retry(lambda: db.table("faq_vectors")
        .select("id", count="exact")
        .not_.like("youtube_url", "%pubmed.ncbi.nlm.nih.gov%")
        .execute()
    )

    # PubMed FAQ 수
    pm_faqs = _db_retry(lambda: db.table("faq_vectors")
        .select("id", count="exact")
        .like("youtube_url", "%pubmed.ncbi.nlm.nih.gov%")
        .execute()
    )

    # PubMed 카테고리별
    pm_derm = _db_retry(lambda: db.table("faq_vectors")
        .select("id", count="exact")
        .like("youtube_url", "%pubmed.ncbi.nlm.nih.gov%")
        .eq("category", "dermatology")
        .execute()
    )
    pm_ps = _db_retry(lambda: db.table("faq_vectors")
        .select("id", count="exact")
        .like("youtube_url", "%pubmed.ncbi.nlm.nih.gov%")
        .eq("category", "plastic_surgery")
        .execute()
    )

    total = (yt_faqs.count or 0) + (pm_faqs.count or 0)

    _safe_print(f"\n{'=' * 50}")
    _safe_print(f"  벡터DB FAQ 통계")
    _safe_print(f"{'=' * 50}")
    _safe_print(f"  [YouTube]")
    _safe_print(f"    FAQ 수: {yt_faqs.count}")
    _safe_print(f"  [PubMed]")
    _safe_print(f"    피부과: {pm_derm.count}")
    _safe_print(f"    성형외과: {pm_ps.count}")
    _safe_print(f"    소계: {pm_faqs.count}")
    _safe_print(f"  총 FAQ 벡터: {total}")
    _safe_print(f"{'=' * 50}\n")

    # JSON 파일 통계
    json_path = os.path.join(os.path.dirname(__file__), "pubmed_articles.json")
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            articles = json.load(f)
        _safe_print(f"  수집된 논문 (로컬): {len(articles)}건")
    else:
        _safe_print(f"  수집된 논문 (로컬): 없음 (step 1 미실행)")


# ============================================
# 메인
# ============================================
def run_pipeline(step: int | None = None):
    if step == 1 or step is None:
        _safe_print(f"\n{'=' * 50}")
        _safe_print(f"  STEP 1: PubMed 논문 수집")
        _safe_print(f"{'=' * 50}\n")
        articles = fetch_pubmed_articles()

        if step == 1:
            return

    if step == 2 or step is None:
        _safe_print(f"\n{'=' * 50}")
        _safe_print(f"  STEP 2: FAQ 변환 (Gemini)")
        _safe_print(f"{'=' * 50}\n")
        generate_pubmed_faqs(articles if step is None else None)

    if step == 3 or step is None:
        _safe_print(f"\n{'=' * 50}")
        _safe_print(f"  STEP 3: 임베딩 (Gemini Embedding)")
        _safe_print(f"{'=' * 50}\n")
        embed_pubmed_faqs()

    if step is None:
        print_stats()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PubMed -> 벡터DB 파이프라인")
    parser.add_argument("--step", type=int, choices=[1, 2, 3], help="실행할 단계 (1-3)")
    parser.add_argument("--stats", action="store_true", help="현재 통계만 출력")
    args = parser.parse_args()

    if args.stats:
        print_stats()
    else:
        run_pipeline(args.step)
