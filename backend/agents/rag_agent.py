from services.gemini_client import get_query_embedding
from services.supabase_client import get_supabase


async def search_relevant_faq(
    keywords: list[str],
    category: str,
    match_threshold: float = 0.7,
    match_count: int = 5,
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

    if result.data:
        return result.data

    # 안전 폴백: 결과가 없으면 빈 배열
    return []
