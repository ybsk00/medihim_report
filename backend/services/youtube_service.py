import json
import time
import re

import google.generativeai as genai
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

from config import YOUTUBE_API_KEY, GEMINI_API_KEY
from services.supabase_client import get_supabase


# ============================================
# 유틸: Windows cp949 안전 출력
# ============================================
def _safe_print(msg: str):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"), flush=True)


# ============================================
# 초기화
# ============================================
genai.configure(api_key=GEMINI_API_KEY)
_llm = genai.GenerativeModel("gemini-2.5-flash")
_embedding_model = "models/gemini-embedding-001"


def _get_youtube():
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


def _db_retry(func, max_retries=3):
    """Supabase DB 작업 재시도 래퍼. 네트워크/서버 오류 시 자동 재시도."""
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


def _gemini_call_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Gemini API 호출 + 429/500 자동 재시도"""
    for attempt in range(max_retries):
        try:
            response = _llm.generate_content(prompt)
            return response.text
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = 30 * (attempt + 1)
                _safe_print(f"    -> Rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif "500" in err_str or "503" in err_str:
                wait = 10 * (attempt + 1)
                _safe_print(f"    -> Server error, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception(f"Max retries exceeded")


# ============================================
# 유틸리티 (기존 API용)
# ============================================
def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _get_transcript_api():
    """쿠키 파일이 있으면 쿠키 기반 세션 사용 (IP 차단 우회)"""
    import os
    cookie_path = os.path.join(os.path.dirname(__file__), "..", "cookies.txt")
    if os.path.exists(cookie_path):
        import http.cookiejar
        import requests as req
        jar = http.cookiejar.MozillaCookieJar(cookie_path)
        jar.load(ignore_discard=True, ignore_expires=True)
        session = req.Session()
        session.cookies = jar
        return YouTubeTranscriptApi(http_client=session)
    return YouTubeTranscriptApi()


def fetch_transcript(video_id: str, korean_only: bool = False) -> str | None:
    """youtube-transcript-api v1.x 대응 (쿠키 지원).
    한국어 → 영어 → 일본어 → 자동생성자막 순서로 폴백.
    korean_only=True: 한국어 자막만 (기존 API 호환용).
    backend/cookies.txt 파일이 있으면 자동으로 쿠키 사용 (IP 차단 우회).
    """
    api = _get_transcript_api()
    if korean_only:
        langs = ["ko"]
    else:
        langs = ["ko", "en", "ja"]

    try:
        # 1) 수동/자동 자막을 언어 순서대로 시도
        for lang in langs:
            try:
                result = api.fetch(video_id, languages=[lang])
                text = " ".join(entry.text for entry in result)
                if text and len(text) > 20:
                    return text
            except Exception:
                continue

        # 2) 어떤 언어든 자동 생성 자막이 있으면 가져오기
        if not korean_only:
            try:
                transcript_list = api.list(video_id)
                for t in transcript_list:
                    try:
                        result = t.fetch()
                        text = " ".join(entry.text for entry in result)
                        if text and len(text) > 20:
                            return text
                    except Exception:
                        continue
            except Exception:
                pass

        return None
    except Exception:
        return None


# ============================================
# 핸들 → 채널 ID 변환
# ============================================
def resolve_handle_to_channel_id(handle: str) -> str | None:
    youtube = _get_youtube()
    clean_handle = handle.lstrip("@")

    # channels.list with forHandle costs 1 quota unit (vs search 100 units)
    try:
        response = (
            youtube.channels()
            .list(part="id", forHandle=clean_handle)
            .execute()
        )
        if response.get("items"):
            return response["items"][0]["id"]
    except Exception:
        pass

    # fallback: search API (100 units)
    try:
        response = (
            youtube.search()
            .list(part="snippet", q=clean_handle, type="channel", maxResults=1)
            .execute()
        )
        if response.get("items"):
            return response["items"][0]["snippet"]["channelId"]
    except Exception:
        pass

    return None


# ============================================
# STEP 1: 채널 영상 수집
# ============================================
def fetch_channel_videos(channel_id: str, category: str, channel_name: str) -> int:
    youtube = _get_youtube()
    db = get_supabase()
    next_page_token = None
    total_fetched = 0

    # uploads playlist: UC... -> UU...  (1 quota unit vs search 100 units)
    uploads_playlist_id = "UU" + channel_id[2:]

    while True:
        request_params = {
            "part": "snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": 50,
        }
        if next_page_token:
            request_params["pageToken"] = next_page_token

        response = youtube.playlistItems().list(**request_params).execute()

        for item in response.get("items", []):
            video_id = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]

            # 오프라이드 채널: 의료 콘텐츠만 필터링 (브이로그 등 제외)
            if channel_id == "UC8av1CNslnPQS3N08rkzzhQ":
                medical_keywords = [
                    "피부", "시술", "레이저", "여드름", "기미", "색소", "모공",
                    "탈모", "하이푸", "울쎄라", "보톡스", "필러", "리쥬란",
                    "스킨", "주름", "탄력", "리프팅", "토닝", "필링",
                    "클리닉", "치료", "진료", "성분", "화장품", "자외선",
                ]
                title_lower = title.lower()
                if not any(kw in title_lower for kw in medical_keywords):
                    continue

            # 중복 체크 + 삽입 (Supabase 일시 오류 재시도)
            for retry in range(3):
                try:
                    existing = (
                        db.table("youtube_sources")
                        .select("id")
                        .eq("video_id", video_id)
                        .execute()
                    )

                    if not existing.data:
                        db.table("youtube_sources").insert(
                            {
                                "video_id": video_id,
                                "title": title,
                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                "channel_name": channel_name,
                                "category": category,
                                "status": "pending",
                            }
                        ).execute()
                        total_fetched += 1
                    break
                except Exception as e:
                    if retry < 2:
                        time.sleep(5 * (retry + 1))
                    else:
                        _safe_print(f"    -> DB error, skip {video_id}: {str(e)[:80]}")

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

        time.sleep(0.5)

    _safe_print(f"  [{channel_name}] {total_fetched} videos collected")
    return total_fetched


def fetch_all_channels():
    from config import TARGET_CHANNELS

    db = get_supabase()
    total = 0
    for ch in TARGET_CHANNELS:
        # 이미 수집된 채널은 스킵
        existing = db.table("youtube_sources").select("id", count="exact").eq("channel_name", ch["name"]).execute()
        if existing.count and existing.count > 0:
            _safe_print(f"  [{ch['name']}] already {existing.count} videos, skipping")
            continue

        channel_id = ch["channel_id"]

        if not channel_id and ch.get("handle"):
            channel_id = resolve_handle_to_channel_id(ch["handle"])
            if channel_id:
                _safe_print(f"  [{ch['name']}] handle {ch['handle']} -> {channel_id}")
            else:
                _safe_print(f"  [{ch['name']}] handle not found, skipping")
                continue

        total += fetch_channel_videos(channel_id, ch["category"], ch["name"])

    _safe_print(f"\n  Total {total} videos collected")


# ============================================
# STEP 2: 자막 추출 (한국어 + 영어 폴백)
# ============================================
def extract_all_transcripts():
    db = get_supabase()
    pending = _db_retry(
        lambda: db.table("youtube_sources").select("*").eq("status", "pending").execute()
    )

    total = len(pending.data)
    success = 0
    skipped = 0
    consecutive_errors = 0
    BATCH_SIZE = 20  # 20건마다 긴 휴식

    for i, video in enumerate(pending.data):
        video_id = video["video_id"]
        _safe_print(f"  [{i + 1}/{total}] transcript: {video['title'][:60]}...")

        try:
            transcript = fetch_transcript(video_id, korean_only=False)

            # 숏폼도 살리기 위해 최소 길이를 20자로 낮춤
            if transcript and len(transcript) > 20:
                _db_retry(lambda v=video_id, t=transcript: (
                    db.table("youtube_sources").update(
                        {"raw_transcript": t, "status": "transcript_fetched"}
                    ).eq("video_id", v).execute()
                ))
                success += 1
                consecutive_errors = 0
            else:
                _db_retry(lambda v=video_id: (
                    db.table("youtube_sources").update({"status": "skipped"}).eq(
                        "video_id", v
                    ).execute()
                ))
                skipped += 1
                consecutive_errors = 0
        except Exception as e:
            err_str = str(e).lower()
            # IP 차단 감지
            if "ipblocked" in err_str or "ip" in err_str and "block" in err_str:
                _safe_print(f"    -> IP BLOCKED! Waiting 120s before retry...")
                time.sleep(120)
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    _safe_print(f"\n  ** IP ban persistent. Stopping. success={success}, skipped={skipped}")
                    _safe_print(f"  ** VPN을 연결하고 다시 실행하세요: python -m scripts.build_vector_db --step 2")
                    return
            elif "too many" in err_str or "429" in err_str:
                _safe_print(f"    -> Rate limited, waiting 60s...")
                time.sleep(60)
                consecutive_errors += 1
            else:
                _safe_print(f"    -> error: {str(e)[:100]}")
                consecutive_errors += 1

            # 연속 에러가 많으면 긴 대기
            if consecutive_errors >= 3:
                _safe_print(f"    -> {consecutive_errors} consecutive errors, waiting 60s...")
                time.sleep(60)

        # 요청 간 딜레이 (IP 차단 방지)
        time.sleep(1.5)

        # 배치 처리: 20건마다 15초 대기
        if (i + 1) % BATCH_SIZE == 0 and i + 1 < total:
            _safe_print(f"    -- batch pause ({i + 1}/{total}), waiting 15s --")
            time.sleep(15)

    _safe_print(f"\n  Transcript done: success={success} / skipped={skipped} / total={total}")


# ============================================
# STEP 3: 자막 정제 (LLM) - 영어 자막도 한국어로 번역+정제
# ============================================
REFINE_PROMPT = """당신은 한국어 의료 콘텐츠 전문 편집자입니다.
아래는 YouTube 의료 영상의 자동 생성 자막입니다.

