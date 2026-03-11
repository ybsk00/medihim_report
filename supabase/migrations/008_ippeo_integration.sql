-- ============================================
-- 008: 이뽀 앱 연동을 위한 스키마 확장
-- ============================================

-- consultations 테이블 확장 (이뽀 연동 필드)
ALTER TABLE consultations ADD COLUMN IF NOT EXISTS hospital_name TEXT;
ALTER TABLE consultations ADD COLUMN IF NOT EXISTS doctor_name TEXT;
ALTER TABLE consultations ADD COLUMN IF NOT EXISTS concern_area TEXT;
ALTER TABLE consultations ADD COLUMN IF NOT EXISTS consultation_round INT DEFAULT 1;
