# 메디힘 이뻐 (MediHim Ippeo) — AI 상담 리포트 시스템

## 프로젝트 개요

일본 의료관광 플랫폼 「이뻐(IPPEO)」의 AI 상담 리포트 시스템.
일본인 소비자가 한국 피부과/성형외과에 대해 상담한 내용(일본어 또는 한국어 STT/다이얼로그)을 AI가 분석하여
구조화된 리포트를 자동 생성하고, 관리자 검토 후 이메일/URL로 소비자에게 발송한다.

> ⚠️ 한국어 명칭은 "이뻐"(O). "이뻐"는 오타. 영문 "IPPEO"는 그대로 유지.

### 리포트 생성 구조 (2026-04-08 확정)

**모든 회차(1차/2차/3차)에서 동일하게 R3 + R4 생성.** 회차별로 리포트 타입을 분기하지 않음.
- **R3 (병원용, 한국어)**: 6섹션. 콜백 키 `doctor_report`. `[활성 — 이뻐앱 연동]`
- **R4 (고객용, 일본어)**: 10섹션. 콜백 키 `patient_report`. `[활성 — 이뻐앱 연동]`

라운드 정보(consultation_round)는 리포트 **헤더/타이틀 표시에만** 사용:
- 1차 → "1차 상담리포트 / 상담실장" + "~상담실장 리포트"
- 2차 → "2차 상담리포트 / 의사" + "~의사 리포트"
- 3차 → "3차 상담리포트 / 상담실장" + "~상담실장 리포트"

> ⚠️ **절대 금지**: pipeline.py에서 consultation_round에 따라 R1/R2/R3/R4를 분기하는 코드 금지. 2026-04-08 긴급 장애로 확인됨.
> ⚠️ R1(r1_cs_writer.py), R2(r2_director_writer.py) 파일은 유지하되 파이프라인에서 호출하지 않음.
> ⚠️ HTML API 연동 방식 검토 중 (iframe 대신 인라인 CSS HTML을 API로 제공). 2026-04-08 이뻐 측 협의 예정.

---

## 기술 스택

