from fastapi import APIRouter
from services.supabase_client import get_supabase

router = APIRouter(prefix="/api/unclassified", tags=["unclassified"])


@router.get("")
async def list_unclassified():
    db = get_supabase()
    result = (
        db.table("consultations")
        .select("id, customer_name, created_at, intent_extraction, original_text")
        .eq("status", "classification_pending")
        .order("created_at", desc=True)
        .execute()
    )

    items = []
    for c in result.data:
        intent = c.get("intent_extraction") or {}
        keywords = intent.get("keywords", [])
        original = c.get("original_text", "")
        preview = original[:150] + "..." if len(original) > 150 else original

        items.append({
            "id": c["id"],
            "name": c["customer_name"],
            "date": c["created_at"],
            "keywords": keywords,
            "preview": preview,
            "full_text": original,
        })

    return {"data": items, "count": len(items)}
