"""이뽀 앱에 리포트 완료 알림 전송 (report_ready webhook callback)"""

import hmac
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta

import httpx

logger = logging.getLogger(__name__)

JST = timezone(timedelta(hours=9))


async def notify_report_ready(consultation_id: str):
    """리포트 생성 완료 시 이뽀 앱에 콜백 전송 (리포트 타입별 개별 전송)

    이뽀 기대 포맷:
    {
            "ippeo_user_id": "...",
      "ippeo_consultation_id": "...",
      "consultation_id": "...",
      "consultation_round": 1,
      "report_token": "...",
      "report_type": "r4",
      "embed_url": { "ja": "...", "ko": "..." },
      "status": "report_ready",
      "created_at": "2026-03-11T15:03:22+09:00"
    }
    """
    from config import IPPEO_WEBHOOK_URL, IPPEO_WEBHOOK_SECRET, IPPEO_API_KEY, FRONTEND_URL
    from services.supabase_client import get_supabase

    callback_url = IPPEO_WEBHOOK_URL
    if not callback_url:
        logger.warning("[Callback] IPPEO_WEBHOOK_URL not configured, skipping callback")
        return

    db = get_supabase()

    # 상담 데이터 조회
    consultation = (
        db.table("consultations")
        .select("id, status, customer_name, customer_id, ippeo_consultation_id, consultation_round, error_message")
        .eq("id", consultation_id)
        .single()
        .execute()
    )
    if not consultation.data:
        logger.error(f"[Callback] Consultation {consultation_id} not found")
        return

    c = consultation.data
    ippeo_user_id = c.get("customer_id") or ""
    ippeo_consultation_id = c.get("ippeo_consultation_id") or ""
    consultation_round = c.get("consultation_round") or 1
    now_jst = datetime.now(JST).isoformat()

    # 실패 시 에러 콜백
    if c["status"] == "report_failed":
        error_payload = {
                        "ippeo_user_id": ippeo_user_id,
            "ippeo_consultation_id": ippeo_consultation_id,
            "consultation_id": consultation_id,
            "consultation_round": consultation_round,
            "status": "report_failed",
            "error_message": c.get("error_message") or "리포트 생성 실패",
            "created_at": now_jst,
        }
        await _send_callback(callback_url, error_payload, IPPEO_API_KEY, IPPEO_WEBHOOK_SECRET)
        return

    # 리포트 조회
    reports = (
        db.table("reports")
        .select("report_type, access_token")
        .eq("consultation_id", consultation_id)
        .execute()
    )

    embed_base = f"{FRONTEND_URL}/embed"

    # 리포트 타입별 개별 콜백 전송
    for r in reports.data or []:
        token = r["access_token"]
        report_type = r["report_type"]

        # embed_url 구성
        if report_type == "r4":
            embed_url = {
                "ja": f"{embed_base}/{token}?lang=ja",
                "ko": f"{embed_base}/{token}?lang=ko",
            }
        else:
            embed_url = {
                "ko": f"{embed_base}/{token}?lang=ko",
            }

        payload = {
                        "ippeo_user_id": ippeo_user_id,
            "ippeo_consultation_id": ippeo_consultation_id,
            "consultation_id": consultation_id,
            "consultation_round": consultation_round,
            "report_token": token,
            "report_type": report_type,
            "embed_url": embed_url,
            "status": "report_ready",
            "created_at": now_jst,
        }

        await _send_callback(callback_url, payload, IPPEO_API_KEY, IPPEO_WEBHOOK_SECRET)


async def _send_callback(url: str, payload: dict, api_key: str, secret: str):
    """콜백 전송 (HMAC 서명 + 최대 3회 재시도)"""
    body = json.dumps(payload, ensure_ascii=False)

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    if secret:
        sig = hmac.new(
            secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-Signature"] = f"sha256={sig}"

    report_type = payload.get("report_type", "unknown")
    event = payload.get("event", "unknown")

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(url, content=body.encode("utf-8"), headers=headers)

            if res.status_code < 300:
                logger.info(
                    f"[Callback] {event} ({report_type}) sent to ippeo "
                    f"(consultation={payload.get('consultation_id', '')[:8]}, status={res.status_code})"
                )
                return
            else:
                logger.warning(
                    f"[Callback] Ippeo returned {res.status_code}: {res.text[:200]} "
                    f"(attempt {attempt + 1}/3, type={report_type})"
                )
        except Exception as e:
            logger.warning(
                f"[Callback] Failed (attempt {attempt + 1}/3, type={report_type}): {e}"
            )

    logger.error(
        f"[Callback] All 3 attempts failed for {report_type} "
        f"(consultation={payload.get('consultation_id', '')[:8]})"
    )
