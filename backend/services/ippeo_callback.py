"""이뽀 앱에 리포트 완료 알림 전송 (report_ready webhook callback)"""

import hmac
import hashlib
import json
import logging

import httpx

logger = logging.getLogger(__name__)


async def notify_report_ready(consultation_id: str):
    """리포트 생성 완료 시 이뽀 앱에 콜백 전송

    POST {IPPEO_CALLBACK_URL} with:
      - consultation_id
      - status
      - patient_report (embed_url.ja, embed_url.ko)
      - doctor_report (embed_url.ko)
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
        .select("id, status, customer_name")
        .eq("id", consultation_id)
        .single()
        .execute()
    )
    if not consultation.data:
        logger.error(f"[Callback] Consultation {consultation_id} not found")
        return

    # 리포트 embed URL 조회
    reports = (
        db.table("reports")
        .select("report_type, access_token")
        .eq("consultation_id", consultation_id)
        .execute()
    )

    embed_base = f"{FRONTEND_URL}/embed"
    payload = {
        "consultation_id": consultation_id,
        "status": consultation.data["status"],
        "customer_name": consultation.data["customer_name"],
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

    body = json.dumps(payload, ensure_ascii=False)

    # HMAC-SHA256 서명 생성
    headers = {
        "Content-Type": "application/json",
    }
    if IPPEO_API_KEY:
        headers["X-API-Key"] = IPPEO_API_KEY
    if IPPEO_WEBHOOK_SECRET:
        sig = hmac.new(
            IPPEO_WEBHOOK_SECRET.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-Signature"] = f"sha256={sig}"

    # 전송 (최대 3회 재시도)
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(callback_url, content=body, headers=headers)

            if res.status_code < 300:
                logger.info(
                    f"[Callback] Report ready notification sent to ippeo "
                    f"(consultation={consultation_id[:8]}, status={res.status_code})"
                )
                return
            else:
                logger.warning(
                    f"[Callback] Ippeo returned {res.status_code}: {res.text[:200]} "
                    f"(attempt {attempt + 1}/3)"
                )
        except Exception as e:
            logger.warning(
                f"[Callback] Failed to notify ippeo (attempt {attempt + 1}/3): {e}"
            )

    logger.error(
        f"[Callback] All 3 attempts failed for consultation {consultation_id[:8]}. "
        f"Ippeo can still poll GET /api/webhook/status/{consultation_id}"
    )
