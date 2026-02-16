"""
보충 PubMed 논문 수집 + FAQ 변환 + 임베딩.
탈모/두피치료, 턱끝성형 등 부족한 주제를 보강.

사용법:
  cd backend
  python -m scripts.add_pubmed_supplement
"""
import json
import os
import re
import sys
import time

from Bio import Entrez
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, NCBI_API_KEY, NCBI_EMAIL, NCBI_TOOL
from services.supabase_client import get_supabase


def _safe_print(msg: str):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"), flush=True)


# ============================================
# Entrez 설정
# ============================================
Entrez.email = NCBI_EMAIL
Entrez.tool = NCBI_TOOL
if NCBI_API_KEY:
    Entrez.api_key = NCBI_API_KEY

_REQ_DELAY = 0.15 if NCBI_API_KEY else 0.4

# ============================================
# Gemini Client
# ============================================
_gemini = genai.Client(api_key=GEMINI_API_KEY)


# ============================================
# 보충 검색 쿼리
# ============================================
SUPPLEMENT_QUERIES = [
    # === 탈모/두피 치료 (dermatology) ===
    {
        "name": "여성형 탈모(미녹시딜)",
        "query": "(female pattern hair loss OR female androgenetic alopecia[Title/Abstract]) AND (minoxidil[Title/Abstract]) AND (efficacy OR outcome[Title/Abstract])",
        "procedure": "여성형 탈모치료(미녹시딜)",
        "category": "dermatology",
    },
    {
        "name": "탈모 PRP",
        "query": "(platelet-rich plasma OR PRP[Title/Abstract]) AND (alopecia OR hair loss[Title/Abstract]) AND (efficacy OR outcome[Title/Abstract])",
        "procedure": "탈모 PRP치료",
        "category": "dermatology",
    },
    {
        "name": "탈모 메조테라피",
        "query": "(mesotherapy[Title/Abstract]) AND (alopecia OR hair loss OR hair growth[Title/Abstract]) AND (efficacy OR outcome[Title/Abstract])",
        "procedure": "육모 메조테라피",
        "category": "dermatology",
    },
    {
        "name": "두피 LLLT(저출력레이저)",
        "query": "(low-level laser therapy OR LLLT OR photobiomodulation[Title/Abstract]) AND (alopecia OR hair loss OR hair growth[Title/Abstract]) AND (efficacy[Title/Abstract])",
        "procedure": "두피 레이저치료(LLLT)",
        "category": "dermatology",
    },
    {
        "name": "PDRN/리쥬란 헤어",
        "query": "(PDRN OR polynucleotide[Title/Abstract]) AND (hair OR scalp OR alopecia[Title/Abstract]) AND (efficacy OR growth[Title/Abstract])",
        "procedure": "리쥬란 헤어(PDRN)",
        "category": "dermatology",
    },
    {
        "name": "출산후 탈모",
        "query": "(postpartum alopecia OR telogen effluvium[Title/Abstract]) AND (treatment OR management[Title/Abstract])",
        "procedure": "출산후 탈모치료",
        "category": "dermatology",
    },
    {
        "name": "여성 탈모 종합",
        "query": "(female hair loss OR female alopecia[Title/Abstract]) AND (treatment[Title/Abstract]) AND (review OR systematic[Title/Abstract])",
        "procedure": "여성 탈모치료",
        "category": "dermatology",
    },
    # === 턱끝/V라인 (plastic_surgery) - 보강 ===
    {
        "name": "턱끝 필러",
        "query": "(chin augmentation OR chin filler[Title/Abstract]) AND (hyaluronic acid[Title/Abstract]) AND (satisfaction OR outcome[Title/Abstract])",
        "procedure": "턱끝 필러",
        "category": "plastic_surgery",
    },
    {
        "name": "V라인 복합시술",
        "query": "(V-line OR facial contouring[Title/Abstract]) AND (mandible OR chin[Title/Abstract]) AND (botulinum OR filler OR surgery[Title/Abstract]) AND (Korean OR Asian[Title/Abstract])",
        "procedure": "V라인 복합시술",
        "category": "plastic_surgery",
    },
]

