"""이뽀 앱 Webhook 발송 서비스 — 리포트 완료/실패 알림"""

import asyncio
import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta

import httpx

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))
RETRY_INTERVALS = [30, 120, 600]  # 30초, 2분, 10분


def _get_config():
    from config import IPPEO_WEBHOOK_URL, IPPEO_API_KEY, IPPEO_WEBHOOK_SECRET, FRONTEND_URL
    return IPPEO_WEBHOOK_URL, IPPEO_API_KEY, IPPEO_WEBHOOK_SECRET, FRONTEND_URL


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """HMAC-SHA256 서명 생성"""
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def _kst_now() -> str:
    """현재 KST 시각을 yyyy-MM-dd HH:mm:ss 형식으로 반환"""
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


async def send_report_ready_webhook(
    consultation_id: str,
    ippeo_user_id: str,
    ippeo_consultation_id: str,
    consultation_round: int,
    patient_token: str | None,
    doctor_token: str | None,
):
    """리포트 생성 완료 Webhook 발송 (환자용 R4 + 의사용 R1 묶어서 1번)"""
    webhook_url, api_key, secret, frontend_url = _get_config()

    if not webhook_url:
        logger.warning("IPPEO_WEBHOOK_URL 미설정 — Webhook 발송 건너뜀")
        return

    embed_base = f"{frontend_url}/embed"

    payload = {
        "event": "report_ready",
        "ippeo_user_id": ippeo_user_id,
        "ippeo_consultation_id": ippeo_consultation_id,
        "ippeo_consultation_round": str(consultation_round),
        "consultation_id": consultation_id,
        "status": "report_ready",
        "created_at": _kst_now(),
    }

    # 환자용 (R4) — 일본어 + 한국어
    if patient_token:
        payload["patient_report"] = {
            "report_token": patient_token,
            "report_type": "r4",
            "embed_url": {
                "ja": f"{embed_base}/{patient_token}?lang=ja",
                "ko": f"{embed_base}/{patient_token}?lang=ko",
            }
        }

    # 의사용 (R1) — 한국어만
    if doctor_token:
        payload["doctor_report"] = {
            "report_token": doctor_token,
            "report_type": "r1",
            "embed_url": {
                "ko": f"{embed_base}/{doctor_token}?lang=ko",
            }
        }

    # 발송 + 재시도
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key or "",
    }
    if secret:
        headers["X-Signature"] = _sign_payload(payload_bytes, secret)

    for attempt in range(len(RETRY_INTERVALS) + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    webhook_url,
                    content=payload_bytes,
                    headers=headers,
                )

            if response.status_code == 200:
                logger.info(f"Webhook 발송 성공: consultation={consultation_id}, attempt={attempt+1}")
                return True
            else:
                logger.warning(f"Webhook 응답 오류: {response.status_code} — {response.text}")

        except Exception as e:
            logger.error(f"Webhook 발송 실패 (attempt {attempt+1}): {e}")

        # 재시도 대기
        if attempt < len(RETRY_INTERVALS):
            wait = RETRY_INTERVALS[attempt]
            logger.info(f"Webhook 재시도 대기: {wait}초 후 attempt {attempt+2}")
            await asyncio.sleep(wait)

    logger.error(f"Webhook 발송 최종 실패: consultation={consultation_id}")
    return False


async def send_report_failed_webhook(
    consultation_id: str,
    ippeo_user_id: str,
    ippeo_consultation_id: str,
    consultation_round: int,
    error_message: str,
):
    """리포트 생성 실패 Webhook 발송"""
    webhook_url, api_key, secret, _ = _get_config()

    if not webhook_url:
        return

    payload = {
        "event": "report_failed",
        "ippeo_user_id": ippeo_user_id,
        "ippeo_consultation_id": ippeo_consultation_id,
        "ippeo_consultation_round": str(consultation_round),
        "consultation_id": consultation_id,
        "status": "report_failed",
        "error_message": error_message,
        "created_at": _kst_now(),
    }

    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key or "",
    }
    if secret:
        headers["X-Signature"] = _sign_payload(payload_bytes, secret)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(webhook_url, content=payload_bytes, headers=headers)
    except Exception as e:
        logger.error(f"실패 Webhook 발송 오류: {e}")
