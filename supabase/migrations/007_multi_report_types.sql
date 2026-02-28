-- ============================================
-- 007: Multi Report Types (R1~R4)
-- ============================================
-- R1: 의사용, R2: 상담실장용, R3: 경영진용, R4: 고객용

-- reports 테이블에 report_type 컬럼 추가
ALTER TABLE reports ADD COLUMN report_type TEXT DEFAULT 'r4'
  CHECK (report_type IN ('r1', 'r2', 'r3', 'r4'));

-- 기존 리포트 모두 r4로 설정
UPDATE reports SET report_type = 'r4' WHERE report_type IS NULL;

-- NOT NULL 제약 추가
ALTER TABLE reports ALTER COLUMN report_type SET NOT NULL;

-- 상담당 리포트 타입 중복 방지
ALTER TABLE reports ADD CONSTRAINT uq_consultation_report_type
  UNIQUE (consultation_id, report_type);

-- 효율적 조회를 위한 인덱스
CREATE INDEX idx_reports_consultation_type
  ON reports (consultation_id, report_type);