CATEGORY_KR = {
    "dermatology": "피부과 미용시술",
    "plastic_surgery": "성형외과 수술",
}

FAQ_PROMPT = """아래는 의료 논문의 제목과 초록입니다. 이 논문에서 한국어 FAQ(질문-답변)을 **2~4개** 생성해주세요.

**시술명**: {procedure}
**카테고리**: {category_kr}
**논문 제목**: {title}
**저널**: {journal} ({pub_year})

**초록**:
{abstract}

**FAQ 작성 규칙:**
1. 질문에 시술명을 포함하세요 (예: "PRP 탈모 치료 효과가 있나요?")
2. 답변에 구체적 수치를 반드시 포함하세요 (만족도 %, 효과 수치, 지속기간, 부작용률 등)
3. 답변 끝에 (출처: {journal}, {pub_year}) 형태로 출처를 표기하세요
4. 부작용/주의사항이 언급된 경우 반드시 포함하세요
5. 영어 시술명은 한국어로 변환하세요:
   - PRP → PRP(자가혈소판풍부혈장)
   - LLLT → 저출력 레이저 치료
   - mesotherapy → 메조테라피
   - minoxidil → 미녹시딜
   - PDRN → PDRN(폴리데옥시리보뉴클레오티드)
6. 답변은 2~3문장으로 간결하되 핵심 수치는 빠짐없이 포함

**출력 형식 (JSON 배열만, 마크다운 없이):**
[
  {{"question": "...", "answer": "..."}},
  {{"question": "...", "answer": "..."}}
]
"""


