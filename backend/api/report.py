from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from models.schemas import ReportEditRequest
from services.supabase_client import get_supabase
from services.email_service import send_report_email
from agents.korean_translator import translate_report_to_korean

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("")
async def list_reports():
    db = get_supabase()
    result = (
        db.table("reports")
        .select("*, consultations(customer_name, customer_email, classification)")
        .order("created_at", desc=True)
        .execute()
    )
    return {"data": result.data}


@router.get("/{report_id}")
async def get_report(report_id: str):
    db = get_supabase()
    result = (
        db.table("reports")
        .select("*, consultations(customer_name, customer_email, customer_line_id, classification, cta_level)")
        .eq("id", report_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    return result.data


@router.put("/{report_id}/approve")
async def approve_report(report_id: str):
    """리포트 승인 (이메일 발송 없이 승인만)"""
    db = get_supabase()

    report = (
        db.table("reports")
        .select("id, status, consultation_id, access_token")
        .eq("id", report_id)
        .single()
        .execute()
    )

    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.data["status"] not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="이 상태에서는 승인할 수 없습니다")

    db.table("reports").update({
        "status": "approved",
    }).eq("id", report_id).execute()

    db.table("consultations").update({
        "status": "report_approved",
    }).eq("id", report.data["consultation_id"]).execute()

    return {
        "id": report_id,
        "status": "approved",
        "access_token": report.data["access_token"],
    }


@router.post("/{report_id}/send-email")
async def send_email(report_id: str):
    """승인된 리포트에 대해 이메일 발송"""
    db = get_supabase()

    report = (
        db.table("reports")
        .select("*, consultations(customer_name, customer_email)")
        .eq("id", report_id)
        .single()
        .execute()
    )

    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.data["status"] not in ("approved", "sent"):
        raise HTTPException(status_code=400, detail="승인된 리포트만 발송할 수 있습니다")

    consultation = report.data["consultations"]
    access_token = report.data["access_token"]

    try:
        await send_report_email(
            to_email=consultation["customer_email"],
            customer_name=consultation["customer_name"],
            access_token=access_token,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"이메일 발송 실패: {str(e)}")

    now = datetime.now(timezone.utc).isoformat()
    db.table("reports").update({
        "status": "sent",
        "email_sent_at": now,
    }).eq("id", report_id).execute()

    db.table("consultations").update({
        "status": "report_sent",
    }).eq("id", report.data["consultation_id"]).execute()

    return {
        "id": report_id,
        "status": "sent",
        "email_sent_to": consultation["customer_email"],
        "access_token": access_token,
    }


@router.put("/{report_id}/reject")
async def reject_report(report_id: str):
    db = get_supabase()

    result = db.table("reports").update({
        "status": "rejected",
    }).eq("id", report_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"id": report_id, "status": "rejected"}


@router.put("/{report_id}/edit")
async def edit_report(report_id: str, data: ReportEditRequest):
    db = get_supabase()

    result = db.table("reports").update({
        "report_data": data.report_data,
    }).eq("id", report_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"id": report_id, "updated": True}


@router.get("/{report_id}/translate")
async def translate_report(report_id: str):
    db = get_supabase()

    report = db.table("reports").select("report_data, report_data_ko").eq("id", report_id).single().execute()

    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")

    # 캐시 확인
    if report.data.get("report_data_ko"):
        return {"report_data_ko": report.data["report_data_ko"], "cached": True}

    # LLM 번역
    report_data_ko = await translate_report_to_korean(report.data["report_data"])

    # 캐시 저장
    db.table("reports").update({
        "report_data_ko": report_data_ko,
    }).eq("id", report_id).execute()

    return {"report_data_ko": report_data_ko, "cached": False}
