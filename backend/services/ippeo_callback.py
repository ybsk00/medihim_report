"""이뽀 앱에 리포트 완료 알림 전송 (report_ready webhook callback)"""

import hmac
import hashlib
import json
import logging

import httpx

logger = logging.getLogger(__name__)


async def notify_report_ready(consultation_id: str):
    """리포트 생성 완료 시 이뽀 앱에 콜백 전송 (1건 통합)"""
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
        .select("id, status, customer_name, consultation_round, ippeo_consultation_id, error_message")
        .eq("id", consultation_id)
        .single()
        .execute()
    )
    if not consultation.data:
        logger.error(f"[Callback] Consultation {consultation_id} not found")
        return

    c = consultation.data
    consultation_round = c.get("consultation_round") or 1
    ippeo_consultation_id = c.get("ippeo_consultation_id") or ""

    # 실패 시
    if c["status"] == "report_failed":
        payload = {
            "status": "report_failed",
            "consultation_id": consultation_id,
            "ippeo_consultation_id": ippeo_consultation_id,
            "ippeo_consultation_round": consultation_round,
            "customer_name": c["customer_name"],
            "error_message": c.get("error_message") or "리포트 생성 실패",
        }
        await _send_callback(callback_url, payload, IPPEO_API_KEY, IPPEO_WEBHOOK_SECRET)
        return

    # 리포트 조회
    reports = (
        db.table("reports")
        .select("report_type, access_token")
        .eq("consultation_id", consultation_id)
        .execute()
    )

    embed_base = f"{FRONTEND_URL}/embed"

    payload = {
        "status": c["status"],
        "consultation_id": consultation_id,
        "ippeo_consultation_id": ippeo_consultation_id,
        "ippeo_consultation_round": consultation_round,
        "customer_name": c["customer_name"],
    }

    for r in reports.data or []:
        token = r["access_token"]
        if r["report_type"] == "r4":
            payload["patient_report"] = {
                "report_token": token,
                "embed_url": {
                    "ja": f"{embed_base}/{token}?lang=ja",
                    "ko": f"{embed_base}/{token}?lang=ko",
                },
            }
        elif r["report_type"] == "r1":
            payload["doctor_report"] = {
                "report_token": token,
                "embed_url": {
                    "ko": f"{embed_base}/{token}?lang=ko",
                },
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

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(url, content=body.encode("utf-8"), headers=headers)

            if res.status_code < 300:
                logger.info(
                    f"[Callback] Report ready sent to ippeo "
                    f"(consultation={payload.get('consultation_id', '')[:8]}, status={res.status_code})"
                )
                return
            else:
                logger.warning(
                    f"[Callback] Ippeo returned {res.status_code}: {res.text[:200]} "
                    f"(attempt {attempt + 1}/3)"
                )
        except Exception as e:
            logger.warning(
                f"[Callback] Failed (attempt {attempt + 1}/3): {e}"
            )

    logger.error(
        f"[Callback] All 3 attempts failed "
        f"(consultation={payload.get('consultation_id', '')[:8]})"
    )
