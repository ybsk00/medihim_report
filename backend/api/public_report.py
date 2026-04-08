from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from models.schemas import BirthDateVerify
from services.supabase_client import get_supabase

router = APIRouter(prefix="/api/public/report", tags=["public_report"])


@router.get("/{token}")
async def get_public_report(token: str):
    db = get_supabase()

    report = (
        db.table("reports")
        .select("id, report_data, access_expires_at, status, consultations(customer_name)")
        .eq("access_token", token)
        .single()
        .execute()
    )

    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")

    # 발송된 리포트만 열람 가능
    if report.data["status"] not in ("sent", "approved"):
        raise HTTPException(status_code=403, detail="Report is not available yet")

    return {
        "report_data": report.data["report_data"],
        "customer_name": report.data["consultations"]["customer_name"],
    }


@router.post("/{token}/verify")
async def verify_report_access(token: str, data: BirthDateVerify):
    # 현재는 토큰만으로 검증. 추후 생년월일 검증 추가 가능
    db = get_supabase()

    report = (
        db.table("reports")
        .select("id, access_expires_at, status")
        .eq("access_token", token)
        .single()
        .execute()
    )

    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"verified": True, "report_id": report.data["id"]}


@router.post("/{token}/opened")
async def track_report_opened(token: str):
    db = get_supabase()

    now = datetime.now(timezone.utc).isoformat()
    result = (
        db.table("reports")
        .update({"email_opened_at": now})
        .eq("access_token", token)
        .is_("email_opened_at", "null")
        .execute()
    )

    return {"tracked": True}


@router.get("/embed/{token}")
async def get_embed_report(token: str, lang: str = "ja"):
    """iframe 임베딩용 리포트 데이터 조회 (승인 전이라도 열람 가능)"""
    db = get_supabase()

    report = (
        db.table("reports")
        .select("id, report_data, report_data_ko, report_type, access_expires_at, status, consultations(customer_name, consultation_round)")
        .eq("access_token", token)
        .single()
        .execute()
    )

    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")

    # draft 이상이면 열람 가능 (iframe 임베딩은 승인 전에도 미리보기 허용)
    if report.data["status"] not in ("draft", "approved", "sent"):
        raise HTTPException(status_code=403, detail="Report is not available")

    # 언어별 데이터 반환
    report_data = report.data["report_data"]
    if lang == "ko" and report.data.get("report_data_ko"):
        report_data = report.data["report_data_ko"]

    # 열람 추적
    now = datetime.now(timezone.utc).isoformat()
    db.table("reports").update({"email_opened_at": now}).eq("access_token", token).is_("email_opened_at", "null").execute()

    consultation = report.data["consultations"]
    return {
        "report_data": report_data,
        "report_type": report.data.get("report_type", "r4"),
        "customer_name": consultation["customer_name"],
        "consultation_round": consultation.get("consultation_round") or 3,
        "lang": lang,
    }
