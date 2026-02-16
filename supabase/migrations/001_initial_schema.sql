-- ============================================
-- 메디힘 이뽀 (MediHim Ippo) — 초기 DB 스키마
-- ============================================

-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- 1. 상담 테이블
-- ============================================
CREATE TABLE consultations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_line_id TEXT,

    -- 원문 및 번역
    original_text TEXT NOT NULL,
    translated_text TEXT,

    -- 화자 분리 데이터
    speaker_segments JSONB,
    customer_utterances TEXT,

    -- AI 분류 결과
    classification TEXT CHECK (classification IN ('dermatology', 'plastic_surgery', 'unclassified')),
    classification_confidence FLOAT,
    classification_reason TEXT,
    is_manually_classified BOOLEAN DEFAULT FALSE,

    -- AI 의도 추출 결과
    intent_extraction JSONB,

    -- CTA 분석 (고객 발화 기반)
    cta_level TEXT CHECK (cta_level IN ('hot', 'warm', 'cool')),
    cta_signals JSONB,

    -- 상태
    status TEXT DEFAULT 'processing' CHECK (status IN (
        'processing',
        'classification_pending',
        'report_generating',
        'report_ready',
        'report_approved',
        'report_sent',
        'report_failed'
    )),
    error_message TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. 리포트 테이블
-- ============================================
CREATE TABLE reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    consultation_id UUID REFERENCES consultations(id) ON DELETE CASCADE,

    -- 리포트 내용 (7섹션)
    report_data JSONB NOT NULL,

    -- 한국어 번역본
    report_data_ko JSONB,

    -- RAG 컨텍스트
    rag_context JSONB,

    -- 검토 상태
    review_count INT DEFAULT 0,
    review_passed BOOLEAN DEFAULT FALSE,
    review_notes TEXT,

    -- 발송 정보
    access_token TEXT UNIQUE,
    access_expires_at TIMESTAMPTZ,

    -- 이메일 발송
    email_sent_at TIMESTAMPTZ,
    email_opened_at TIMESTAMPTZ,

    -- 상태
    status TEXT DEFAULT 'draft' CHECK (status IN (
        'draft',
        'approved',
        'rejected',
        'sent'
    )),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 3. 벡터DB - FAQ 테이블 (YouTube 기반)
-- ============================================
CREATE TABLE faq_vectors (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

    category TEXT NOT NULL CHECK (category IN ('dermatology', 'plastic_surgery')),

    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    procedure_name TEXT,

    embedding vector(768) NOT NULL,

    youtube_video_id TEXT,
    youtube_title TEXT,
    youtube_url TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 벡터 검색 인덱스
CREATE INDEX idx_faq_vectors_embedding ON faq_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 카테고리 필터 인덱스
CREATE INDEX idx_faq_vectors_category ON faq_vectors (category);

-- ============================================
-- 4. YouTube 소스 관리 테이블
-- ============================================
CREATE TABLE youtube_sources (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    video_id TEXT UNIQUE NOT NULL,
    title TEXT,
    url TEXT,
    channel_name TEXT,
    category TEXT CHECK (category IN ('dermatology', 'plastic_surgery')),

    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending',
        'transcript_fetched',
        'refined',
        'faq_generated',
        'embedded',
        'skipped',
        'failed'
    )),

    raw_transcript TEXT,
    refined_transcript TEXT,
    faq_count INT DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 5. 분류 키워드 사전 테이블
-- ============================================
CREATE TABLE classification_keywords (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category TEXT NOT NULL CHECK (category IN ('dermatology', 'plastic_surgery', 'boundary')),
    keyword TEXT NOT NULL,
    context_keywords JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 6. 에이전트 처리 로그 테이블
-- ============================================
CREATE TABLE agent_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    consultation_id UUID REFERENCES consultations(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,
    input_data JSONB,
    output_data JSONB,
    duration_ms INT,
    status TEXT CHECK (status IN ('success', 'failed', 'retry')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 인덱스
-- ============================================
CREATE INDEX idx_consultations_status ON consultations (status);
CREATE INDEX idx_consultations_classification ON consultations (classification);
CREATE INDEX idx_consultations_cta_level ON consultations (cta_level);
CREATE INDEX idx_consultations_created_at ON consultations (created_at DESC);

CREATE INDEX idx_reports_consultation_id ON reports (consultation_id);
CREATE INDEX idx_reports_status ON reports (status);
CREATE INDEX idx_reports_access_token ON reports (access_token);

CREATE INDEX idx_agent_logs_consultation_id ON agent_logs (consultation_id);

-- ============================================
-- 벡터 검색 함수 (Supabase RPC)
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
        1 - (fv.embedding <=> query_embedding) AS similarity
    FROM faq_vectors fv
    WHERE fv.category = target_category
        AND 1 - (fv.embedding <=> query_embedding) > match_threshold
    ORDER BY fv.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ============================================
-- updated_at 자동 갱신 트리거
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_consultations_updated_at
    BEFORE UPDATE ON consultations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trigger_youtube_sources_updated_at
    BEFORE UPDATE ON youtube_sources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
