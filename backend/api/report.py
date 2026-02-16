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
    db = get_supabase()

    # 리포트 조회
    report = (
        db.table("reports")
        .select("*, consultations(customer_name, customer_email)")
        .eq("id", report_id)
        .single()
        .execute()
    )

    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.data["status"] not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="Report cannot be approved in current status")

    consultation = report.data["consultations"]
    access_token = report.data["access_token"]

    # 이메일 발송
    email_error = None
    try:
        await send_report_email(
            to_email=consultation["customer_email"],
            customer_name=consultation["customer_name"],
            access_token=access_token,
        )
    except Exception as e:
        email_error = str(e)

    # 상태 업데이트 (이메일 실패와 무관하게 승인 처리)
    now = datetime.now(timezone.utc).isoformat()
    db.table("reports").update({
        "status": "sent",
        "email_sent_at": now if not email_error else None,
    }).eq("id", report_id).execute()

    db.table("consultations").update({
        "status": "report_sent",
    }).eq("id", report.data["consultation_id"]).execute()

    result = {
        "id": report_id,
        "status": "sent",
        "email_sent_to": consultation["customer_email"],
        "access_token": access_token,
    }
    if email_error:
        result["email_error"] = email_error

    return result


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
