"""주간 시스템 헬스체크 API — 매주 금요일 18:00 KST Cloud Scheduler 호출"""

import asyncio
import hmac
import hashlib
import json
import logging
import smtplib
import time
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx
from fastapi import APIRouter

from config import (
    GMAIL_ADDRESS, GMAIL_APP_PASSWORD,
    IPPEO_WEBHOOK_URL, IPPEO_WEBHOOK_URL_DEV,
    IPPEO_API_KEY, IPPEO_WEBHOOK_SECRET,
    SUPABASE_URL, GEMINI_API_KEY, FRONTEND_URL,
)
from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["health"])

HEALTH_REPORT_TO = "ug_shin@medihim.com"
KST = timezone(timedelta(hours=9))


async def _check_database() -> dict:
    """DB 연결 + 테이블 상태 확인"""
    try:
        db = get_supabase()
        start = time.time()

        # 상담 수
        consultations = db.table("consultations").select("id", count="exact").execute()
        consultation_count = consultations.count or 0

        # 리포트 수 (타입별)
        reports = db.table("reports").select("report_type").execute()
        type_counts = {}
        for r in reports.data or []:
            rt = r["report_type"]
            type_counts[rt] = type_counts.get(rt, 0) + 1

        # 최근 7일 생성 리포트
        week_ago = (datetime.now(KST) - timedelta(days=7)).isoformat()
        recent = db.table("reports").select("id", count="exact").gte("created_at", week_ago).execute()
        recent_count = recent.count or 0

        # 실패 상담
        failed = db.table("consultations").select("id", count="exact").eq("status", "report_failed").execute()
        failed_count = failed.count or 0

        duration = int((time.time() - start) * 1000)

        return {
            "status": "OK",
            "latency_ms": duration,
            "total_consultations": consultation_count,
            "total_reports": sum(type_counts.values()),
            "report_types": type_counts,
            "reports_last_7days": recent_count,
            "failed_consultations": failed_count,
        }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