**중요: 자막이 영어인 경우 반드시 한국어로 번역하면서 정제하세요.**

다음 작업을 수행하세요:

1. **언어 확인**: 영어 자막이면 한국어로 번역. 한국어 자막이면 그대로 정제.
2. **오탈자 수정**: 자동 자막의 오류를 문맥에 맞게 수정
3. **의료 용어 교정**:
   - "울세라" → "울쎄라", "하이후" → "하이푸" (HIFU)
   - "필라" → "필러", "레이져" → "레이저"
   - Ultherapy → 울쎄라, Thermage → 써마지, HIFU → 하이푸
   - Botox → 보톡스, Filler → 필러, Laser → 레이저
   - 기타 의료 용어를 정확한 한국어로 교정
4. **문장 단위 정리**: 자연스러운 한국어 문장으로 재구성
5. **불필요 내용 제거**: 구독/좋아요 유도, 광고, 인사말 등 의료 정보와 무관한 내용 삭제
6. **의료 정보만 보존**: 시술 설명, 효과, 부작용, 회복기간, 주의사항 등에 집중

원본 자막:
{transcript}

반드시 한국어로 정제된 텍스트만 반환하세요. 마크다운이나 제목 없이 순수 텍스트로."""


def refine_transcript(raw_transcript: str) -> str:
    MAX_CHARS = 15000

    if len(raw_transcript) <= MAX_CHARS:
        return _gemini_call_with_retry(
            REFINE_PROMPT.format(transcript=raw_transcript)
        )

    chunks = [
        raw_transcript[i : i + MAX_CHARS]
        for i in range(0, len(raw_transcript), MAX_CHARS)
    ]
    refined_parts = []

    for chunk in chunks:
        text = _gemini_call_with_retry(REFINE_PROMPT.format(transcript=chunk))
        refined_parts.append(text)
        time.sleep(4)

    return "\n\n".join(refined_parts)


def refine_all_transcripts():
    db = get_supabase()
    fetched = _db_retry(
        lambda: db.table("youtube_sources").select("*").eq("status", "transcript_fetched").execute()
    )

    total = len(fetched.data)
    success = 0

    for i, video in enumerate(fetched.data):
        _safe_print(f"  [{i + 1}/{total}] refining: {video['title'][:50]}...")

        try:
            refined = refine_transcript(video["raw_transcript"])

            _db_retry(lambda v=video["video_id"], r=refined: (
                db.table("youtube_sources").update(
                    {"refined_transcript": r, "status": "refined"}
                ).eq("video_id", v).execute()
            ))
            success += 1

        except Exception as e:
            _safe_print(f"    -> refine failed: {str(e)[:80]}")
            try:
                _db_retry(lambda v=video["video_id"]: (
                    db.table("youtube_sources").update({"status": "failed"}).eq(
                        "video_id", v
                    ).execute()
                ))
            except Exception:
                pass

        time.sleep(4)

    _safe_print(f"\n  Refine done: {success}/{total}")


# ============================================
# STEP 4: FAQ 변환 (LLM)
# ============================================
FAQ_PROMPT = """당신은 의료 콘텐츠에서 FAQ를 추출하는 전문가입니다.
아래 정제된 의료 영상 텍스트에서 환자 관점의 FAQ를 추출하세요.

