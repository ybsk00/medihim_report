import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from typing import Optional
from models.schemas import ConsultationCreate, ConsultationBulkCreate, ClassifyRequest, CTAUpdateRequest, GenerateReportsRequest
from services.supabase_client import get_supabase
from agents.pipeline import run_pipeline, resume_pipeline


async def _run_pipelines_parallel(consultation_ids: list[str], concurrency: int = 5):
    """파이프라인을 동시성 제한하여 병렬 실행"""
    semaphore = asyncio.Semaphore(concurrency)

    async def _run_one(cid: str):
        async with semaphore:
            await run_pipeline(cid)

    await asyncio.gather(*[_run_one(cid) for cid in consultation_ids], return_exceptions=True)

router = APIRouter(prefix="/api/consultations", tags=["consultations"])


@router.post("")
async def create_consultation(data: ConsultationCreate):
    db = get_supabase()

    result = db.table("consultations").insert(
        {
            "customer_id": data.customer_id,
            "customer_name": data.customer_name,
            "customer_email": data.customer_email,
            "customer_line_id": data.customer_line_id,
            "original_text": data.original_text,
            "status": "registered",
        }
    ).execute()

    consultation = result.data[0]

    return {"id": consultation["id"], "status": "registered"}


@router.post("/bulk")
async def create_consultations_bulk(data: ConsultationBulkCreate):
    if len(data.consultations) > 100:
        raise HTTPException(status_code=400, detail="최대 100건까지 일괄 등록 가능합니다")

    if len(data.consultations) == 0:
        raise HTTPException(status_code=400, detail="등록할 상담 데이터가 없습니다")

    db = get_supabase()
    rows = [
        {
            "customer_id": c.customer_id,
            "customer_name": c.customer_name,
            "customer_email": c.customer_email,
            "customer_line_id": c.customer_line_id,
            "original_text": c.original_text,
            "status": "registered",
        }
        for c in data.consultations
    ]

    result = db.table("consultations").insert(rows).execute()

    created_ids = [consultation["id"] for consultation in result.data]

    return {"created": len(created_ids), "ids": created_ids}


@router.post("/generate-reports")
async def generate_reports(data: GenerateReportsRequest, background_tasks: BackgroundTasks):
    """선택한 상담건에 대해 AI 리포트 생성 파이프라인 실행"""
    if len(data.consultation_ids) == 0:
        raise HTTPException(status_code=400, detail="생성할 상담 ID가 없습니다")
    if len(data.consultation_ids) > 50:
        raise HTTPException(status_code=400, detail="최대 50건까지 일괄 생성 가능합니다")

    db = get_supabase()

    result = db.table("consultations").select("id, status").in_("id", data.consultation_ids).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="해당 상담을 찾을 수 없습니다")

    found_ids = {row["id"] for row in result.data}
    missing = set(data.consultation_ids) - found_ids
    if missing:
        raise HTTPException(status_code=404, detail=f"찾을 수 없는 상담 ID: {list(missing)}")

    valid_statuses = {"registered", "report_failed"}
    triggered_ids = []
    skipped = []

    for row in result.data:
        if row["status"] in valid_statuses:
            db.table("consultations").update({"status": "processing"}).eq("id", row["id"]).execute()
            triggered_ids.append(row["id"])
        else:
            skipped.append({
                "id": row["id"],
                "status": row["status"],
                "reason": "이미 처리 중이거나 완료된 상담입니다",
            })

    # 병렬 실행 (최대 5건 동시)
    if triggered_ids:
        background_tasks.add_task(_run_pipelines_parallel, triggered_ids, 5)

    return {
        "triggered": len(triggered_ids),
        "triggered_ids": triggered_ids,
        "skipped": skipped,
    }


@router.get("")
async def list_consultations(
    classification: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    db = get_supabase()
    query = db.table("consultations").select("*", count="exact")

    if classification:
        query = query.eq("classification", classification)
    if status:
        query = query.eq("status", status)

    offset = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)

    result = query.execute()
    return {
        "data": result.data,
        "total": result.count,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{consultation_id}")
async def get_consultation(consultation_id: str):
    db = get_supabase()
    result = db.table("consultations").select("*").eq("id", consultation_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Consultation not found")

    return result.data


@router.put("/{consultation_id}/classify")
async def classify_consultation(
    consultation_id: str,
    data: ClassifyRequest,
    background_tasks: BackgroundTasks,
):
    db = get_supabase()

    # 상담 존재 확인
    consultation = db.table("consultations").select("status").eq("id", consultation_id).single().execute()
    if not consultation.data:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if consultation.data["status"] != "classification_pending":
        raise HTTPException(status_code=400, detail="Consultation is not pending classification")

    # 수동 분류 후 파이프라인 재개
    background_tasks.add_task(resume_pipeline, consultation_id, data.classification)

    return {"id": consultation_id, "status": "report_generating"}


@router.put("/{consultation_id}/cta")
async def update_cta(consultation_id: str, data: CTAUpdateRequest):
    db = get_supabase()

    result = db.table("consultations").update(
        {"cta_level": data.cta_level}
    ).eq("id", consultation_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Consultation not found")

    return {"id": consultation_id, "cta_level": data.cta_level}
