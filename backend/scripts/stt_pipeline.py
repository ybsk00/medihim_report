"""
STT 파이프라인: 자막 없는 YouTube 영상을 음성 추출 → Gemini Audio로 전사.

사용법:
  cd backend
  python -m scripts.stt_pipeline              # 스킵된 영상 전부 STT 처리
  python -m scripts.stt_pipeline --limit 10   # 10건만 처리
  python -m scripts.stt_pipeline --stats      # 현재 통계
"""
import argparse
import os
import sys
import time
import tempfile
import subprocess

from google import genai
from google.genai import types

from config import GEMINI_API_KEY
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
# Gemini Client 초기화 (새로운 google-genai SDK)
# ============================================
client = genai.Client(api_key=GEMINI_API_KEY)

TRANSCRIBE_PROMPT = """이 오디오는 의료 콘텐츠(피부과/성형외과) YouTube 영상입니다.
어떤 언어(한국어, 영어, 일본어, 중국어, 태국어, 몽골어 등)든 상관없이 처리하세요.

다음 작업을 수행하세요:
1. 오디오의 음성을 **한국어**로 전사(transcription)하세요.
2. 한국어가 아닌 음성(영어, 일본어, 태국어, 몽골어 등)인 경우 한국어로 번역하면서 전사하세요.
3. 음악, 효과음, 무음 구간은 무시하세요.
4. 의료 용어는 정확하게 표기하세요 (예: 보톡스, 필러, 레이저, 울쎄라, 하이푸, 써마지 등).
5. 구독/좋아요 유도, 광고 등 비의료 내용은 간략히 처리하세요.

결과는 순수 텍스트로만 반환하세요. 마크다운이나 타임스탬프 없이."""


# ============================================
# yt-dlp로 오디오 다운로드
# ============================================
def _get_cookie_path():
    """backend/cookies.txt 경로 반환 (존재하면)."""
    cookie_path = os.path.join(os.path.dirname(__file__), "..", "cookies.txt")
    if os.path.exists(cookie_path):
        return os.path.abspath(cookie_path)
    return None


