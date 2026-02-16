from services.gemini_client import get_query_embedding
from services.supabase_client import get_supabase


async def search_relevant_faq(
    keywords: list[str],
    category: str,
    match_threshold: float = 0.65,
    match_count: int = 8,
) -> list[dict]:
    db = get_supabase()

    # 키워드를 하나의 검색 쿼리로 결합
    query_text = " ".join(keywords)
    embedding = await get_query_embedding(query_text)

    # Supabase RPC로 벡터 검색
    result = db.rpc(
        "search_faq",
        {
            "query_embedding": embedding,
            "target_category": category,
            "match_threshold": match_threshold,
            "match_count": match_count,
        },
    ).execute()

    if not result.data:
        return []

    # RPC 결과에 youtube_title, youtube_video_id가 없을 수 있으므로
    # id 목록으로 추가 정보 조회
    faq_ids = [faq["id"] for faq in result.data]
    extra_result = db.table("faq_vectors").select(
        "id, youtube_title, youtube_video_id, youtube_url"
    ).in_("id", faq_ids).execute()

    extra_map = {}
    if extra_result.data:
        for row in extra_result.data:
            extra_map[row["id"]] = row

    # source_type 태깅: PubMed vs YouTube 구분
    tagged_results = []
    for faq in result.data:
        faq_id = faq["id"]
        extra = extra_map.get(faq_id, {})

        # RPC에 없는 필드를 추가 조회에서 병합
        if "youtube_title" not in faq:
            faq["youtube_title"] = extra.get("youtube_title", "")
        if "youtube_video_id" not in faq:
            faq["youtube_video_id"] = extra.get("youtube_video_id", "")

        url = faq.get("youtube_url", "") or ""
        if "pubmed.ncbi.nlm.nih.gov" in url:
            faq["source_type"] = "pubmed"
            faq["paper_title"] = faq.get("youtube_title", "")
            faq["pmid"] = faq.get("youtube_video_id", "")
        else:
            faq["source_type"] = "youtube"
        tagged_results.append(faq)

    return tagged_results
