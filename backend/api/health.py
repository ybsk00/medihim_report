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

HEALTH_REPORT_TO = ["ug_shin@medihim.com", "lumibreeze00@gmail.com"]
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


def _status_badge(status: str) -> str:
    """상태에 따른 HTML 배지 생성"""
    if status == "OK":
        return '<span style="display:inline-block;background:#dcfce7;color:#16a34a;font-size:12px;font-weight:700;padding:3px 10px;border-radius:20px;">정상</span>'
    return '<span style="display:inline-block;background:#fef2f2;color:#dc2626;font-size:12px;font-weight:700;padding:3px 10px;border-radius:20px;">이상</span>'


def _latency_color(ms: int) -> str:
    if ms < 500:
        return "#16a34a"
    if ms < 2000:
        return "#d97706"
    return "#dc2626"


def _build_health_email(checks: dict, now_kst: datetime) -> str:
    """헬스체크 결과 HTML 이메일 생성 (한글 템플릿)"""
    date_str = now_kst.strftime("%Y년 %m월 %d일 %H:%M KST")
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    day_name = day_names[now_kst.weekday()]

    overall = "OK" if all(c.get("status") == "OK" for c in checks.values()) else "WARNING"
    ok_count = sum(1 for c in checks.values() if c.get("status") == "OK")
    total_count = len(checks)

    db = checks.get("database", {})
    api = checks.get("api", {})
    wh = checks.get("webhook", {})
    fe = checks.get("frontend", {})
    gm = checks.get("gemini", {})
    report_types = db.get("report_types", {})

    # 종합 상태 바
    if overall == "OK":
        overall_bg = "linear-gradient(135deg,#22c55e,#16a34a)"
        overall_icon = "&#10003;"
        overall_text = "모든 시스템이 정상 작동 중입니다"
        overall_sub = f"총 {total_count}개 항목 중 {ok_count}개 정상"
    else:
        overall_bg = "linear-gradient(135deg,#ef4444,#dc2626)"
        overall_icon = "!"
        overall_text = "일부 시스템에 이상이 감지되었습니다"
        fail_count = total_count - ok_count
        overall_sub = f"총 {total_count}개 항목 중 {fail_count}개 이상 감지"

    # 웹훅 서버 상세
    wh_servers = wh.get("servers", {})
    wh_rows = ""
    server_labels = {"DEV": "개발 서버 (dev.ippeo.io)", "PROD": "운영 서버 (www.ippeo.io)"}
    for label, info in wh_servers.items():
        badge = _status_badge(info.get("status", "ERROR"))
        lat = info.get("latency_ms", "-")
        lc = _latency_color(lat) if isinstance(lat, int) else "#64748b"
        wh_rows += f'''<tr>
          <td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:13px;">{server_labels.get(label, label)}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;text-align:center;">{badge}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;text-align:center;font-size:13px;color:{lc};font-weight:600;">{lat}ms</td>
        </tr>'''

    # API 엔드포인트 상세
    api_endpoints = api.get("endpoints", {})
    ep_labels = {"root": "메인 API 서버", "dashboard": "대시보드 통계 API"}
    api_rows = ""
    for name, info in api_endpoints.items():
        badge = _status_badge(info.get("status", "ERROR"))
        lat = info.get("latency_ms", "-")
        lc = _latency_color(lat) if isinstance(lat, int) else "#64748b"
        api_rows += f'''<tr>
          <td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;font-size:13px;">{ep_labels.get(name, name)}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;text-align:center;">{badge}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #f1f5f9;text-align:center;font-size:13px;color:{lc};font-weight:600;">{lat}ms</td>
        </tr>'''

    # 리포트 생성 현황
    r3_count = report_types.get("r3", 0)
    r4_count = report_types.get("r4", 0)
    recent_7d = db.get("reports_last_7days", 0)
    failed = db.get("failed_consultations", 0)
    failed_color = "#dc2626" if failed > 0 else "#16a34a"

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Apple SD Gothic Neo','Noto Sans KR','Malgun Gothic',sans-serif;">
<div style="max-width:640px;margin:24px auto;background:#ffffff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">

  <!-- 헤더 -->
  <div style="background:linear-gradient(135deg,#1e293b 0%,#0f172a 100%);padding:32px 28px;text-align:center;">
    <div style="display:inline-block;background:rgba(255,255,255,0.1);border-radius:8px;padding:6px 14px;margin-bottom:12px;">
      <span style="color:rgba(255,255,255,0.7);font-size:11px;letter-spacing:1px;">IPPEO SYSTEM MONITOR</span>
    </div>
    <h1 style="margin:0;font-size:22px;color:#ffffff;font-weight:800;letter-spacing:-0.5px;">주간 시스템 상태 리포트</h1>
    <p style="margin:8px 0 0;font-size:13px;color:rgba(255,255,255,0.6);">{date_str} ({day_name}요일)</p>
  </div>

  <!-- 종합 상태 -->
  <div style="margin:24px;border-radius:12px;overflow:hidden;background:{overall_bg};padding:20px 24px;text-align:center;">
    <div style="display:inline-block;width:40px;height:40px;background:rgba(255,255,255,0.25);border-radius:50%;line-height:40px;font-size:20px;color:#fff;font-weight:900;margin-bottom:8px;">{overall_icon}</div>
    <h2 style="margin:0;color:#ffffff;font-size:18px;font-weight:700;">{overall_text}</h2>
    <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:13px;">{overall_sub}</p>
  </div>

  <div style="padding:0 24px 24px;">

    <!-- 1. 데이터베이스 -->
    <div style="margin-bottom:28px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:18px;">&#128451;</span>
        <h3 style="margin:0;font-size:16px;color:#1e293b;font-weight:700;">데이터베이스</h3>
        {_status_badge(db.get('status', 'ERROR'))}
      </div>
      <p style="margin:0 0 12px;font-size:12px;color:#94a3b8;">Supabase PostgreSQL + pgvector 벡터DB 연결 상태 및 데이터 현황</p>
      <div style="background:#f8fafc;border-radius:10px;padding:16px;border:1px solid #e2e8f0;">
        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#64748b;">응답 속도</td>
            <td style="padding:6px 0;font-size:13px;font-weight:600;text-align:right;color:{_latency_color(db.get('latency_ms', 0))};">{db.get('latency_ms', '-')}ms</td>
          </tr>
          <tr><td colspan="2" style="border-bottom:1px solid #e2e8f0;"></td></tr>
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#64748b;">총 상담 건수</td>
            <td style="padding:6px 0;font-size:13px;font-weight:600;text-align:right;color:#1e293b;">{db.get('total_consultations', '-')}건</td>
          </tr>
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#64748b;">총 리포트 수</td>
            <td style="padding:6px 0;font-size:13px;font-weight:600;text-align:right;color:#1e293b;">{db.get('total_reports', '-')}건</td>
          </tr>
          <tr><td colspan="2" style="border-bottom:1px solid #e2e8f0;"></td></tr>
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#64748b;">R3 상담실장 리포트</td>
            <td style="padding:6px 0;font-size:13px;font-weight:600;text-align:right;color:#7c3aed;">{r3_count}건</td>
          </tr>
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#64748b;">R4 소비자 리포트</td>
            <td style="padding:6px 0;font-size:13px;font-weight:600;text-align:right;color:#e8927c;">{r4_count}건</td>
          </tr>
          <tr><td colspan="2" style="border-bottom:1px solid #e2e8f0;"></td></tr>
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#64748b;">최근 7일 생성 리포트</td>
            <td style="padding:6px 0;font-size:13px;font-weight:600;text-align:right;color:#1e293b;">{recent_7d}건</td>
          </tr>
          <tr>
            <td style="padding:6px 0;font-size:13px;color:#64748b;">실패 상담 건수</td>
            <td style="padding:6px 0;font-size:13px;font-weight:700;text-align:right;color:{failed_color};">{failed}건</td>
          </tr>
        </table>
      </div>
    </div>

    <!-- 2. 리포트 생성 기능 -->
    <div style="margin-bottom:28px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:18px;">&#128196;</span>
        <h3 style="margin:0;font-size:16px;color:#1e293b;font-weight:700;">리포트 생성 현황</h3>
      </div>
      <p style="margin:0 0 12px;font-size:12px;color:#94a3b8;">AI 파이프라인으로 자동 생성되는 R3(상담실장) + R4(소비자) 리포트 상태</p>
      <div style="display:flex;gap:12px;">
        <div style="flex:1;background:linear-gradient(135deg,#f5f3ff,#ede9fe);border-radius:10px;padding:16px;text-align:center;border:1px solid #ddd6fe;">
          <p style="margin:0;font-size:11px;color:#7c3aed;font-weight:600;">3차 상담리포트</p>
          <p style="margin:4px 0 0;font-size:11px;color:#a78bfa;">(상담실장용)</p>
          <p style="margin:8px 0 0;font-size:28px;font-weight:800;color:#6d28d9;">{r3_count}</p>
          <p style="margin:0;font-size:11px;color:#8b5cf6;">R3 | 활성</p>
        </div>
        <div style="flex:1;background:linear-gradient(135deg,#fff7ed,#ffedd5);border-radius:10px;padding:16px;text-align:center;border:1px solid #fed7aa;">
          <p style="margin:0;font-size:11px;color:#ea580c;font-weight:600;">소비자 리포트</p>
          <p style="margin:4px 0 0;font-size:11px;color:#fb923c;">(일본어)</p>
          <p style="margin:8px 0 0;font-size:28px;font-weight:800;color:#c2410c;">{r4_count}</p>
          <p style="margin:0;font-size:11px;color:#f97316;">R4 | 활성</p>
        </div>
      </div>
      <div style="display:flex;gap:12px;margin-top:12px;">
        <div style="flex:1;background:#f8fafc;border-radius:10px;padding:12px;text-align:center;border:1px solid #e2e8f0;">
          <p style="margin:0;font-size:11px;color:#94a3b8;">R1 사전상담 (CS)</p>
          <p style="margin:4px 0 0;font-size:12px;color:#cbd5e1;font-weight:600;">비활성</p>
        </div>
        <div style="flex:1;background:#f8fafc;border-radius:10px;padding:12px;text-align:center;border:1px solid #e2e8f0;">
          <p style="margin:0;font-size:11px;color:#94a3b8;">R2 의료진</p>
          <p style="margin:4px 0 0;font-size:12px;color:#cbd5e1;font-weight:600;">비활성</p>
        </div>
      </div>
    </div>

    <!-- 3. API 서버 -->
    <div style="margin-bottom:28px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:18px;">&#9881;</span>
        <h3 style="margin:0;font-size:16px;color:#1e293b;font-weight:700;">백엔드 API 서버</h3>
        {_status_badge(api.get('status', 'ERROR'))}
      </div>
      <p style="margin:0 0 12px;font-size:12px;color:#94a3b8;">Google Cloud Run 기반 FastAPI 백엔드 엔드포인트 응답 상태</p>
      <div style="background:#f8fafc;border-radius:10px;overflow:hidden;border:1px solid #e2e8f0;">
        <table style="width:100%;border-collapse:collapse;">
          <tr style="background:#f1f5f9;">
            <th style="padding:10px 14px;text-align:left;font-size:12px;color:#64748b;font-weight:600;">엔드포인트</th>
            <th style="padding:10px 14px;text-align:center;font-size:12px;color:#64748b;font-weight:600;">상태</th>
            <th style="padding:10px 14px;text-align:center;font-size:12px;color:#64748b;font-weight:600;">응답속도</th>
          </tr>
          {api_rows}
        </table>
      </div>
    </div>

    <!-- 4. 웹훅 통신 -->
    <div style="margin-bottom:28px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:18px;">&#128279;</span>
        <h3 style="margin:0;font-size:16px;color:#1e293b;font-weight:700;">이뽀앱 웹훅 통신</h3>
        {_status_badge(wh.get('status', 'ERROR'))}
      </div>
      <p style="margin:0 0 12px;font-size:12px;color:#94a3b8;">이뽀 앱과의 실시간 리포트 전송 연동 (HMAC 서명 + API Key 인증)</p>
      <div style="background:#f8fafc;border-radius:10px;overflow:hidden;border:1px solid #e2e8f0;">
        <table style="width:100%;border-collapse:collapse;">
          <tr style="background:#f1f5f9;">
            <th style="padding:10px 14px;text-align:left;font-size:12px;color:#64748b;font-weight:600;">서버</th>
            <th style="padding:10px 14px;text-align:center;font-size:12px;color:#64748b;font-weight:600;">상태</th>
            <th style="padding:10px 14px;text-align:center;font-size:12px;color:#64748b;font-weight:600;">응답속도</th>
          </tr>
          {wh_rows}
        </table>
      </div>
    </div>

    <!-- 5. 프론트엔드 -->
    <div style="margin-bottom:28px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:18px;">&#127760;</span>
        <h3 style="margin:0;font-size:16px;color:#1e293b;font-weight:700;">프론트엔드 웹서비스</h3>
        {_status_badge(fe.get('status', 'ERROR'))}
      </div>
      <p style="margin:0 0 12px;font-size:12px;color:#94a3b8;">Firebase Hosting 기반 관리자페이지 + 소비자 리포트 웹 접속 상태</p>
      <div style="background:#f8fafc;border-radius:10px;padding:16px;border:1px solid #e2e8f0;">
        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="padding:4px 0;font-size:13px;color:#64748b;">서비스 URL</td>
            <td style="padding:4px 0;font-size:13px;text-align:right;color:#3b82f6;">ippeo-medhim.web.app</td>
          </tr>
          <tr>
            <td style="padding:4px 0;font-size:13px;color:#64748b;">응답 속도</td>
            <td style="padding:4px 0;font-size:13px;font-weight:600;text-align:right;color:{_latency_color(fe.get('latency_ms', 0))};">{fe.get('latency_ms', '-')}ms</td>
          </tr>
        </table>
      </div>
    </div>

    <!-- 6. AI 엔진 -->
    <div style="margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span style="font-size:18px;">&#129302;</span>
        <h3 style="margin:0;font-size:16px;color:#1e293b;font-weight:700;">Gemini AI 엔진</h3>
        {_status_badge(gm.get('status', 'ERROR'))}
      </div>
      <p style="margin:0 0 12px;font-size:12px;color:#94a3b8;">Google Gemini API 기반 리포트 생성 AI 모델 연결 상태</p>
      <div style="background:#f8fafc;border-radius:10px;padding:16px;border:1px solid #e2e8f0;">
        <table style="width:100%;border-collapse:collapse;">
          <tr>
            <td style="padding:4px 0;font-size:13px;color:#64748b;">모델</td>
            <td style="padding:4px 0;font-size:13px;text-align:right;color:#1e293b;">Gemini (텍스트 + 임베딩)</td>
          </tr>
          <tr>
            <td style="padding:4px 0;font-size:13px;color:#64748b;">응답 속도</td>
            <td style="padding:4px 0;font-size:13px;font-weight:600;text-align:right;color:{_latency_color(gm.get('latency_ms', 0))};">{gm.get('latency_ms', '-')}ms</td>
          </tr>
        </table>
      </div>
    </div>

  </div>

  <!-- 푸터 -->
  <div style="background:#f8fafc;padding:20px 24px;border-top:1px solid #e2e8f0;text-align:center;">
    <p style="margin:0 0 4px;font-size:12px;color:#64748b;font-weight:600;">IPPEO MediHim AI Report System</p>
    <p style="margin:0;font-size:11px;color:#94a3b8;">매주 금요일 18:10 KST 자동 발송 | Cloud Scheduler</p>
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
    msg["To"] = ", ".join(HEALTH_REPORT_TO)
    msg.attach(MIMEText(html, "html", "utf-8"))

    def _send():
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, HEALTH_REPORT_TO, msg.as_string())

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