def _gemini_call(prompt: str, max_retries: int = 5) -> str:
    for attempt in range(max_retries):
        try:
            response = _gemini.models.generate_content(
                model="gemini-2.0-flash",
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
            else:
                _safe_print(f"    -> Gemini error: {err_str[:120]}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                else:
                    return ""
    return ""


def main():
    db = get_supabase()

    # 이미 DB에 있는 PubMed PMID 확인
    existing_pmids = set()
    offset = 0
    while True:
        page = db.table("faq_vectors") \
            .select("youtube_video_id") \
            .like("youtube_url", "%pubmed.ncbi.nlm.nih.gov%") \
            .range(offset, offset + 999) \
            .execute()
        for row in page.data:
            if row.get("youtube_video_id"):
                existing_pmids.add(row["youtube_video_id"])
        if len(page.data) < 1000:
            break
        offset += 1000

    _safe_print(f"기존 PubMed PMID: {len(existing_pmids)}건\n")

    # ---- STEP 1: 논문 수집 ----
    all_articles = []

    for qi, q in enumerate(SUPPLEMENT_QUERIES):
        _safe_print(f"[{qi+1}/{len(SUPPLEMENT_QUERIES)}] {q['name']} ({q['category']})")

        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=q["query"],
                retmax=20,
                sort="relevance",
                mindate="2015",
                maxdate="2025",
                datetype="pdat",
            )
            search_results = Entrez.read(handle)
            handle.close()
            time.sleep(_REQ_DELAY)

            id_list = search_results.get("IdList", [])
            new_ids = [pid for pid in id_list if pid not in existing_pmids]

            if not new_ids:
                _safe_print(f"  -> {len(id_list)} results, all duplicates")
                continue

            handle = Entrez.efetch(
                db="pubmed",
                id=",".join(new_ids[:15]),  # 쿼리당 최대 15개
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
                    if pmid in existing_pmids:
                        continue

                    art_data = medline.get("Article", {})
                    title = str(art_data.get("ArticleTitle", ""))

                    abstract_parts = art_data.get("Abstract", {}).get("AbstractText", [])
                    if not abstract_parts:
                        continue

                    abstract = " ".join(str(p) for p in abstract_parts)
                    if len(abstract) < 50:
                        continue

                    journal_info = art_data.get("Journal", {})
                    journal = str(journal_info.get("Title", ""))
                    if not journal:
                        journal = str(journal_info.get("ISOAbbreviation", ""))

                    pub_date = journal_info.get("JournalIssue", {}).get("PubDate", {})
                    pub_year = str(pub_date.get("Year", ""))
                    if not pub_year:
                        md = pub_date.get("MedlineDate", "")
                        if md:
                            ym = re.search(r"(\d{4})", str(md))
                            if ym:
                                pub_year = ym.group(1)

                    existing_pmids.add(pmid)
                    all_articles.append({
                        "pmid": pmid,
                        "title": title,
                        "abstract": abstract,
                        "journal": journal,
                        "pub_year": pub_year,
                        "procedure": q["procedure"],
                        "category": q["category"],
                    })
                    count += 1
                except Exception as e:
                    _safe_print(f"    -> parse error: {str(e)[:80]}")

            _safe_print(f"  -> {count} new articles")

        except Exception as e:
            _safe_print(f"  -> search error: {str(e)[:100]}")
            time.sleep(2)

        time.sleep(_REQ_DELAY * 2)

    _safe_print(f"\n수집 완료: {len(all_articles)}건\n")

    if not all_articles:
        _safe_print("수집된 논문이 없습니다.")
        return

    # ---- STEP 2: FAQ 변환 + 임베딩 + DB 저장 ----
    total_faqs = 0
    failed = 0

    for i, article in enumerate(all_articles):
        pmid = article["pmid"]
        _safe_print(f"[{i+1}/{len(all_articles)}] PMID:{pmid} {article['title'][:50]}...")

        # FAQ 생성
        prompt = FAQ_PROMPT.format(
            procedure=article["procedure"],
            category_kr=CATEGORY_KR.get(article["category"], article["category"]),
            title=article["title"],
            journal=article["journal"],
            pub_year=article["pub_year"],
            abstract=article["abstract"][:3000],
        )

        time.sleep(4)
        result = _gemini_call(prompt)
        if not result:
            _safe_print("    -> empty response")
            failed += 1
            continue

        # JSON 파싱
        try:
            cleaned = result.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            faqs = json.loads(cleaned)
            if not isinstance(faqs, list):
                raise ValueError("Not a list")
        except (json.JSONDecodeError, ValueError):
            _safe_print("    -> JSON parse error, retrying...")
            time.sleep(4)
            result2 = _gemini_call(prompt + "\n\n반드시 순수 JSON 배열만 출력하세요.")
            if result2:
                try:
                    c2 = result2.strip()
                    if c2.startswith("```"):
                        c2 = re.sub(r"^```(?:json)?\s*", "", c2)
                        c2 = re.sub(r"\s*```$", "", c2)
                    faqs = json.loads(c2)
                except Exception:
                    failed += 1
                    continue
            else:
                failed += 1
                continue

        # 유효한 FAQ 필터
        valid_faqs = []
        for faq in faqs:
            q = faq.get("question", "").strip()
            a = faq.get("answer", "").strip()
            if q and a and len(q) > 5 and len(a) > 10:
                valid_faqs.append({"question": q, "answer": a})

        if not valid_faqs:
            _safe_print("    -> no valid FAQs")
            failed += 1
            continue

        # 임베딩 생성
        texts = [f"{f['question']} {f['answer']}" for f in valid_faqs]
        try:
            time.sleep(2)
            embed_result = _gemini.models.embed_content(
                model="models/gemini-embedding-001",
                contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=768),
            )
            embeddings = embed_result.embeddings
        except Exception as e:
            _safe_print(f"    -> embedding error: {str(e)[:80]}")
            failed += 1
            continue

        # DB 저장
        rows = []
        for j, faq in enumerate(valid_faqs):
            rows.append({
                "category": article["category"],
                "question": faq["question"],
                "answer": faq["answer"],
                "procedure_name": article["procedure"],
                "youtube_video_id": pmid,
                "youtube_title": article["title"][:200],
                "youtube_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "embedding": embeddings[j].values,
            })

        try:
            db.table("faq_vectors").insert(rows).execute()
            total_faqs += len(rows)
            _safe_print(f"    -> {len(rows)} FAQs saved")
        except Exception as e:
            _safe_print(f"    -> DB error: {str(e)[:80]}")
            failed += 1

    _safe_print(f"\n{'=' * 50}")
    _safe_print(f"  완료: {total_faqs} FAQs 추가 (실패: {failed})")
    _safe_print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