def download_audio(video_id: str, output_dir: str, retry: int = 0) -> str | None:
    """YouTube 영상에서 오디오만 다운로드 (mp3 변환).
    브라우저 쿠키 우선 사용, 없으면 cookies.txt 사용.
    Returns: 다운로드된 파일 경로 or None
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = os.path.join(output_dir, f"{video_id}.mp3")

    cmd = [
        "yt-dlp",
        "-f", "worstaudio/worst",      # 오디오 우선, 없으면 최소 품질 영상
        "-x",                          # 오디오만 추출
        "--audio-format", "mp3",       # mp3로 변환
        "--audio-quality", "9",        # 최저 품질 (용량 절약)
        "--js-runtimes", "node",       # YouTube n challenge solver
        "--no-playlist",
        "--no-warnings",
        "--output", os.path.join(output_dir, f"{video_id}.%(ext)s"),
    ]

    # 브라우저 쿠키 우선, 없으면 cookies.txt
    cookie_path = _get_cookie_path()
    if cookie_path:
        cmd.extend(["--cookies", cookie_path])

    cmd.append(url)

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            err = result.stderr[:200] if result.stderr else ""
            # 403 에러 시 재시도 (1회)
            if "403" in err and retry < 1:
                _safe_print(f"    -> 403 error, retrying in 60s...")
                time.sleep(60)
                return download_audio(video_id, output_dir, retry + 1)
            _safe_print(f"    -> yt-dlp error: {err[:120]}")
            return None

        # mp3 파일 확인
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            if size_mb > 25:
                _safe_print(f"    -> file too large ({size_mb:.1f}MB), skipping")
                os.remove(output_path)
                return None
            _safe_print(f"    -> downloaded: {size_mb:.1f}MB")
            return output_path

        # mp3 외 다른 포맷 확인 (ffmpeg 없으면 원본 그대로)
        for ext in ["m4a", "webm", "opus", "ogg", "wav"]:
            path = os.path.join(output_dir, f"{video_id}.{ext}")
            if os.path.exists(path):
                size_mb = os.path.getsize(path) / (1024 * 1024)
                _safe_print(f"    -> downloaded: {size_mb:.1f}MB ({ext})")
                return path

        return None
    except subprocess.TimeoutExpired:
        _safe_print("    -> download timeout (5min)")
        return None
    except Exception as e:
        _safe_print(f"    -> download error: {str(e)[:80]}")
        return None


# ============================================
# Gemini Audio로 전사
# ============================================
def transcribe_with_gemini(audio_path: str) -> str | None:
    """Gemini 2.0 Flash로 오디오 전사.
    파일을 Gemini Files API에 업로드 후 전사 요청.
    """
    try:
        # 파일 업로드
        _safe_print("    -> uploading to Gemini...")
        uploaded_file = client.files.upload(file=audio_path)

        # 처리 대기 (파일이 ACTIVE 상태가 될 때까지)
        max_wait = 60
        waited = 0
        while uploaded_file.state == "PROCESSING" and waited < max_wait:
            time.sleep(3)
            waited += 3
            uploaded_file = client.files.get(name=uploaded_file.name)

        if uploaded_file.state != "ACTIVE":
            _safe_print(f"    -> file state: {uploaded_file.state}, skipping")
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
            return None

        # 전사 요청
        _safe_print("    -> transcribing...")
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_uri(
                            file_uri=uploaded_file.uri,
                            mime_type=uploaded_file.mime_type,
                        ),
                        types.Part.from_text(text=TRANSCRIBE_PROMPT),
                    ]
                )
            ],
        )

        # 정리: 업로드된 파일 삭제
        try:
            client.files.delete(name=uploaded_file.name)
        except Exception:
            pass

        if response and response.text:
            return response.text.strip()

        return None

    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            _safe_print("    -> Rate limited, waiting 60s...")
            time.sleep(60)
            return transcribe_with_gemini(audio_path)  # 1회 재시도
        _safe_print(f"    -> transcribe error: {err_str[:120]}")
        return None


# ============================================
# 메인 STT 파이프라인
# ============================================
def run_stt_pipeline(limit: int | None = None):
    db = get_supabase()

    # skipped + pending 상태인 영상 가져오기
    skipped_data = []
    for status in ["skipped", "pending"]:
        query = db.table("youtube_sources").select("*").eq("status", status)
        result = _db_retry(lambda: query.execute())
        skipped_data.extend(result.data)

    if limit:
        skipped_data = skipped_data[:limit]

    total = len(skipped_data)
    _safe_print(f"\n{'=' * 50}")
    _safe_print(f"  STT Pipeline: {total} videos (skipped+pending)")
    _safe_print(f"{'=' * 50}\n")

    # skipped_data를 skipped.data 호환용으로 래핑
    class _Wrapper:
        def __init__(self, data):
            self.data = data
    skipped = _Wrapper(skipped_data)

    if total == 0:
        _safe_print("  No skipped videos found.")
        return

    success = 0
    failed = 0

    # 임시 디렉토리 생성
    tmp_dir = os.path.join(tempfile.gettempdir(), "ippo_stt")
    os.makedirs(tmp_dir, exist_ok=True)

    for i, video in enumerate(skipped.data):
        video_id = video["video_id"]
        title = video.get("title", "")[:60]
        _safe_print(f"  [{i + 1}/{total}] STT: {title}...")

        # 1. 오디오 다운로드
        audio_path = download_audio(video_id, tmp_dir)
        if not audio_path:
            _safe_print("    -> no audio, keeping skipped")
            failed += 1
            continue

        # 2. Gemini로 전사
        transcript = transcribe_with_gemini(audio_path)

        # 3. 오디오 파일 정리
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception:
            pass

        # 4. DB 업데이트
        if transcript and len(transcript) > 20:
            try:
                _db_retry(lambda v=video_id, t=transcript: (
                    db.table("youtube_sources").update(
                        {"raw_transcript": t, "status": "transcript_fetched"}
                    ).eq("video_id", v).execute()
                ))
                success += 1
                _safe_print(f"    -> OK ({len(transcript)} chars)")
            except Exception as e:
                _safe_print(f"    -> DB save error: {str(e)[:80]}")
                failed += 1
        else:
            _safe_print(f"    -> transcript too short or empty, keeping skipped")
            failed += 1

        # Rate limit 대기 (yt-dlp + Gemini 모두 고려, IP ban 방지)
        time.sleep(15)

        # 3건마다 긴 대기 (YouTube 403 방지)
        if (i + 1) % 3 == 0 and i + 1 < total:
            _safe_print(f"    -- batch pause ({i + 1}/{total}), waiting 90s --")
            time.sleep(90)

    # 임시 디렉토리 정리
    try:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass

    _safe_print(f"\n  STT done: success={success} / failed={failed} / total={total}")


def print_stats():
    db = get_supabase()
    from collections import Counter

    r = db.table("youtube_sources").select("status").execute()
    c = Counter(row["status"] for row in r.data)

    _safe_print(f"\n{'=' * 50}")
    _safe_print(f"  YouTube Sources Status")
    _safe_print(f"{'=' * 50}")
    for s, n in sorted(c.items()):
        _safe_print(f"  {s}: {n}")
    _safe_print(f"  TOTAL: {len(r.data)}")
    _safe_print(f"{'=' * 50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STT Pipeline for skipped YouTube videos")
    parser.add_argument("--limit", type=int, help="Process only N videos")
    parser.add_argument("--stats", action="store_true", help="Show current stats")
    args = parser.parse_args()

    if args.stats:
        print_stats()
    else:
        run_stt_pipeline(args.limit)
