from fastapi import APIRouter
from services.supabase_client import get_supabase

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats():
    db = get_supabase()

    # 총 상담 수
    total = db.table("consultations").select("id", count="exact").execute()
    total_count = total.count or 0

    # 미분류 대기
    unclassified = (
        db.table("consultations")
        .select("id", count="exact")
        .eq("status", "classification_pending")
        .execute()
    )
    unclassified_count = unclassified.count or 0

    # 리포트 대기 (report_ready)
    report_pending = (
        db.table("consultations")
        .select("id", count="exact")
        .eq("status", "report_ready")
        .execute()
    )
    report_pending_count = report_pending.count or 0

    # 발송 완료
    sent = (
        db.table("consultations")
        .select("id", count="exact")
        .eq("status", "report_sent")
        .execute()
    )
    sent_count = sent.count or 0

    # 열람률
    viewed = (
        db.table("reports")
        .select("id", count="exact")
        .not_.is_("email_opened_at", "null")
        .execute()
    )
    viewed_count = viewed.count or 0
    view_rate = (viewed_count / sent_count * 100) if sent_count > 0 else 0.0

    # CTA 현황
    cta_hot = db.table("consultations").select("id", count="exact").eq("cta_level", "hot").execute()
    cta_warm = db.table("consultations").select("id", count="exact").eq("cta_level", "warm").execute()
    cta_cool = db.table("consultations").select("id", count="exact").eq("cta_level", "cool").execute()

    # 최근 상담 10건
    recent = (
        db.table("consultations")
        .select("id, customer_name, classification, cta_level, status, created_at")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    return {
        "total_consultations": total_count,
        "unclassified_count": unclassified_count,
        "report_pending_count": report_pending_count,
        "sent_count": sent_count,
        "view_rate": round(view_rate, 1),
        "cta_hot": cta_hot.count or 0,
        "cta_warm": cta_warm.count or 0,
        "cta_cool": cta_cool.count or 0,
        "recent_consultations": recent.data,
    }