카테고리: {category_kr}

규칙:
1. 각 FAQ는 환자가 실제로 궁금해할 질문이어야 합니다.
2. 답변은 2~3문장, 영상 내용 기반으로 근거를 포함하세요.
3. 관련 시술명을 태그하세요.
4. 영상당 3~8개 FAQ를 추출하세요.
5. 의료 정보가 적은 영상이면 빈 배열 []을 반환하세요.

반드시 JSON 형식만 반환하세요 (마크다운 코드블록 없이):
[
  {{
    "question": "환자 관점의 질문",
    "answer": "의료진 설명 (2~3문장, 근거 포함)",
    "procedure_name": "관련 시술명 (없으면 null)"
  }}
]

텍스트:
{text}"""


def generate_faqs(refined_text: str, category: str) -> list:
    category_kr = "피부과" if category == "dermatology" else "성형외과"

    text = _gemini_call_with_retry(
        FAQ_PROMPT.format(category_kr=category_kr, text=refined_text)
    )

    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        faqs = json.loads(text)
        return faqs if isinstance(faqs, list) else []
    except json.JSONDecodeError:
        _safe_print("    -> JSON parse failed")
        return []


def generate_all_faqs():
    db = get_supabase()
    refined = _db_retry(
        lambda: db.table("youtube_sources").select("*").eq("status", "refined").execute()
    )

    total = len(refined.data)
    total_faqs = 0

    for i, video in enumerate(refined.data):
        _safe_print(f"  [{i + 1}/{total}] FAQ gen: {video['title'][:50]}...")

        try:
            faqs = generate_faqs(video["refined_transcript"], video["category"])

            if faqs:
                for faq in faqs:
                    _db_retry(lambda f=faq, v=video: (
                        db.table("faq_vectors").insert(
                            {
                                "category": v["category"],
                                "question": f["question"],
                                "answer": f["answer"],
                                "procedure_name": f.get("procedure_name"),
                                "youtube_video_id": v["video_id"],
                                "youtube_title": v["title"],
                                "youtube_url": v["url"],
                                "embedding": [0.0] * 768,
                            }
                        ).execute()
                    ))

                total_faqs += len(faqs)

            _db_retry(lambda v=video["video_id"], n=len(faqs): (
                db.table("youtube_sources").update(
                    {"status": "faq_generated", "faq_count": n}
                ).eq("video_id", v).execute()
            ))

        except Exception as e:
            _safe_print(f"    -> FAQ gen failed: {str(e)[:80]}")
            try:
                _db_retry(lambda v=video["video_id"]: (
                    db.table("youtube_sources").update({"status": "failed"}).eq(
                        "video_id", v
                    ).execute()
                ))
            except Exception:
                pass

        time.sleep(4)

    _safe_print(f"\n  FAQ done: {total_faqs} FAQs / {total} videos")


# ============================================
# STEP 5: 임베딩 + 벡터 저장
# ============================================
def generate_embedding(text: str) -> list[float]:
    result = genai.embed_content(
        model=_embedding_model,
        content=text,
        task_type="retrieval_document",
        output_dimensionality=768,
    )
    return result["embedding"]


def embed_all_faqs():
    db = get_supabase()
    sources = _db_retry(
        lambda: db.table("youtube_sources").select("video_id").eq("status", "faq_generated").execute()
    )

    total_embedded = 0

    for source in sources.data:
        video_id = source["video_id"]

        faqs = _db_retry(
            lambda v=video_id: db.table("faq_vectors").select("id, question").eq("youtube_video_id", v).execute()
        )

        for faq in faqs.data:
            try:
                embedding = generate_embedding(faq["question"])

                _db_retry(lambda fid=faq["id"], emb=embedding: (
                    db.table("faq_vectors").update({"embedding": emb}).eq(
                        "id", fid
                    ).execute()
                ))

                total_embedded += 1

            except Exception as e:
                _safe_print(f"    -> embedding failed: {str(e)[:80]}")
                time.sleep(5)

            time.sleep(0.3)

        _db_retry(lambda v=video_id: (
            db.table("youtube_sources").update({"status": "embedded"}).eq(
                "video_id", v
            ).execute()
        ))

    _safe_print(f"\n  Embedding done: {total_embedded} FAQ vectors")
