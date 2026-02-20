-- ============================================
-- 006: input_language 컬럼 추가
-- 상담 다이얼로그 입력 언어 ('ja' 또는 'ko')
-- ============================================

ALTER TABLE consultations ADD COLUMN IF NOT EXISTS input_language TEXT DEFAULT 'ja';

-- 기존 데이터는 모두 일본어로 간주
UPDATE consultations SET input_language = 'ja' WHERE input_language IS NULL;
