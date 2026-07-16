"""이뻐 앱 → AI 서버 Webhook 수신 API (v1.1 스펙)"""

import logging
import os
import tempfile

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Request

from api.auth_webhook import verify_webhook, verify_api_key
from models.schemas import IppeoConsultationRequest
from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


def _sanitize_stt_text(text: str) -> str:
    """PostgreSQL TEXT가 거부하는 널 문자(\x00) 제거 (22P05 방어)"""
    return text.replace("\x00", "")


def _decode_stt_bytes(content: bytes) -> str:
    """STT 파일 바이트를 인코딩 자동 감지로 디코딩 (UTF-16/UTF-8 BOM/CP949)"""
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = content.decode("utf-16")
    elif content.startswith(b"\xef\xbb\xbf"):
        text = content.decode("utf-8-sig")
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            # BOM 없는 파일: UTF-16(널 바이트 다수) → CP949 → UTF-8(대체) 순 시도
            if content.count(b"\x00") > len(content) // 4:
                try:
                    return _sanitize_stt_text(content.decode("utf-16"))
                except UnicodeDecodeError:
                    pass
            try:
                text = content.decode("cp949")
            except UnicodeDecodeError:
                text = content.decode("utf-8", errors="replace")
        else:
            # UTF-8로 디코딩됐지만 널 바이트 비율이 높으면 BOM 없는 UTF-16일 가능성
            if content.count(b"\x00") > len(content) // 4:
                try:
                    text = content.decode("utf-16")
                except UnicodeDecodeError:
                    pass
    return _sanitize_stt_text(text)


def _detect_audio_ext(content: bytes) -> str | None:
    """매직 바이트로 음성 파일 여부 판별. 음성이면 확장자, 아니면 None"""
    if len(content) < 12:
        return None
    if content.startswith(b"ID3"):
        return ".mp3"
    # MP3 프레임 싱크(FF Ex) — 단 UTF-16 LE BOM(FF FE)은 텍스트이므로 제외
    if (
        content[0] == 0xFF
        and (content[1] & 0xE0) == 0xE0
        and not content.startswith(b"\xff\xfe")
    ):
        return ".mp3"
    if content.startswith(b"RIFF") and content[8:12] == b"WAVE":
        return ".wav"
    if content[4:8] == b"ftyp":
        return ".m4a"
    if content.startswith(b"OggS"):
        return ".ogg"
    if content.startswith(b"fLaC"):
        return ".flac"
    return None


async def _download_stt_bytes(url: str) -> bytes:
    """S3 Presigned URL에서 STT 파일 다운로드 (10분 유효)"""
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


