from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from typing import Optional
from models.schemas import ConsultationCreate, ConsultationBulkCreate, ClassifyRequest, CTAUpdateRequest
from services.supabase_client import get_supabase
from agents.pipeline import run_pipeline, resume_pipeline

router = APIRouter(prefix="/api/consultations", tags=["consultations"])


@router.post("")
async def create_consultation(data: ConsultationCreate, background_tasks: BackgroundTasks):
    db = get_supabase()

    result = db.table("consultations").insert(
        {
            "customer_id": data.customer_id,
            "customer_name": data.customer_name,
            "customer_email": data.customer_email,
            "customer_line_id": data.customer_line_id,
            "original_text": data.original_text,
            "status": "processing",
        }
    ).execute()

    consultation = result.data[0]

    # 백그라운드에서 파이프라인 실행
    background_tasks.add_task(run_pipeline, consultation["id"])

    return {"id": consultation["id"], "status": "processing"}


@router.post("/bulk")
async def create_consultations_bulk(data: ConsultationBulkCreate, background_tasks: BackgroundTasks):
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
            "status": "processing",
        }
        for c in data.consultations
    ]

    result = db.table("consultations").insert(rows).execute()

    created_ids = []
    for consultation in result.data:
        created_ids.append(consultation["id"])
        background_tasks.add_task(run_pipeline, consultation["id"])

    return {"created": len(created_ids), "ids": created_ids}


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
