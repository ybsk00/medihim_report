from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.schemas import ReportEditRequest, ReportRegenerateRequest, BulkApproveRequest


class DeleteReportsRequest(BaseModel):
    report_ids: List[str]
from services.supabase_client import get_supabase
from services.email_service import send_report_email
from agents.korean_translator import translate_report_to_korean
from agents.pipeline import regenerate_report

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


@router.post("/delete")
async def delete_reports(data: DeleteReportsRequest):
    """선택한 리포트 삭제"""
    if not data.report_ids:
        raise HTTPException(status_code=400, detail="삭제할 리포트 ID가 없습니다")

    db = get_supabase()
    result = db.table("reports").delete().in_("id", data.report_ids).execute()

    return {"deleted": len(result.data), "ids": [r["id"] for r in result.data]}


@router.post("/bulk-approve")
async def bulk_approve_reports(data: BulkApproveRequest):
    """선택한 리포트 일괄 승인 (이메일 발송 없이)"""
    if not data.report_ids:
        raise HTTPException(status_code=400, detail="승인할 리포트 ID가 없습니다")

    db = get_supabase()

    approved_ids = []
    skipped = []

    for report_id in data.report_ids:
        report = db.table("reports").select("id, status, consultation_id").eq("id", report_id).single().execute()
        if not report.data:
            skipped.append({"id": report_id, "reason": "리포트를 찾을 수 없습니다"})
            continue

        if report.data["status"] not in ("draft", "rejected"):
            skipped.append({"id": report_id, "reason": f"승인 불가 상태: {report.data['status']}"})
            continue

        db.table("reports").update({"status": "approved"}).eq("id", report_id).execute()
        db.table("consultations").update({"status": "report_approved"}).eq("id", report.data["consultation_id"]).execute()
        approved_ids.append(report_id)

    return {
        "approved": len(approved_ids),
        "approved_ids": approved_ids,
        "skipped": skipped,
    }


@router.get("/{report_id}")
async def get_report(report_id: str):
    db = get_supabase()
    # 1차: report_id로 조회
    result = (
        db.table("reports")
        .select("*, consultations(customer_name, customer_email, customer_line_id, classification, cta_level)")
        .eq("id", report_id)
        .maybe_single()
        .execute()
    )

    if result.data:
        return result.data

    # 2차: consultation_id로 조회 (상담 상세에서 리포트 보기 링크용)
    result = (
        db.table("reports")
        .select("*, consultations(customer_name, customer_email, customer_line_id, classification, cta_level)")
        .eq("consultation_id", report_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if result.data and len(result.data) > 0:
        return result.data[0]

    raise HTTPException(status_code=404, detail="Report not found")


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


@router.post("/{report_id}/regenerate")
async def regenerate_report_endpoint(
    report_id: str,
    data: ReportRegenerateRequest,
    background_tasks: BackgroundTasks,
):
    """관리자 피드백 기반 리포트 재생성"""
    db = get_supabase()

    report = (
        db.table("reports")
        .select("id, status, consultation_id")
        .eq("id", report_id)
        .single()
        .execute()
    )

    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")

    allowed_statuses = {"draft", "rejected", "approved"}
    if report.data["status"] not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"이 상태({report.data['status']})에서는 재생성할 수 없습니다",
        )

    if not data.direction or not data.direction.strip():
        raise HTTPException(status_code=400, detail="재생성 방향을 입력해주세요")

    # 상태를 재생성 중으로 변경
    db.table("reports").update({"status": "draft"}).eq("id", report_id).execute()
    db.table("consultations").update(
        {"status": "report_generating"}
    ).eq("id", report.data["consultation_id"]).execute()

    background_tasks.add_task(regenerate_report, report_id, data.direction.strip())

    return {
        "id": report_id,
        "status": "regenerating",
        "message": "리포트 재생성이 시작되었습니다",
    }


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