async def _run_stt_on_audio(content: bytes, ext: str) -> dict:
    """음성 바이트를 임시 파일로 저장 후 Gemini STT + 감정 분석 (upload-audio와 동일 플로우)"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        from agents.speech_emotion_analyzer import stt_with_emotion

        return await stt_with_emotion(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


async def _process_consultation_with_id(consultation_id: str, data: dict):
    """백그라운드: STT 확보 → 파이프라인 실행 (R3 + R4 자동 생성)"""
    db = get_supabase()

    try:
        # 1. STT 텍스트 확보
        stt_text = _sanitize_stt_text(data.get("stt_text", "") or "")

        # stt_file_url이 있으면 S3에서 다운로드 (텍스트 또는 음성 파일)
        if data.get("stt_file_url"):
            content = await _download_stt_bytes(data["stt_file_url"])
            audio_ext = _detect_audio_ext(content)

            if audio_ext:
                # 음성 파일 → Gemini STT + 감정 분석 후 파이프라인 진행
                logger.info(
                    f"[Webhook] Audio detected ({audio_ext}, {len(content)} bytes) "
                    f"→ Gemini STT: {consultation_id}"
                )
                stt_result = await _run_stt_on_audio(content, audio_ext)
                stt_text = _sanitize_stt_text(stt_result.get("transcription", "") or "")
                detected = stt_result.get("detected_language", "ja")
                db.table("consultations").update({
                    "original_text": stt_text,
                    "input_language": "ko" if detected == "ko" else "ja",
                    "voice_emotion_analysis": stt_result.get("emotion_analysis", {}),
                }).eq("id", consultation_id).execute()
            else:
                stt_text = _decode_stt_bytes(content)
                # 텍스트도 음성도 아닌 바이너리(대체문자 과다)는 명확한 에러로 중단
                if stt_text and stt_text.count("�") > max(1, len(stt_text) // 20):
                    raise ValueError(
                        "stt_file_url 파일이 텍스트/음성 형식이 아닙니다 (인코딩 판별 실패)"
                    )
                db.table("consultations").update({
                    "original_text": stt_text,
                }).eq("id", consultation_id).execute()

        if not stt_text or not stt_text.strip():
            raise ValueError("STT 텍스트가 비어있습니다.")

        logger.info(f"[Webhook] STT ready: {len(stt_text)} chars, consultation: {consultation_id}")

        # 2. 파이프라인 자동 실행 (R3 + R4)
        from agents.pipeline import run_pipeline
        await run_pipeline(consultation_id)

    except Exception as e:
        logger.error(f"[Webhook] Processing failed: {e}", exc_info=True)
        db = get_supabase()
        db.table("consultations").update({
            "status": "report_failed",
            "error_message": str(e),
        }).eq("id", consultation_id).execute()


@router.post("/consultation")
async def receive_consultation(
    data: IppeoConsultationRequest,
    background_tasks: BackgroundTasks,
    _auth=Depends(verify_webhook),
):
    """
    이뻐 앱에서 상담 STT 데이터 수신.
    즉시 consultation_id를 반환하고, 백그라운드에서 R3(상담실장용) + R4(환자용) 리포트 자동 생성.
    """
    logger.info(
        f"[Webhook] Received: customer={data.customer_name}, round={data.consultation_round}"
    )

    # 상담 먼저 등록 (consultation_id 확보)
    db = get_supabase()
    stt_text = _sanitize_stt_text(data.stt_text or "")

    record = {
        "customer_name": data.customer_name,
        "customer_email": data.customer_email or "",
        "original_text": stt_text or "(stt_file_url로 다운로드 예정)",
        "hospital_name": data.hospital_name or "",
        "doctor_name": data.doctor_name or "",
        "concern_area": data.concern_area or "",
        "consultation_round": data.consultation_round,
        "customer_id": data.ippeo_user_id or "",
        "ippeo_consultation_id": data.ippeo_consultation_id or "",
        "status": "processing",
    }
    result = db.table("consultations").insert(record).execute()
    consultation_id = result.data[0]["id"]
    logger.info(f"[Webhook] Created consultation: {consultation_id}")

    # 백그라운드에서 파이프라인 실행 (즉시 200 응답)
    background_tasks.add_task(
        _process_consultation_with_id, consultation_id, data.model_dump()
    )

    return {
        "success": True,
        "consultation_id": consultation_id,
        "message": "상담 데이터 수신 완료. 리포트 자동 생성을 시작합니다.",
    }


@router.get("/status/{consultation_id}")
async def get_report_status(
    consultation_id: str,
    _auth=Depends(verify_api_key),
):
    """상담 처리 상태 + embed URL 조회 (이뻐 앱에서 폴링)"""
    db = get_supabase()

    consultation = (
        db.table("consultations")
        .select("id, status, customer_name, error_message")
        .eq("id", consultation_id)
        .single()
        .execute()
    )

    if not consultation.data:
        return {"success": False, "error": "NOT_FOUND"}

    c = consultation.data
    result = {
        "success": True,
        "status": c["status"],
        "customer_name": c["customer_name"],
    }

    # 리포트 생성 완료 시 embed URL 포함
    if c["status"] in ("report_ready", "report_approved", "report_sent"):
        reports = (
            db.table("reports")
            .select("report_type, access_token")
            .eq("consultation_id", c["id"])
            .execute()
        )
        from config import FRONTEND_URL
        embed_base = f"{FRONTEND_URL}/embed"

        for r in reports.data or []:
            token = r["access_token"]
            if r["report_type"] == "r4":
                result["patient_report"] = {
                    "report_token": token,
                    "embed_url": {
                        "ja": f"{embed_base}/patient/ja/{token}",
                        "ko": f"{embed_base}/patient/ko/{token}",
                    }
                }
            elif r["report_type"] == "r3":
                result["doctor_report"] = {
                    "report_token": token,
                    "embed_url": {
                        "ko": f"{embed_base}/doctor/ko/{token}",
                    }
                }
            elif r["report_type"] == "r1":
                result["pre_consultation_report"] = {
                    "report_token": token,
                    "embed_url": {
                        "ko": f"{embed_base}/doctor/ko/{token}",
                    }
                }
            elif r["report_type"] == "r2":
                result["medical_report"] = {
                    "report_token": token,
                    "embed_url": {
                        "ko": f"{embed_base}/doctor/ko/{token}",
                    }
                }

    if c.get("error_message"):
        result["error_message"] = c["error_message"]

    return result