### 프론트엔드
- **프레임워크**: Next.js 16+ (App Router)
- **스타일링**: Tailwind CSS v4
- **배포**: Firebase Hosting (https://ippeo-medhim.web.app)
- **용도**: 관리자페이지(한국어) + 소비자 리포트 웹페이지(일본어)

### 백엔드
- **프레임워크**: Python FastAPI (Python 3.13)
- **배포**: Google Cloud Run (asia-northeast3)
- **GitHub**: https://github.com/ybsk00/medihim_report (수동 배포: `cd backend && gcloud run deploy ippo-backend --source . --project=ipp0-medhim --region=asia-northeast3 --allow-unauthenticated`)
- **용도**: AI 에이전트 파이프라인, YouTube 자막 수집, 벡터DB 구축, 이메일 발송

### 데이터베이스
- **Supabase** (PostgreSQL + pgvector 확장)
- 일반 데이터 + 벡터 임베딩 모두 Supabase에서 관리

### AI/ML
- **LLM**: Google Gemini API (텍스트 생성 + 임베딩 모두 동일 API 키)
- **임베딩**: Gemini Embedding 768차원
- **벡터 검색**: Supabase pgvector

### 이메일
- **Gmail SMTP** (report.ippeo@gmail.com, App Password 인증)
- `smtplib.SMTP_SSL("smtp.gmail.com", 465)` + `asyncio.to_thread` 비동기 발송

---

## 환경변수 (.env)

```env
GEMINI_API_KEY=           # Gemini API (LLM + 임베딩 모두)
SUPABASE_URL=             # Supabase 프로젝트 URL
SUPABASE_SERVICE_KEY=     # Supabase 서비스 키 (서버 전용)
GMAIL_ADDRESS=            # Gmail 이메일 (report.ippeo@gmail.com)
GMAIL_APP_PASSWORD=       # Gmail 앱 비밀번호
FRONTEND_URL=             # 프론트엔드 URL (https://ippeo-medhim.web.app)
YOUTUBE_API_KEY=          # YouTube Data API v3
ADMIN_SECRET=             # 관리자 JWT 시크릿
NCBI_API_KEY=             # PubMed NCBI API 키
NCBI_EMAIL=               # NCBI API 이메일
NCBI_TOOL=                # NCBI API 도구명
```

> ⚠️ 모든 API 키는 서버단(.env)에서만 관리. 관리자페이지 UI에 절대 노출하지 않는다.

---

## 프로젝트 디렉토리 구조

```
ippeo/
├── frontend/                    # Next.js (Vercel 배포)
│   ├── app/
│   │   ├── admin/               # 관리자페이지 (한국어)
│   │   │   ├── page.tsx         # 대시보드
│   │   │   ├── consultations/   # 상담 관리
│   │   │   │   ├── page.tsx     # 상담 목록
│   │   │   │   ├── new/page.tsx # 새 상담 등록
│   │   │   │   └── [id]/page.tsx # 상담 상세
│   │   │   ├── unclassified/    # 미분류 처리
│   │   │   │   └── page.tsx
│   │   │   └── reports/         # 리포트 관리
│   │   │       ├── page.tsx     # 리포트 목록
│   │   │       └── [id]/page.tsx # 리포트 상세/검토
│   │   ├── report/              # 소비자 리포트 (일본어)
│   │   │   └── [token]/page.tsx # 토큰 기반 리포트 열람
│   │   ├── layout.tsx
│   │   └── page.tsx             # 루트 → /admin 리다이렉트
│   ├── components/
│   │   ├── admin/               # 관리자페이지 컴포넌트
│   │   │   ├── Sidebar.tsx
│   │   │   ├── DashboardCards.tsx
│   │   │   ├── ConsultationTable.tsx
│   │   │   ├── ConsultationForm.tsx
│   │   │   ├── UnclassifiedModal.tsx
│   │   │   ├── ReportPreview.tsx
│   │   │   ├── ReportReviewPanel.tsx
│   │   │   ├── ShareButton.tsx       # URL 공유 (링크 복사 + LINE)
│   │   │   └── CTABadge.tsx
│   │   ├── report-internal/     # 내부용 리포트 컴포넌트
│   │   │   ├── R1CSReport.tsx          # CS 사전상담 리포트 [비활성화]
│   │   │   ├── R2DirectorReport.tsx   # 의료진용 리포트 (인디고 테마) [비활성화]
│   │   │   └── R3DirectorReport.tsx   # 상담실장용 리포트 (보라색 테마) [활성]
│   │   └── report/              # 소비자 리포트 컴포넌트
│   │       ├── ReportHeader.tsx
│   │       ├── Section1Summary.tsx
│   │       ├── Section2Direction.tsx
│   │       ├── Section3Concerns.tsx
│   │       ├── Section4Medical.tsx
│   │       ├── Section5Proposal.tsx
│   │       ├── Section6Options.tsx
│   │       ├── Section7Recovery.tsx
│   │       └── ReportFooter.tsx
│   ├── lib/
│   │   ├── supabase.ts          # Supabase 클라이언트
│   │   └── api.ts               # Cloud Run API 호출 함수
│   ├── design-reference/        # Google Stitch HTML 레퍼런스
│   │   ├── report-template.html # 리포트 디자인 원본 (이 파일 참고해서 코딩)
│   │   └── admin-template.html  # 관리자페이지 디자인 원본 (이 파일 참고해서 코딩)
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── package.json
│
├── backend/                     # Python FastAPI (Cloud Run 배포)
│   ├── main.py                  # FastAPI 앱 엔트리
│   ├── api/
│   │   ├── consultation.py      # 상담 등록/조회 API
│   │   ├── report.py            # 리포트 승인/발송 API
│   │   ├── classify.py          # 수동 분류 API
│   │   └── youtube.py           # YouTube 자막 수집 API
│   ├── agents/
│   │   ├── pipeline.py          # 전체 파이프라인 오케스트레이터 (R1~R4 멀티타입)
│   │   ├── translator.py        # 번역 에이전트 (일→한)
│   │   ├── intent_extractor.py  # 의도 추출 에이전트
│   │   ├── classifier.py        # 분류 에이전트
│   │   ├── validator.py         # 검증 에이전트
│   │   ├── rag_agent.py         # RAG 에이전트 (과별 벡터DB 검색)
│   │   ├── report_writer.py     # R4 리포트 작성 에이전트 (고객용, 일본어 10섹션)
│   │   ├── r1_cs_writer.py      # R1 리포트 작성 에이전트 (CS 사전상담용, 한국어 3섹션) [비활성화]
│   │   ├── r2_director_writer.py # R2 리포트 작성 에이전트 (의료진용, 한국어 5섹션) [비활성화]
│   │   ├── r3_director_writer.py # R3 리포트 작성 에이전트 (상담실장용, 한국어 7섹션) [활성]
│   │   ├── report_reviewer.py   # 검토 에이전트 (R1~R4 타입별 검토 기준, max 3회)
│   │   ├── cta_analyzer.py      # CTA 분석 에이전트 (고객 발화 기반)
│   │   └── korean_translator.py # 리포트 한글 번역 에이전트
│   ├── services/
│   │   ├── supabase_client.py   # Supabase 연결
│   │   ├── gemini_client.py     # Gemini API (LLM + 임베딩)
│   │   ├── email_service.py     # Gmail SMTP 이메일 발송
│   │   └── youtube_service.py   # YouTube 자막 수집 + 정제 + FAQ 변환
│   ├── scripts/
│   │   ├── build_vector_db.py         # YouTube 벡터DB 빌드
│   │   ├── build_pubmed_vectors.py    # PubMed 벡터DB 빌드
│   │   ├── stt_pipeline.py            # STT 파이프라인
│   │   └── reclassify_youtube_faq.py  # YouTube FAQ 카테고리 재분류 스크립트
│   ├── models/
│   │   └── schemas.py           # Pydantic 데이터 모델
│   ├── config.py                # 환경변수 로드
│   ├── requirements.txt
│   └── Dockerfile               # Cloud Run 배포용
│
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql         # 전체 DB 스키마
│       ├── 002_classification_keywords.sql # 분류 키워드 사전 seed
│       ├── 003_customer_id_admin.sql      # customer_id + admin_users 추가
│       ├── 004_search_faq_columns.sql     # search_faq RPC에 출처 컬럼 추가
│       ├── 005_registered_status.sql      # consultations에 registered 상태 추가
│       ├── 006_input_language.sql         # consultations.input_language 추가 (ja/ko)
│       └── 007_multi_report_types.sql     # reports.report_type 추가 (r1~r4)
│
├── CLAUDE.md                    # 이 파일
└── .env                         # 환경변수 (gitignore)
```

---

## 데이터베이스 스키마 (Supabase PostgreSQL + pgvector)

### pgvector 확장 활성화

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 테이블

```sql
-- ============================================
-- 1. 상담 테이블
-- ============================================
CREATE TABLE consultations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_line_id TEXT,
    customer_id TEXT,                      -- 플랫폼 고객 ID
    input_language TEXT DEFAULT 'ja' CHECK (input_language IN ('ja', 'ko')), -- 입력 언어

    -- 원문 및 번역
    original_text TEXT NOT NULL,           -- 원문 (일본어 또는 한국어, input_language에 따라)
    translated_text TEXT,                  -- 한국어 번역본
    
    -- 화자 분리 데이터
    speaker_segments JSONB,               -- [{speaker: "counselor"|"customer", text: "..."}]
    customer_utterances TEXT,              -- 고객 발화만 추출한 텍스트
    
    -- AI 분류 결과
    classification TEXT CHECK (classification IN ('dermatology', 'plastic_surgery', 'unclassified')),
    classification_confidence FLOAT,
    classification_reason TEXT,            -- 분류 근거 설명
    is_manually_classified BOOLEAN DEFAULT FALSE,
    
    -- AI 의도 추출 결과
    intent_extraction JSONB,
    -- 구조:
    -- {
    --   "main_concerns": ["코끝 뾰족함", "이물감"],
    --   "desired_direction": "덜 뾰족하게, 자연스럽게",
    --   "unwanted": "과도한 높이 변화",
    --   "mentioned_procedures": ["코끝 재수술", "귀연골 활용"],
    --   "keywords": ["코끝", "재수술", "자연스러움"]
    -- }
    
    -- CTA 분석 (고객 발화 기반)
    cta_level TEXT CHECK (cta_level IN ('hot', 'warm', 'cool')),
    cta_signals JSONB,                    -- 판단 근거 고객 발화 목록
    -- 구조: ["7月に合わせられますか？", "費用はどのくらい？"]
    
    -- 상태
    status TEXT DEFAULT 'registered' CHECK (status IN (
        'registered',        -- 등록 완료 (파이프라인 미실행)
        'processing',        -- 파이프라인 처리 중
        'classification_pending',  -- 미분류 (수동 분류 대기)
        'report_generating', -- 리포트 생성 중
        'report_ready',      -- 리포트 생성 완료 (검토 대기)
        'report_approved',   -- 승인 완료
        'report_sent',       -- 발송 완료
        'report_failed'      -- 처리 실패
    )),
    error_message TEXT,                   -- 실패 시 에러 메시지
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 2. 리포트 테이블
-- ============================================
CREATE TABLE reports (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    consultation_id UUID REFERENCES consultations(id) ON DELETE CASCADE,
    report_type TEXT NOT NULL DEFAULT 'r4' CHECK (report_type IN ('r1', 'r2', 'r3', 'r4')),

    -- 리포트 내용 (R4: 10섹션, R1: 7섹션, R2: 5섹션, R3: 4섹션)
    report_data JSONB NOT NULL,
    -- R4 구조 (고객용, 일본어, 10섹션):
    -- {
    --   "title": "OO様 ご相談リポート",
    --   "section1_key_summary": { "summary_text": "...", "concern_list": [...] },
    --   "section2_cause_analysis": { "explanations": [...], "footnote": "..." },
    --   "section3_recommendation": { "steps": [...] },
    --   "section4_recovery": { "info": [...] },
    --   "section5_scar_info": { ... },
    --   "section6_precautions": { ... },
    --   "section7_risks": { ... },
    --   "section8_cost_estimate": { ... },
    --   "section9_visit_date": { ... },
    --   "section10_ippeo_message": { ... }
    -- }

    -- UNIQUE 제약: 상담 1건당 같은 타입 리포트 1개만
    -- UNIQUE (consultation_id, report_type)
    
    -- 한국어 번역본
    report_data_ko JSONB,                 -- 동일 구조의 한국어 버전
    
    -- RAG 컨텍스트 (어떤 벡터DB 데이터를 참조했는지)
    rag_context JSONB,
    -- 구조: [{"faq_id": "...", "question": "...", "answer": "...", "similarity": 0.89}]
    
    -- 검토 상태
    review_count INT DEFAULT 0,           -- 검토 에이전트 시도 횟수 (max 3)
    review_passed BOOLEAN DEFAULT FALSE,
    review_notes TEXT,
    
    -- 발송 정보
    access_token TEXT UNIQUE,             -- 리포트 열람 URL 토큰
    access_expires_at TIMESTAMPTZ,        -- 토큰 유효기간 (만료 체크 비활성화, 영구 열람 가능)
    
    -- 이메일 발송
    email_sent_at TIMESTAMPTZ,
    email_opened_at TIMESTAMPTZ,          -- 열람 추적
    
    -- 상태
    status TEXT DEFAULT 'draft' CHECK (status IN (
        'draft',          -- 생성 완료 (검토 전)
        'approved',       -- 관리자 승인
        'rejected',       -- 관리자 반려
        'sent'            -- 발송 완료
    )),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 3. 벡터DB - FAQ 테이블 (YouTube 기반)
-- ============================================
CREATE TABLE faq_vectors (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    
    -- 카테고리 (필터 검색용)
    category TEXT NOT NULL CHECK (category IN ('dermatology', 'plastic_surgery')),
    
    -- FAQ 내용
    question TEXT NOT NULL,               -- 환자 관점 질문
    answer TEXT NOT NULL,                 -- 의료진 설명 (근거 포함)
    procedure_name TEXT,                  -- 관련 시술명
    
    -- 벡터 임베딩
    embedding vector(768) NOT NULL,       -- Gemini Embedding 768차원
    
    -- 출처
    youtube_video_id TEXT,
    youtube_title TEXT,
    youtube_url TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 벡터 검색 인덱스
CREATE INDEX ON faq_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 카테고리 필터 인덱스
CREATE INDEX ON faq_vectors (category);

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
    
    -- 처리 상태
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending',         -- 대기
        'transcript_fetched', -- 자막 추출 완료
        'refined',         -- LLM 정제 완료
        'faq_generated',   -- FAQ 변환 완료
        'embedded',        -- 임베딩 완료
        'skipped',         -- 자동자막 없어서 스킵
        'failed'           -- 처리 실패
    )),
    
    raw_transcript TEXT,                  -- 원본 자막
    refined_transcript TEXT,              -- 정제된 자막
    faq_count INT DEFAULT 0,             -- 생성된 FAQ 수
    
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
    context_keywords JSONB,               -- 경계 시술의 경우 동반 키워드
    -- 구조: {"plastic_surgery": ["코 높이기", "윤곽"], "dermatology": ["레이저", "피부결"]}
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- 6. 에이전트 처리 로그 테이블
-- ============================================
CREATE TABLE agent_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    consultation_id UUID REFERENCES consultations(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL,             -- 'translator', 'classifier', 'rag', 'report_writer' 등
    input_data JSONB,
    output_data JSONB,
    duration_ms INT,
    status TEXT CHECK (status IN ('success', 'failed', 'retry')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 벡터 검색 함수 (Supabase RPC)

```sql
-- 피부과 또는 성형외과 카테고리 필터링 + 유사도 검색
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
```

---

## AI 에이전트 파이프라인 — 상세 설계

### 전체 흐름

```
[STT/다이얼로그 입력 (일본어)]
         │
    ┌────▼──────────┐
    │ 번역 Agent     │ → 일본어 → 한국어 번역 (원문 보존)
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ 화자 분리      │ → 상담사 발화 / 고객 발화 분리
    └────┬──────────┘
         │
         ├── 고객 발화 → CTA 분석 Agent → Hot/Warm/Cool + 근거 저장
         │
    ┌────▼──────────┐
    │ 의도 추출 Agent │ → 핵심 시술 목적, 희망 시술명, 부위, 키워드 추출
    └────┬──────────┘
         │
    ┌────▼──────────┐
    │ 분류 Agent     │ → 분류 가이드(룰셋) + 키워드 사전 참조
    │ + 경계시술 룰셋  │    피부과 / 성형외과 / 판단불가
    └────┬──────────┘
         │ (신뢰도 낮거나 경계 시술일 때)
    ┌────▼──────────┐
    │ 검증 Agent     │ → 분류 확정 or 관리자 검토 플래그(unclassified)
    └────┬──────────┘
         │
         │ (unclassified면 폴백 R1+R4 자동 생성 후 콜백 전송)
         │
         ├──────────────────┐
         │                  │
    ┌────▼─────┐      ┌────▼──────┐
    │피부과 RAG │      │성형외과 RAG │
    │Agent     │      │Agent      │
    │(category:│      │(category: │
    │dermatology)     │plastic_surgery)
    └────┬─────┘      └────┬──────┘
         │                  │
         └────────┬─────────┘
                  │
         ┌────────▼─────────┐
         │ _generate_all_reports()  │
         │                         │
         │ [R1] 사전상담 CS (한국어) │ → 3섹션 (비활성화)
         │ [R2] 의료진 (한국어)     │ → 5섹션 (비활성화)
         │ [R3] 상담실장 (한국어)   │ → 7섹션 (활성)
         │ [R4] 고객용 (일본어)     │ → 10섹션 (활성)
         └────────┬─────────┘
                  │ (각 타입별)
             ┌────▼──────┐
             │ 검토 Agent  │ → Pass/Fail (max 3회, 타입별 검토 기준)
             └────┬──────┘
                  │
            [DB 저장 (consultation_id + report_type으로 upsert)]
                  │
            [관리자 검토 대기]
```

### 상담 등록과 리포트 생성 분리

상담 등록과 AI 파이프라인 실행이 분리되어 있다:
1. **상담 등록** (`POST /api/consultations`) → `status: "registered"` (파이프라인 미실행)
2. **리포트 생성** (`POST /api/consultations/generate-reports`) → 관리자가 체크박스 선택 후 수동 트리거
   - status `registered` 또는 `report_failed` 상태만 허용
   - 최대 50건 동시 생성 (concurrency=5)

```python
# 등록만 (파이프라인 미실행)
@router.post("")
async def create_consultation(data):
    result = db.table("consultations").insert({..., "status": "registered"}).execute()
    return {"id": consultation["id"], "status": "registered"}

# 별도로 리포트 생성 트리거
@router.post("/generate-reports")
async def generate_reports(data):
    background_tasks.add_task(_run_pipelines_parallel, triggered_ids, 5)
```

### 리포트 재생성 (관리자 피드백 기반)

관리자가 생성된 리포트에 대해 한국어로 방향을 지시하면 RAG 재검색 + 리포트 재생성:
- `POST /api/reports/{id}/regenerate` → `{ direction: "..." }`
- 관리자 지시사항이 프롬프트에 최우선으로 반영됨
- 재생성 후 한국어 번역 캐시(`report_data_ko`) 자동 초기화

---

## 각 에이전트 상세 설계

### 1. 번역 에이전트 (translator.py)

```
입력: 일본어 STT/다이얼로그 원문
출력: 한국어 번역본
모델: Gemini
```

**프롬프트 핵심:**
- 의료 용어 정확히 번역 (시술명, 부위명)
- 뉘앙스 보존 (환자의 불안감, 요청 정도 등)
- 고유명사는 원문 병기

**중요: 일본어 원문은 반드시 DB에 보존한다.** 리포트 작성 에이전트가 최종 일본어 리포트 작성 시 참조해야 자연스러운 일본어 표현이 나온다.

### 2. 화자 분리 + CTA 분석 에이전트 (cta_analyzer.py)

```
입력: 일본어 원문 + 한국어 번역본
출력: 화자별 발화 세그먼트 + CTA 레벨 + 근거
```

**화자 분리:** LLM에게 대화 구조를 분석하게 하여 상담사/고객 발화를 분리한다.

**CTA 판단 기준 (고객 발화만 분석):**

| 레벨 | 신호 | 예시 발화 |
|------|------|-----------|
| Hot | 구체적 일정/비용 질문 | "7月に可能ですか？", "費用はいくら？", "回復期間は？" |
| Warm | 관심 있지만 비교/고민 | "他の病院では〜", "もう少し調べたい", "家族と相談します" |
| Cool | 정보 탐색 | "ちょっと気になって", "まだ具体的には", "いつか機会があれば" |

**출력 저장:**
- `consultations.cta_level`: "hot" / "warm" / "cool"
- `consultations.cta_signals`: 근거 발화 JSON 배열 (일본어)
- `consultations.speaker_segments`: 전체 화자 분리 데이터
- `consultations.customer_utterances`: 고객 발화 텍스트만 추출

### 3. 의도 추출 에이전트 (intent_extractor.py)

```
입력: 한국어 번역본
출력: 구조화된 의도 데이터
```

**추출 항목:**
```json
{
    "main_concerns": ["코끝 뾰족함", "이물감", "부자연스러움"],
    "desired_direction": "덜 뾰족하게, 덜 티나게, 자연스럽게",
    "unwanted": "과도한 높이 변화, 너무 큰 변화",
    "mentioned_procedures": ["코끝 재수술", "귀연골 활용"],
    "body_parts": ["코끝", "코등"],
    "keywords": ["코끝", "재수술", "자연스러움", "귀연골"]
}
```

### 4. 분류 에이전트 (classifier.py)

```
입력: 한국어 번역본 + 의도 추출 결과 + 키워드 사전 (DB에서 조회)
출력: 피부과 / 성형외과 / 미분류
```

**단일 분류 원칙**: 피부과 OR 성형외과. 혼합 분류 불가.
**분류 기준**: 핵심 의도(주소)가 기준.

**분류 로직:**

#### 명확 분류 키워드 (DB: classification_keywords 테이블에서 조회)

**성형외과 (plastic_surgery):**
쌍꺼풀, 코 성형, 코끝, 코등, 지방흡입, 안면윤곽, 양악, 이마 리프팅, 눈 재수술, 가슴 수술, 턱 수술, V라인, 리프팅 실

**피부과 (dermatology):**
여드름, 기미, 색소, 모공, 탈모 치료, 레이저, 하이푸, 울쎄라, 피부결, 주름 개선, 탄력, 리쥬란, 스킨 부스터

#### 경계 시술 (보톡스, 필러) 처리 규칙

1. **동반 키워드 기반 분류:**
   - 성형 맥락 단어 동반 → 성형외과
     - "코 높이기, 턱 끝, 윤곽, 이마 볼륨, 리프팅 실"과 함께 언급
   - 피부 관리 맥락 단어 동반 → 피부과
     - "레이저, 하이푸, 울쎄라, 피부결, 주름 개선, 탄력, 리쥬란"과 함께 언급

2. **맥락 단서 없으면** → `unclassified` (폴백 리포트 자동 생성)

#### 복합 니즈 예시
- "여드름 흉터 심해서 코 높이고 싶어요" → 성형외과 (코 성형이 주 목적)
- "피부 관리 받으면서 보톡스도 맞고 싶어요" → 피부과 (피부 관리가 주 목적)

### 5. 검증 에이전트 (validator.py)

```
입력: 분류 Agent의 분류 결과 + 신뢰도
출력: 분류 확정 or 관리자 검토 플래그
```

- 분류 신뢰도가 높고 명확 키워드 매칭이면 → 바로 확정
- 경계 시술이거나 신뢰도 낮으면 → `unclassified`로 플래그, 폴백 리포트 자동 생성
- `unclassified`인 상담은 관리자가 수동 분류 후 파이프라인 재개

### 6. RAG 에이전트 (rag_agent.py)

```
입력: 한국어 키워드 + 분류 결과 (피부과 or 성형외과)
출력: 관련 FAQ 데이터 (상위 5개)
```

**검색 흐름:**
1. 의도 추출에서 나온 키워드를 Gemini Embedding으로 768차원 벡터 생성
2. Supabase pgvector에서 해당 카테고리(dermatology / plastic_surgery)만 필터링하여 유사도 검색
3. 유사도 0.7 이상, 상위 5개 반환

**안전 폴백:** 벡터DB에서 유사도 0.7 이상 결과가 없는 시술은 리포트에 "내원 상담 시 상세 안내드리겠습니다"로 처리.

### 7. R4 리포트 작성 에이전트 (report_writer.py) — 고객용, 일본어

```
입력:
  - 한국어 RAG 데이터 (의료 지식)
  - 일본어 원문 (고객 뉘앙스)
  - 의도 추출 결과
  - 분류 결과
출력: 10섹션 일본어 리포트 JSON
```

**중요: 이 에이전트에는 한국어 RAG 데이터 + 일본어 원문을 동시에 제공한다.**
- 의료 정보의 정확성 → 한국어 RAG 데이터에서
- 일본어 표현의 자연스러움 → 일본어 원문에서

#### R4 리포트 10섹션 구조 (현행)

**섹션1 — ご相談の要点 (핵심 요약)**
- summary_text: 상담 핵심 요약 2~3줄
- concern_list: 핵심 고민 리스트

**섹션2 — 原因・背景の分析 (원인 분석)**
- explanations: 의료적 근거 설명 카드 (3~4개) ← RAG 의존도 높음
- footnote: 안심 문구

**섹션3 — おすすめの方向性 (추천 방향)**
- steps: STEP 형태로 접근 방법 제시 ← RAG 의존도 높음

**섹션4 — 回復について (회복 정보)**
- info: 회복 기간, 주의사항 등 정보 테이블

**섹션5 — 傷跡について (흉터 정보)**
- 시술 후 흉터 관련 안내

**섹션6 — 施術前後の注意点 (시술 전후 주의사항)**
- 시술 전/후 주의점 리스트

**섹션7 — リスクについて (리스크 안내)**
- 시술 관련 리스크 설명

**섹션8 — 費用の目安 (비용 목안)**
- 참고용 비용 안내 (AI 창작 금지, RAG 근거만 허용)

**섹션9 — ご来院の目安 (내원 일정)**
- 추천 내원 시기, 상담 예약 안내

**섹션10 — イッポからのメッセージ (이뻐 메시지)**
- 개인화된 격려/안내 메시지 (상담 고유 내용 반영, 템플릿 복사 금지)

> 리포트 버전 이력: V2(7섹션) → V3(9섹션) → V4(10섹션, 현행). 프론트엔드에서 `isV3Report()` 함수로 V3+ 판별 (`section1_key_summary` 키 존재 여부).

### 7-1. R1 사전상담 리포트 (r1_doctor_writer.py) `[활성 — 이뻐앱 연동]`

```
입력: 원문 + 번역 + 의도추출 + 분류 + RAG + CTA + 화자분리
출력: 7섹션 한국어 리포트 JSON
```

7섹션: 환자 개요, 핵심 호소, 언급 시술, 의학적 맥락, 환자 우려사항(우선순위 포함), 내원 의지(CTA+근거), 사전 참고사항.

### 7-2. R2 상담실장용 리포트 (r2_director_writer.py) `[비활성화]`

```
입력: R1 리포트 데이터 + 상담 원본 데이터
출력: 5섹션 한국어 리포트 JSON
```

5섹션: 시술 요약(R1 기반), 필요 리소스, 비용 계획(`is_estimate: true` 필수), 일정 계획, 환자 준비도.

### 7-3. R3 경영진용 리포트 (r3_executive_writer.py) `[비활성화]`

```
입력: R1 + R2 리포트 데이터
출력: 4섹션 한국어 리포트 JSON
```

4섹션 (3기둥 + 요약): 마케팅 분석, 의료 분석, 환자 관리 전략, 경영진 요약(액션 아이템 3개).

#### 톤앤매너
- 부드러운 제안형 어투: "〜と理解されました", "〜と見受けられました", "〜をお勧めいたします"
- 절대 단정형 사용 금지: "〜です", "〜しなければなりません" ✘
- 일본 소비자가 안심할 수 있는 톤

#### 과별 서브 템플릿 차이
- **성형외과**: 구조적 접근법 중심. "骨格ラインの整理", "軟骨の再配置" 등
- **피부과**: 치료 프로토콜 중심. "レーザー治療O回コース", "O週間間隔で施術" 등

### 8. 검토 에이전트 (report_reviewer.py)

```
입력: 생성된 리포트 JSON + report_type (r1/r2/r3/r4)
출력: Pass / Fail + 피드백
최대 재시도: 3회
```

타입별 검토 기준이 분리되어 있다 (`_get_review_config(report_type)`):

**R4 검토 기준 (일본어 프롬프트):**
- 10섹션 모두 존재하는가?
- 일본어 문법/표현이 자연스러운가?
- 비용 정보가 AI 창작이 아닌가? (RAG 근거만 허용)
- 톤앤매너가 중립 간결체인가?
- 개인화 메시지가 상담 고유 내용을 반영하는가?

**R1 검토 기준 (한국어):** 7섹션 존재, 의료 전문 용어 사용, CTA 정보 포함 여부
**R2 검토 기준 (한국어):** 5섹션 존재, 리소스 현실성, 비용 추정치 라벨 여부
**R3 검토 기준 (한국어):** 4섹션 존재, 액션 아이템 구체성, 경영 인사이트 포함

Fail 시 피드백과 함께 리포트 작성 에이전트에 재전달. 3회 실패 시 현재 상태로 저장하고 관리자에게 수동 검토 요청.

### 9. 한국어 번역 에이전트 (korean_translator.py)

```
입력: 일본어 리포트 JSON
출력: 한국어 리포트 JSON (동일 구조)
```

관리자가 "한글 보기" 토글 시 호출. 번역 결과는 `reports.report_data_ko`에 캐싱하여 재호출 방지.

---

## YouTube 자막 → 벡터DB 파이프라인

### 처리 흐름

```
[YouTube 영상 URL/ID 등록]
       │
  ┌────▼──────────┐
  │ YouTube API    │ → 영상 메타데이터 확인 + 자동 생성 자막 확인
  └────┬──────────┘
       │
       ├── 자동 자막 없음 → status: 'skipped' (스킵)
       │
  ┌────▼──────────┐
  │ 자막 추출      │ → 자동 생성 자막(transcript) 텍스트 추출
  └────┬──────────┘
       │
  ┌────▼──────────┐
  │ 자막 정제 (LLM) │ → 오탈자 수정, 의료 용어 교정, 문장 단위 정리
  └────┬──────────┘   → "울세라" → "울쎄라", "하이후" → "하이푸" 등
       │
  ┌────▼──────────┐
  │ FAQ 변환 (LLM)  │ → 정제된 텍스트에서 Q&A 쌍 추출
  └────┬──────────┘
       │
  ┌────▼──────────┐
  │ 임베딩 + 저장   │ → Gemini Embedding 768 → Supabase pgvector
  └───────────────┘
```

### FAQ 변환 프롬프트 핵심

```
이 의료 영상 자막에서 FAQ를 추출해주세요.
각 FAQ는 다음 형식으로 작성:
- question: 환자 관점의 질문 (예: "코끝이 뾰족해 보이는 이유는?")
- answer: 의료진 설명 (근거 포함, 2~3문장)
- procedure_name: 관련 시술명
- category: "dermatology" 또는 "plastic_surgery"

JSON 배열로 반환.
```

### 자막 없는 영상 처리

자동 생성 자막이 없는 영상은 **스킵한다.** YouTube에 피부과/성형외과 영상이 수천 개 있으므로 자막 없는 것은 무시해도 충분한 데이터를 확보할 수 있다.

---

## 관리자페이지 상세 설계 (한국어)

> ⚠️ /design-reference/admin-template.html 파일이 디자인 원본이다.
> 이 HTML의 레이아웃, 색상, 폰트, 간격을 그대로 유지할 것.
> React/Next.js 컴포넌트로 변환하되 디자인 톤을 절대 변경하지 말 것.

### 공통 레이아웃

- 좌측 사이드바 (240px) + 우측 메인 콘텐츠
- 사이드바 배경: #1E293B, 텍스트: #CBD5E1, 활성 메뉴: #3B82F6
- 메인 배경: #F8FAFC
- 폰트: Pretendard 또는 Noto Sans KR

**사이드바 메뉴:**
```
📊 대시보드
📋 상담 관리
⚠️ 미분류 처리  [배지: N건]
📄 리포트 관리
```

### 1. 대시보드 (/admin)

**상단 요약 카드 4개 (가로 배열):**
- 총 상담 건수
- 미분류 대기 건수 (⚠️)
- 리포트 대기 건수
- 발송 완료 건수 + 열람률

**CTA 현황 카드:**
- 🔴 Hot: N건 (N%)
- 🟡 Warm: N건 (N%)
- 🔵 Cool: N건 (N%)
- 가로 바 차트로 시각화

**최근 상담 목록 테이블 (최근 10건):**
- 컬럼: 고객명, 분류, CTA, 리포트 상태, 등록일
- CTA 배지: Hot=레드, Warm=옐로, Cool=블루
- 분류 배지: 성형외과=🏥, 피부과=💊, 미분류=⚠️

### 2. 상담 관리 (/admin/consultations)

**상단:** [+ 새 상담 등록] 버튼 + 검색 + 필터(분류, 상태)

**상담 목록 테이블:**
- 컬럼: 체크박스, 고객명, 이메일, 분류, CTA, 상태, 등록일
- 행 클릭 → 상세 화면 이동
- 페이지네이션

**새 상담 등록 모달 (/admin/consultations/new):**
- 고객명 (필수)
- 이메일 (필수)
- LINE ID (선택)
- 입력 방식 선택: STT 파일 업로드 / 다이얼로그 직접 입력
- STT: 드래그앤드롭 파일 업로드 영역
- 다이얼로그: 텍스트 에어리어
- [취소] [등록하기] 버튼

**상담 상세 화면 (/admin/consultations/[id]):**

상단:
- ← 목록으로 돌아가기 + "田中様 상담 상세" 타이틀

좌측 카드 - 고객 정보:
- 이름, 이메일, LINE ID, 등록일

우측 카드 - AI 분석 결과:
- 분류: 🏥 성형외과 (또는 💊 피부과)
- CTA: 🔴 Hot (또는 🟡 Warm, 🔵 Cool)
- CTA 판단 근거 (고객 발화 목록, 일본어)
- CTA 수동 변경 드롭다운

하단 카드 - 상담 원문:
- [일본어 원문] / [한국어 번역] 탭 전환
- 화자 구분 표시: 상담사=그레이 배경, 고객=흰 배경
- 하단: [리포트 보기 →] 링크

### 3. 미분류 처리 (/admin/unclassified)

**미분류 건 목록 테이블:**
- 컬럼: 고객명, 등록일, 주요 키워드(AI 추출), [분류하기] 버튼

**분류 모달:**
- AI 추출 키워드 표시
- 상담 원문 미리보기 (3~4줄 + [전체 보기])
- 분류 선택: [💊 피부과] [🏥 성형외과] 큰 버튼 2개
- [확인] 버튼 → 분류 후 파이프라인 자동 재개

### 4. 리포트 관리 (/admin/reports)

**리포트 목록 테이블:**
- 컬럼: 고객명, 분류, 상태, 발송일, 열람 여부, [보기/검토] 버튼
- 상태 배지: 발송완료=그린, 승인대기=옐로, 생성완료=블루, 분류대기=그레이

**리포트 상세/검토 화면 (/admin/reports/[id]):**

상단: ← 목록으로 + "田中様 리포트 검토" 타이틀

메인 영역:
- [일본어 원문] / [한글 번역] 토글 탭
  - 한글 번역 클릭 시: 캐시 있으면 즉시 표시, 없으면 LLM 번역 에이전트 호출 후 캐시 저장
- 리포트 미리보기: 모바일 프레임(480px) 안에 실제 소비자 뷰와 동일하게 렌더링
  - 7섹션 전체 스크롤 표시

하단 버튼:
- [❌ 반려] [✏️ 수정] [✅ 승인] 3개 버튼
- 수정: 텍스트 에디터 모드로 전환, 섹션별 내용 수정 가능

승인 시:
- 확인 다이얼로그: "이메일이 자동 발송됩니다. 승인하시겠습니까?"
- 승인 후 표시:
  - ✅ 이메일 자동 발송 완료 (tanaka@email.jp)
  - 📎 [URL 공유] 버튼 → 드롭다운: "링크 복사" / "LINE으로 공유"
- 발송 이력: 발송 시간, 열람 여부

---

## 소비자 리포트 웹페이지 상세 설계 (일본어)

> ⚠️ /design-reference/report-template.html 파일이 디자인 원본이다.
> 이 HTML의 레이아웃, 색상, 폰트, 간격을 그대로 유지할 것.
> React/Next.js 컴포넌트로 변환하되 디자인 톤을 절대 변경하지 말 것.

### 접근 방식
- URL: `/report/{access_token}`
- 본인 확인: 생년월일 입력 (토큰 + 생년월일 일치 시 열람 가능)
- 유효기간: 없음 (영구 열람 가능, 만료 체크 비활성화)

### 디자인 사양
- **모바일 최적화 필수** (일본 소비자 대부분 스마트폰 열람)
- 최대 폭: 480px
- 원페이지 스크롤 (7섹션 세로 스크롤)
- 폰트: Noto Sans JP
- 메인: #FAFAFA, 텍스트: #2C3E50, 포인트: #E8927C (코랄 핑크)
- 카드: 흰색, 라운드 12px, 부드러운 그림자
- 세션 간 40px 여백
- 스크롤 시 섹션 페이드인 애니메이션 (경량)

### 10섹션 컴포넌트 (R4, 현행)

관리자 리포트 상세 화면(`/admin/reports/[id]`)에서 `R4Sections` 컴포넌트로 인라인 렌더링:
1. **핵심 요약** (section1_key_summary) — 상담 요점 + 고민 리스트
2. **원인 분석** (section2_cause_analysis) — 의료적 근거 설명 카드
3. **추천 방향** (section3_recommendation) — STEP 형태 제안
4. **회복 정보** (section4_recovery) — 회복 기간/주의사항
5. **흉터 정보** (section5_scar_info) — 시술 후 흉터 안내
6. **주의사항** (section6_precautions) — 시술 전후 주의점
7. **리스크** (section7_risks) — 시술 리스크 설명
8. **비용 목안** (section8_cost_estimate) — 참고 비용
9. **내원 일정** (section9_visit_date) — 추천 내원 시기
10. **이뻐 메시지** (section10_ippeo_message) — 개인화 격려 메시지

> 소비자 리포트 페이지(`/report/[token]`)의 컴포넌트 (기존 V2 7섹션):
> Section1Summary ~ Section7Recovery — 레거시 하위호환용으로 유지

### 헤더/푸터
- 헤더: "IPPEO | オンライン相談リポート" 로고 + 고객명 + 상담 제목 + 날짜
- 푸터: "이뻐(이뻐) | 韓国美容医療コンサルティング" + 면책 문구 + 문의 링크

---

## 이메일 발송 시스템

### 발송 흐름 (승인과 발송 분리)

```
[관리자 리포트 승인] → status: approved (이메일 발송 없음)
       │
       ├──→ [이메일 발송 버튼] → Gmail SMTP 발송
       │    From: IPPEO <report.ippeo@gmail.com>
       │    To: 고객 이메일
       │    내용: 리포트 URL 포함
       │
       └──→ [URL 공유 버튼] 관리자페이지에서
            ├── 링크 복사 (클립보드)
            └── LINE 공유 (Web Share API → LINE 앱 오픈)
```

### 이메일 내용
- 제목: "【イッポ】OO様 ご相談リポートが届きました"
- 본문: 간단한 인사 + 리포트 URL 링크 + 유효기간 안내
- 디자인: 심플하고 깔끔한 HTML 이메일
- 발송: Gmail SMTP (smtplib.SMTP_SSL + asyncio.to_thread)

### URL 공유 버튼 (ShareButton.tsx)
- 버튼 클릭 → 드롭다운 메뉴
- "링크 복사": `navigator.clipboard.writeText(url)`
- "LINE으로 공유": 모바일에서 Web Share API 사용 시 LINE 앱 바로 열림
  - 데스크톱: `https://social-plugins.line.me/lineit/share?url={encoded_url}`

---

## API 엔드포인트 설계 (FastAPI)

### 상담 관련

```
POST   /api/consultations                # 새 상담 등록 (status: registered, 파이프라인 미실행)
POST   /api/consultations/bulk           # 일괄 등록 (최대 100건)
POST   /api/consultations/generate-reports  # 선택한 상담에 리포트 생성 트리거 (최대 50건)
GET    /api/consultations                # 상담 목록 (필터: classification, status, page)
GET    /api/consultations/{id}           # 상담 상세
PUT    /api/consultations/{id}           # 고객 정보 수정 (이름, 이메일, LINE ID, 플랫폼 ID)
PUT    /api/consultations/{id}/classify  # 수동 분류 (미분류 → 피부과/성형외과, 파이프라인 재개)
PUT    /api/consultations/{id}/cta       # CTA 레벨 수동 변경
POST   /api/consultations/delete         # 선택한 상담 삭제
```

### 리포트 관련

```
GET    /api/reports                      # 리포트 목록
GET    /api/reports/{id}                 # 리포트 상세
PUT    /api/reports/{id}/approve         # 리포트 승인 (이메일 발송 없이 승인만)
POST   /api/reports/{id}/send-email      # 승인된 리포트 이메일 발송
PUT    /api/reports/{id}/reject          # 리포트 반려
PUT    /api/reports/{id}/edit            # 리포트 내용 수정
GET    /api/reports/{id}/translate       # 한국어 번역 요청 (캐싱)
POST   /api/reports/{id}/regenerate      # 관리자 피드백 기반 재생성
POST   /api/reports/bulk-approve         # 일괄 승인
POST   /api/reports/delete               # 선택한 리포트 삭제
```

### 소비자 리포트

```
GET    /api/public/report/{token}           # 리포트 열람 (토큰 검증, 만료 없음)
POST   /api/public/report/{token}/verify    # 본인 확인 (생년월일)
POST   /api/public/report/{token}/opened    # 열람 추적 (이메일 열람 기록)
```

### YouTube/벡터DB

```
POST   /api/youtube/add            # YouTube 영상 URL 등록
POST   /api/youtube/process        # 등록된 영상 일괄 처리 (자막→정제→FAQ→임베딩)
GET    /api/youtube/sources        # 등록된 영상 목록 + 처리 상태
```

### 대시보드

```
GET    /api/dashboard/stats        # 대시보드 통계 (총 상담, 미분류, 대기, 발송, CTA 현황)
```

---

## 배포 설정

### Firebase Hosting (프론트엔드)

- **URL**: https://ippeo-medhim.web.app
- Next.js SSR은 Cloud Functions로 자동 배포됨
- API 프록시: `firebase.json`의 rewrites 설정으로 `/api/*` → Cloud Run

```bash
cd frontend && npx firebase deploy --only hosting
```

### Google Cloud Run (백엔드)

- **리전**: asia-northeast3
- GitHub push 시 자동 빌드/배포

```dockerfile
# backend/Dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

```
# backend/requirements.txt (주요)
fastapi
uvicorn[standard]
google-generativeai
supabase
youtube-transcript-api
pydantic
python-dotenv
httpx
PyJWT
```

---

## 분류 키워드 사전 초기 데이터

```sql
-- 성형외과 명확 키워드
INSERT INTO classification_keywords (category, keyword) VALUES
('plastic_surgery', '쌍꺼풀'),
('plastic_surgery', '코 성형'),
('plastic_surgery', '코끝'),
('plastic_surgery', '코등'),
('plastic_surgery', '지방흡입'),
('plastic_surgery', '안면윤곽'),
('plastic_surgery', '양악'),
('plastic_surgery', '이마 리프팅'),
('plastic_surgery', '눈 재수술'),
('plastic_surgery', '가슴 수술'),
('plastic_surgery', '턱 수술'),
('plastic_surgery', 'V라인'),
('plastic_surgery', '리프팅 실'),
('plastic_surgery', '코 재수술');

-- 피부과 명확 키워드
INSERT INTO classification_keywords (category, keyword) VALUES
('dermatology', '여드름'),
('dermatology', '기미'),
('dermatology', '색소'),
('dermatology', '모공'),
('dermatology', '탈모'),
('dermatology', '레이저'),
('dermatology', '하이푸'),
('dermatology', '울쎄라'),
('dermatology', '피부결'),
('dermatology', '주름 개선'),
('dermatology', '탄력'),
('dermatology', '리쥬란'),
('dermatology', '스킨 부스터');

-- 경계 시술 + 동반 키워드
INSERT INTO classification_keywords (category, keyword, context_keywords) VALUES
('boundary', '보톡스', '{"plastic_surgery": ["코 높이기", "턱 끝", "윤곽", "이마 볼륨", "리프팅 실"], "dermatology": ["레이저", "하이푸", "울쎄라", "피부결", "주름 개선", "탄력", "리쥬란"]}'),
('boundary', '필러', '{"plastic_surgery": ["코 높이기", "턱 끝", "윤곽", "이마 볼륨", "리프팅 실"], "dermatology": ["레이저", "하이푸", "울쎄라", "피부결", "주름 개선", "탄력", "리쥬란"]}');
```

---

## 현재 완료 상태

- Phase 1 (인프라): 완료
- Phase 2 (백엔드): 완료 — 12개 에이전트 (R1~R4 writer 4개 + 공통 8개) + 파이프라인 + API + Gmail 이메일
- Phase 3 (프론트엔드): 완료 — 관리자페이지 + 소비자 리포트 + 내부 리포트 컴포넌트(R1~R3)
- Phase 4 (배포): 완료 — Cloud Run (백엔드) + Firebase (프론트엔드)
- 벡터DB 파이프라인: 완료 — YouTube 2,448 + PubMed 2,336 = 4,784 벡터
- 회차별 리포트 분기(v4.0): round=1→R1(사전상담,4섹션) round=2→R2(의사용,5섹션) round≥3→R3(상담실장,6섹션)+R4(고객용,10섹션) — 모두 활성화
- DB 마이그레이션: 001~009 완료 (009: report_type r1→r3 재구조화)
- 추가 기능: 고객 정보 인라인 편집, 일괄 승인, 리포트 재생성, 한국어 입력 지원, FAQ 재분류 스크립트
- 이뻐 앱 연동: Webhook 수신 + iframe embed + 콜백 전송 구현 완료
- 폴백 로직: 미분류/에러 시 폴백 R3+R4(한국어 포함) 자동 생성 + 이뻐 콜백 전송
- 주간 헬스체크: Cloud Scheduler 매주 금요일 18:10 KST → `POST /api/health/weekly-report` → 이메일 자동 발송

---

## 벡터DB 현황 (완료)

| 소스 | 벡터 수 | 비고 |
|------|---------|------|
| YouTube FAQ | 2,448 | 1,104개 영상 임베딩 완료 |
| PubMed FAQ | 2,336 | 853편 논문, 34개 카테고리 |
| **합계** | **4,784** | 피부과 2,282 + 성형외과 2,502 |

- 임베딩 모델: `models/gemini-embedding-001` (output_dimensionality=768)
- PubMed 데이터: `youtube_video_id`=PMID, `youtube_url`=PubMed URL로 저장 (URL 패턴으로 구분)

---

## 핵심 주의사항

1. **API 키는 절대 프론트엔드에 노출하지 않는다.** 모든 키는 .env에서 서버단으로만.
2. **일본어 원문은 반드시 보존한다.** 번역 후에도 원문 DB에 남겨야 한다.
3. **분류는 단일 분류 원칙.** 피부과 OR 성형외과, 혼합 불가.
4. **미분류는 폴백 리포트 자동 생성.** 분류 불가 시 폴백 R3+R4(한국어 포함)를 생성하고 이뻐 콜백 전송. 파이프라인 중단 없음.
5. **R4 리포트의 비용 정보는 AI 창작 금지.** RAG에 근거가 있을 때만 목안으로 표시.
6. **CTA는 R4 고객 리포트에 넣지 않는다.** R1(사전상담용)에만 포함. 관리자페이지에서도 활용.
7. **벡터DB 검색 시 카테고리 필터 필수.** 피부과 상담에 성형외과 데이터가 나오면 안 된다.
8. **YouTube 자동 자막 없는 영상은 스킵.** 처리하려고 시간 쓰지 말 것.
9. **리포트 톤: 부드러운 제안형.** 단정형/명령형 절대 사용 금지.
10. **모바일 최적화 필수.** 리포트 페이지는 480px 기준으로 디자인.
11. **Gemini API JSON 응답 방어.** `json.loads()` 후 `isinstance(data, list)` 체크 필수 (가끔 `[{...}]` 반환).
12. **Supabase select() 페이지네이션.** 기본 1000행 제한. `.range(offset, offset+999)` 루프 필요.
13. **이메일 발송 실패가 승인을 블로킹하면 안 됨.** 승인과 이메일 발송은 별도 동작.
14. **R1~R2 비활성화 주석 규칙.** R1(CS사전상담), R2(의료진) 관련 코드 블록은 비활성화 주석 상태 유지. 활성화 시 주석만 해제.
15. **리포트 저장은 upsert.** `consultation_id + report_type`으로 기존 리포트가 있으면 update, 없으면 insert.
16. **R4 리포트 톤: 중립형 간결체.** 과도한 감정 표현이나 단정형 금지. (최근 커밋에서 따뜻한 상세 문체 → 중립 간결체로 복원)
17. **리포트 토큰 만료 없음.** access_expires_at 컬럼은 존재하나 만료 체크 비활성화. 영구 열람 가능.
18. **폴백 리포트는 R3+R4 쌍으로 생성.** `_build_fallback_r3()` + `_build_fallback_r4()` + `_build_fallback_r4_ko()` 세트.
19. **Cloud Run 배포는 수동.** `gcloud run deploy` 명령으로 직접 배포. 자동 배포 트리거 설정 중 (GitHub OAuth 완료, 트리거 생성 대기).
20. **회차별 리포트 타입 분기 절대 금지.** pipeline.py에서 consultation_round에 따라 R1/R2를 생성하면 이뻐 앱 연동 깨짐. 모든 회차에서 R3+R4만 생성. (2026-04-08 긴급 장애로 확인)
21. **R3DirectorReport 배열 방어 필수.** Gemini가 배열 대신 문자열 반환 시 .map() 크래시. 모든 .map()에 Array.isArray 체크 필수.
