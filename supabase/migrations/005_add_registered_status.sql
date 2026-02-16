-- ============================================
-- 005: consultations 테이블에 'registered' 상태 추가
-- 등록과 리포트 생성을 분리하기 위한 마이그레이션
-- ============================================

-- 기존 CHECK 제약조건 삭제
ALTER TABLE consultations DROP CONSTRAINT IF EXISTS consultations_status_check;

-- 새 CHECK 제약조건 추가 ('registered' 포함)
ALTER TABLE consultations ADD CONSTRAINT consultations_status_check
    CHECK (status IN (
        'registered',
        'processing',
        'classification_pending',
        'report_generating',
        'report_ready',
        'report_approved',
        'report_sent',
        'report_failed'
    ));

-- 기본값 변경: 새 상담은 'registered' 상태로 시작
ALTER TABLE consultations ALTER COLUMN status SET DEFAULT 'registered';