async def _check_api_endpoints() -> dict:
    """주요 API 엔드포인트 응답 확인"""
    results = {}
    base = "https://ippo-backend-788517765486.asia-northeast3.run.app"
    endpoints = {
        "root": "/",
        "dashboard": "/api/dashboard/stats",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        for name, path in endpoints.items():
            try:
                start = time.time()
                res = await client.get(f"{base}{path}")
                duration = int((time.time() - start) * 1000)
                results[name] = {
                    "status": "OK" if res.status_code < 400 else "ERROR",
                    "status_code": res.status_code,
                    "latency_ms": duration,
                }
            except Exception as e:
                results[name] = {"status": "ERROR", "error": str(e)}

    all_ok = all(r["status"] == "OK" for r in results.values())
    return {"status": "OK" if all_ok else "ERROR", "endpoints": results}


async def _check_webhook() -> dict:
    """이뽀 웹훅 DEV/PROD 통신 테스트"""
    results = {}

    test_payload = {
        "status": "health_check",
        "consultation_id": "health-check-ping",
        "ippeo_consultation_id": "",
        "ippeo_consultation_round": 0,
        "customer_name": "HealthCheck",
    }
    body = json.dumps(test_payload, ensure_ascii=True)

    headers = {"Content-Type": "application/json; charset=utf-8"}
    if IPPEO_API_KEY:
        headers["X-API-Key"] = IPPEO_API_KEY
    if IPPEO_WEBHOOK_SECRET:
        sig = hmac.new(
            IPPEO_WEBHOOK_SECRET.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        headers["X-Signature"] = f"sha256={sig}"

    urls = []
    if IPPEO_WEBHOOK_URL_DEV:
        urls.append(("DEV", IPPEO_WEBHOOK_URL_DEV))
    if IPPEO_WEBHOOK_URL:
        urls.append(("PROD", IPPEO_WEBHOOK_URL))

    async with httpx.AsyncClient(timeout=15) as client:
        for label, url in urls:
            try:
                start = time.time()
                res = await client.post(url, content=body.encode("utf-8"), headers=headers)
                duration = int((time.time() - start) * 1000)
                results[label] = {
                    "status": "OK" if res.status_code < 300 else "ERROR",
                    "status_code": res.status_code,
                    "latency_ms": duration,
                }
            except Exception as e:
                results[label] = {"status": "ERROR", "error": str(e)}

    all_ok = all(r["status"] == "OK" for r in results.values())
    return {"status": "OK" if all_ok else "ERROR", "servers": results}


async def _check_frontend() -> dict:
    """프론트엔드 접속 확인"""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            start = time.time()
            res = await client.get("https://ippeo-medhim.web.app/")
            duration = int((time.time() - start) * 1000)
            return {
                "status": "OK" if res.status_code < 400 else "ERROR",
                "status_code": res.status_code,
                "latency_ms": duration,
            }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


async def _check_gemini() -> dict:
    """Gemini API 연결 확인"""
    try:
        from services.gemini_client import generate_json
        start = time.time()
        result = await generate_json('Return exactly: {"test": "ok"}', "You are a test assistant. Return valid JSON only.")
        duration = int((time.time() - start) * 1000)
        return {"status": "OK", "latency_ms": duration}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def _build_health_email(checks: dict, now_kst: datetime) -> str:
    """헬스체크 결과 HTML 이메일 생성"""
    date_str = now_kst.strftime("%Y-%m-%d %H:%M KST")

    overall = "OK" if all(c.get("status") == "OK" for c in checks.values()) else "WARNING"
    overall_color = "#22c55e" if overall == "OK" else "#ef4444"
    overall_emoji = "&#9989;" if overall == "OK" else "&#9888;&#65039;"

    # DB 정보
    db = checks.get("database", {})
    db_status_color = "#22c55e" if db.get("status") == "OK" else "#ef4444"
    report_types = db.get("report_types", {})

    # API
    api = checks.get("api", {})
    api_status_color = "#22c55e" if api.get("status") == "OK" else "#ef4444"

    # Webhook
    wh = checks.get("webhook", {})
    wh_status_color = "#22c55e" if wh.get("status") == "OK" else "#ef4444"

    # Frontend
    fe = checks.get("frontend", {})
    fe_status_color = "#22c55e" if fe.get("status") == "OK" else "#ef4444"

    # Gemini
    gm = checks.get("gemini", {})
    gm_status_color = "#22c55e" if gm.get("status") == "OK" else "#ef4444"

    # Webhook server details
    wh_servers = wh.get("servers", {})
    wh_rows = ""
    for label, info in wh_servers.items():
        sc = "#22c55e" if info.get("status") == "OK" else "#ef4444"
        wh_rows += f'<tr><td style="padding:6px 12px;">{label}</td><td style="padding:6px 12px;color:{sc};font-weight:bold;">{info.get("status", "?")}</td><td style="padding:6px 12px;">{info.get("status_code", "-")}</td><td style="padding:6px 12px;">{info.get("latency_ms", "-")}ms</td></tr>'

    # API endpoint details
    api_endpoints = api.get("endpoints", {})
    api_rows = ""
    for name, info in api_endpoints.items():
        sc = "#22c55e" if info.get("status") == "OK" else "#ef4444"
        api_rows += f'<tr><td style="padding:6px 12px;">{name}</td><td style="padding:6px 12px;color:{sc};font-weight:bold;">{info.get("status", "?")}</td><td style="padding:6px 12px;">{info.get("status_code", "-")}</td><td style="padding:6px 12px;">{info.get("latency_ms", "-")}ms</td></tr>'

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Noto Sans KR',sans-serif;background:#f8fafc;margin:0;padding:0;">
<div style="max-width:600px;margin:20px auto;background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06);overflow:hidden;">

<div style="background:linear-gradient(135deg,#1e293b,#334155);padding:24px;text-align:center;color:white;">
  <h1 style="margin:0;font-size:18px;">IPPEO System Health Report</h1>
  <p style="margin:4px 0 0;font-size:12px;opacity:0.8;">{date_str}</p>
</div>

<div style="padding:24px;">

<div style="background:{overall_color}15;border:1px solid {overall_color}40;border-radius:8px;padding:16px;text-align:center;margin-bottom:24px;">
  <span style="font-size:24px;">{overall_emoji}</span>
  <h2 style="margin:8px 0 0;color:{overall_color};font-size:20px;">Overall: {overall}</h2>
</div>

<h3 style="color:#1e293b;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">1. Database</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;">
  <tr><td style="padding:4px 0;color:#64748b;">Status</td><td style="color:{db_status_color};font-weight:bold;">{db.get('status', '?')}</td></tr>
  <tr><td style="padding:4px 0;color:#64748b;">Latency</td><td>{db.get('latency_ms', '-')}ms</td></tr>
  <tr><td style="padding:4px 0;color:#64748b;">Total Consultations</td><td>{db.get('total_consultations', '-')}</td></tr>
  <tr><td style="padding:4px 0;color:#64748b;">Total Reports</td><td>{db.get('total_reports', '-')}</td></tr>
  <tr><td style="padding:4px 0;color:#64748b;">R3 (상담실장)</td><td>{report_types.get('r3', 0)}</td></tr>
  <tr><td style="padding:4px 0;color:#64748b;">R4 (고객용)</td><td>{report_types.get('r4', 0)}</td></tr>
  <tr><td style="padding:4px 0;color:#64748b;">Reports (Last 7 Days)</td><td>{db.get('reports_last_7days', '-')}</td></tr>
  <tr><td style="padding:4px 0;color:#64748b;">Failed Consultations</td><td style="color:{'#ef4444' if db.get('failed_consultations', 0) > 0 else '#22c55e'}">{db.get('failed_consultations', '-')}</td></tr>
</table>

<h3 style="color:#1e293b;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">2. API Endpoints</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;">
  <tr style="background:#f1f5f9;"><th style="padding:6px 12px;text-align:left;">Endpoint</th><th style="padding:6px 12px;text-align:left;">Status</th><th style="padding:6px 12px;text-align:left;">Code</th><th style="padding:6px 12px;text-align:left;">Latency</th></tr>
  {api_rows}
</table>

<h3 style="color:#1e293b;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">3. Webhook Communication</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;">
  <tr style="background:#f1f5f9;"><th style="padding:6px 12px;text-align:left;">Server</th><th style="padding:6px 12px;text-align:left;">Status</th><th style="padding:6px 12px;text-align:left;">Code</th><th style="padding:6px 12px;text-align:left;">Latency</th></tr>
  {wh_rows}
</table>

<h3 style="color:#1e293b;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">4. Frontend</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;">
  <tr><td style="padding:4px 0;color:#64748b;">Status</td><td style="color:{fe_status_color};font-weight:bold;">{fe.get('status', '?')}</td></tr>
  <tr><td style="padding:4px 0;color:#64748b;">Latency</td><td>{fe.get('latency_ms', '-')}ms</td></tr>
</table>

<h3 style="color:#1e293b;border-bottom:2px solid #e2e8f0;padding-bottom:8px;">5. Gemini AI</h3>
<table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;">
  <tr><td style="padding:4px 0;color:#64748b;">Status</td><td style="color:{gm_status_color};font-weight:bold;">{gm.get('status', '?')}</td></tr>
  <tr><td style="padding:4px 0;color:#64748b;">Latency</td><td>{gm.get('latency_ms', '-')}ms</td></tr>
</table>

</div>

<div style="padding:16px 24px;border-top:1px solid #e2e8f0;text-align:center;">
  <p style="font-size:11px;color:#94a3b8;margin:0;">IPPEO MediHim AI Report System | Automated Weekly Health Check</p>
</div>

</div>
</body>
</html>"""


async def _send_health_email(html: str, now_kst: datetime):
    """헬스체크 이메일 발송"""
    date_str = now_kst.strftime("%Y-%m-%d")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[IPPEO] Weekly System Health Report — {date_str}"
    msg["From"] = f"IPPEO System <{GMAIL_ADDRESS}>"
    msg["To"] = HEALTH_REPORT_TO
    msg.attach(MIMEText(html, "html", "utf-8"))

    def _send():
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)

    await asyncio.to_thread(_send)
    logger.info(f"[Health] Weekly report email sent to {HEALTH_REPORT_TO}")


@router.post("/weekly-report")
async def weekly_health_report():
    """주간 시스템 헬스체크 실행 + 이메일 발송 (Cloud Scheduler 호출용)"""
    now_kst = datetime.now(KST)
    logger.info(f"[Health] Starting weekly health check at {now_kst.isoformat()}")

    checks = {}

    # 병렬 실행
    db_task = asyncio.create_task(_check_database())
    api_task = asyncio.create_task(_check_api_endpoints())
    wh_task = asyncio.create_task(_check_webhook())
    fe_task = asyncio.create_task(_check_frontend())
    gm_task = asyncio.create_task(_check_gemini())

    checks["database"] = await db_task
    checks["api"] = await api_task
    checks["webhook"] = await wh_task
    checks["frontend"] = await fe_task
    checks["gemini"] = await gm_task

    overall = "OK" if all(c.get("status") == "OK" for c in checks.values()) else "WARNING"
    logger.info(f"[Health] Check complete: {overall}")

    # 이메일 발송
    try:
        html = _build_health_email(checks, now_kst)
        await _send_health_email(html, now_kst)
    except Exception as e:
        logger.error(f"[Health] Email send failed: {e}")
        checks["email"] = {"status": "ERROR", "error": str(e)}

    return {"overall": overall, "checks": checks, "sent_to": HEALTH_REPORT_TO}


@router.get("/status")
async def health_status():
    """간단한 헬스 상태 (모니터링용)"""
    try:
        db = get_supabase()
        db.table("consultations").select("id").limit(1).execute()
        return {"status": "healthy", "timestamp": datetime.now(KST).isoformat()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
