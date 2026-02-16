from fastapi import APIRouter
from services.supabase_client import get_supabase

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats():
    db = get_supabase()

    # 1개 쿼리로 모든 상담 데이터 가져오기 (status, cta_level만)
    all_consultations = []
    offset = 0
    while True:
        page = (
            db.table("consultations")
            .select("id, customer_name, classification, cta_level, status, created_at")
            .order("created_at", desc=True)
            .range(offset, offset + 999)
            .execute()
        )
        all_consultations.extend(page.data)
        if len(page.data) < 1000:
            break
        offset += 1000

    # Python에서 카운팅 (DB 왕복 1회로 끝남)
    total_count = len(all_consultations)
    registered_count = 0
    unclassified_count = 0
    report_pending_count = 0
    sent_count = 0
    cta_hot = 0
    cta_warm = 0
    cta_cool = 0

    for c in all_consultations:
        status = c.get("status", "")
        cta = c.get("cta_level", "")

        if status == "registered":
            registered_count += 1
        elif status == "classification_pending":
            unclassified_count += 1
        elif status == "report_ready":
            report_pending_count += 1
        elif status == "report_sent":
            sent_count += 1

        if cta == "hot":
            cta_hot += 1
        elif cta == "warm":
            cta_warm += 1
        elif cta == "cool":
            cta_cool += 1

    # 열람률 (reports 테이블에서 1개만 쿼리)
    viewed_count = 0
    if sent_count > 0:
        viewed = (
            db.table("reports")
            .select("id", count="exact")
            .not_.is_("email_opened_at", "null")
            .execute()
        )
        viewed_count = viewed.count or 0
    view_rate = (viewed_count / sent_count * 100) if sent_count > 0 else 0.0

    # 최근 10건 (이미 created_at desc로 정렬됨)
    recent = all_consultations[:10]

    return {
        "total_consultations": total_count,
        "registered_count": registered_count,
        "unclassified_count": unclassified_count,
        "report_pending_count": report_pending_count,
        "sent_count": sent_count,
        "view_rate": round(view_rate, 1),
        "cta_hot": cta_hot,
        "cta_warm": cta_warm,
        "cta_cool": cta_cool,
        "recent_consultations": recent,
    }
