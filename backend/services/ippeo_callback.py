"""이뻐 앱에 리포트 완료 알림 전송 (report_ready webhook callback)"""

import asyncio
import copy
import hmac
import hashlib
import json
import logging

import httpx

logger = logging.getLogger(__name__)


async def notify_report_ready(consultation_id: str):
    """리포트 생성 완료 시 이뻐 앱에 콜백 전송 (운영 + 개발 동시)"""
    from config import IPPEO_WEBHOOK_URL, IPPEO_WEBHOOK_URL_DEV, IPPEO_WEBHOOK_SECRET, IPPEO_API_KEY, FRONTEND_URL
    from services.supabase_client import get_supabase

    # 전송할 URL 목록 구성
    callback_urls = []
    if IPPEO_WEBHOOK_URL:
        callback_urls.append(("PROD", IPPEO_WEBHOOK_URL))
    if IPPEO_WEBHOOK_URL_DEV:
        callback_urls.append(("DEV", IPPEO_WEBHOOK_URL_DEV))

    if not callback_urls:
        logger.warning("[Callback] No IPPEO_WEBHOOK_URL configured, skipping callback")
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
        # 실패 콜백은 리포트가 없으므로 PROD/DEV 동일 payload
        payloads = {label: payload for label, _ in callback_urls}
        await _send_to_all(callback_urls, payloads, IPPEO_API_KEY, IPPEO_WEBHOOK_SECRET)
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

    # R4 폴백 시 직전 회차 정상 R4 토큰 승계 (페이로드 키/URL/status 변경 없이 token만 치환)
    inherited_r4_token = None
    is_fallback = (c.get("error_message") or "").startswith("[폴백]")
    if is_fallback and ippeo_consultation_id and "_r" in ippeo_consultation_id:
        prefix = ippeo_consultation_id.rsplit("_r", 1)[0]
        prior = (
            db.table("consultations")
            .select("id, consultation_round")
            .like("ippeo_consultation_id", f"{prefix}_r%")
            .lt("consultation_round", consultation_round)
            .is_("error_message", "null")
            .order("consultation_round", desc=True)
            .limit(1)
            .execute()
        )
        if prior.data:
            prior_id = prior.data[0]["id"]
            prior_round = prior.data[0]["consultation_round"]
            prior_r4 = (
                db.table("reports")
                .select("access_token")
                .eq("consultation_id", prior_id)
                .eq("report_type", "r4")
                .limit(1)
                .execute()
            )
            if prior_r4.data and prior_r4.data[0].get("access_token"):
                inherited_r4_token = prior_r4.data[0]["access_token"]
                logger.info(
                    f"[Callback] R4 폴백 감지 → 직전 정상 R4 토큰 승계 "
                    f"(round {prior_round} → {consultation_round}, "
                    f"consultation={consultation_id[:8]})"
                )

    for r in reports.data or []:
        token = r["access_token"]
        if r["report_type"] == "r4":
            if inherited_r4_token:
                token = inherited_r4_token
            payload["patient_report"] = {
                "report_token": token,
                "embed_url": {
                    "ja": f"{embed_base}/patient/ja/{token}",
                    "ko": f"{embed_base}/patient/ko/{token}",
                },
            }
        elif r["report_type"] == "r3":
            payload["doctor_report"] = {
                "report_token": token,
                "embed_url": {
                    "ko": f"{embed_base}/doctor/ko/{token}",
                },
            }
        elif r["report_type"] == "r1":
            payload["pre_consultation_report"] = {
                "report_token": token,
                "embed_url": {
                    "ko": f"{embed_base}/doctor/ko/{token}",
                },
            }
        elif r["report_type"] == "r2":
            payload["medical_report"] = {
                "report_token": token,
                "embed_url": {
                    "ko": f"{embed_base}/doctor/ko/{token}",
                },
            }

    # PROD + DEV 모두에 json_url 추가 (사용자 지시 2026-07-01: 운영에도 JSON 적용).
    # embed_url(아이프레임)은 그대로 유지하고 json_url을 형제 키로 추가 = 가산적 변경.
    # ⚠️ embed_url 절대 제거 금지 원칙은 유지. 콜백 키/URL/status는 불변, json_url만 추가.
    augmented_payload = _build_json_payload(payload, FRONTEND_URL)
    payloads = {label: augmented_payload for label, _ in callback_urls}
    await _send_to_all(callback_urls, payloads, IPPEO_API_KEY, IPPEO_WEBHOOK_SECRET)


# DEV json_url 언어 매핑 (리포트 키별 제공 언어)
_DEV_JSON_LANGS = {
    "patient_report": ["ja", "ko"],   # R4 고객용
    "doctor_report": ["ko"],          # R3 병원용 (한국어)
    "pre_consultation_report": ["ko"],  # R1 (평소 미생성)
    "medical_report": ["ko"],         # R2 (평소 미생성)
}


def _build_json_payload(base_payload: dict, frontend_url: str) -> dict:
    """기존 payload에 리포트별 json_url만 추가 (PROD/DEV 공통).

    embed_url(아이프레임)은 그대로 두고 json_url을 형제 키로 붙인다.
    json_url은 embed_url과 동일한 report_token(폴백 승계 토큰 포함)을 사용한다.
    2026-07-01 사용자 지시로 운영(PROD) 콜백에도 동일 적용.
    """
    dev = copy.deepcopy(base_payload)
    json_base = f"{frontend_url}/api/dev/report"
    for key, langs in _DEV_JSON_LANGS.items():
        item = dev.get(key)
        if isinstance(item, dict) and item.get("report_token"):
            tok = item["report_token"]
            item["json_url"] = {lg: f"{json_base}/{lg}/{tok}.json" for lg in langs}
    return dev


async def _send_to_all(urls: list[tuple[str, str]], payloads: dict, api_key: str, secret: str):
    """운영 + 개발 서버에 동시 전송 (각각 독립적으로 재시도).

    payloads: {label: payload} — 라벨(PROD/DEV)별로 다른 payload 전송 가능.
    """
    tasks = [
        _send_callback(label, url, payloads[label], api_key, secret)
        for label, url in urls
    ]
    await asyncio.gather(*tasks, return_exceptions=True)


async def _send_callback(label: str, url: str, payload: dict, api_key: str, secret: str):
    """콜백 전송 (HMAC 서명 + 최대 3회 재시도)"""
    body = json.dumps(payload, ensure_ascii=True)

    headers = {"Content-Type": "application/json; charset=utf-8"}
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
                    f"[Callback:{label}] Report ready sent "
                    f"(consultation={payload.get('consultation_id', '')[:8]}, status={res.status_code})"
                )
                return
            else:
                logger.warning(
                    f"[Callback:{label}] Ippeo returned {res.status_code}: {res.text[:200]} "
                    f"(attempt {attempt + 1}/3)"
                )
        except Exception as e:
            logger.warning(
                f"[Callback:{label}] Failed (attempt {attempt + 1}/3): {e}"
            )

    logger.error(
        f"[Callback:{label}] All 3 attempts failed "
        f"(consultation={payload.get('consultation_id', '')[:8]})"
    )
