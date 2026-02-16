-- ============================================
-- search_faq RPC 함수 업데이트
-- youtube_title, youtube_video_id 컬럼 추가 반환
-- PubMed 논문 출처 표시를 위해 필요
-- ============================================

CREATE OR REPLACE FUNCTION search_faq(
    query_embedding vector(768),
    target_category TEXT,
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    question TEXT,
    answer TEXT,
    procedure_name TEXT,
    youtube_url TEXT,
    youtube_title TEXT,
    youtube_video_id TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        fv.id,
        fv.question,
        fv.answer,
        fv.procedure_name,
        fv.youtube_url,
        fv.youtube_title,
        fv.youtube_video_id,
        1 - (fv.embedding <=> query_embedding) AS similarity
    FROM faq_vectors fv
    WHERE fv.category = target_category
        AND 1 - (fv.embedding <=> query_embedding) > match_threshold
    ORDER BY fv.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
