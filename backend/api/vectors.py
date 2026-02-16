from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from services.supabase_client import get_supabase

router = APIRouter(prefix="/api/vectors", tags=["vectors"])


class BulkDeleteRequest(BaseModel):
    ids: List[str]


@router.get("")
async def list_vectors(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
):
    db = get_supabase()
    offset = (page - 1) * page_size

    # 총 개수 조회
    count_query = db.table("faq_vectors").select("id", count="exact")
    if category:
        count_query = count_query.eq("category", category)
    count_result = count_query.execute()
    total = count_result.count or 0

    # 데이터 조회 (embedding 제외)
    data_query = db.table("faq_vectors").select(
        "id, category, question, answer, procedure_name, youtube_video_id, youtube_title, youtube_url, created_at"
    ).order("created_at", desc=True).range(offset, offset + page_size - 1)

    if category:
        data_query = data_query.eq("category", category)

    result = data_query.execute()

    return {
        "data": result.data,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/{vector_id}")
async def delete_vector(vector_id: str):
    db = get_supabase()

    existing = db.table("faq_vectors").select("id").eq("id", vector_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="벡터를 찾을 수 없습니다")

    db.table("faq_vectors").delete().eq("id", vector_id).execute()
    return {"deleted": True, "id": vector_id}


@router.post("/bulk-delete")
async def bulk_delete_vectors(data: BulkDeleteRequest):
    if not data.ids:
        raise HTTPException(status_code=400, detail="삭제할 ID를 지정해주세요")
    if len(data.ids) > 100:
        raise HTTPException(status_code=400, detail="한번에 최대 100건까지 삭제 가능합니다")

    db = get_supabase()
    db.table("faq_vectors").delete().in_("id", data.ids).execute()
    return {"deleted": len(data.ids), "ids": data.ids}
