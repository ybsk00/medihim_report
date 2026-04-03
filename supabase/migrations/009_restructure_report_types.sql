-- 009: 리포트 타입 재구조화
-- R1(의사 사전상담) → R3(상담실장)으로 변경
-- R3(경영진) 데이터 삭제 (비활성 상태였으므로 데이터 없을 것)
--
-- 새 체계:
--   R1: 1차 상담리포트 - 사전상담 (CS용, 비활성화)
--   R2: 2차 상담리포트 - 의료진 (비활성화)
--   R3: 3차 상담리포트 - 상담실장 (활성화)
--   R4: 고객용 리포트 (일본어, 활성화)

-- 1. 기존 R3(경영진) 데이터 삭제 (UNIQUE 제약 충돌 방지)
DELETE FROM reports WHERE report_type = 'r3';

-- 2. 기존 R1 → R3로 변경
UPDATE reports SET report_type = 'r3' WHERE report_type = 'r1';

-- 3. 기존 리포트 title 텍스트 업데이트 ("사전상담 브리핑" → "3차 상담리포트")
UPDATE reports
SET report_data = jsonb_set(
    report_data,
    '{title}',
    to_jsonb(replace(report_data->>'title', '사전상담 브리핑', '3차 상담리포트'))
)
WHERE report_type = 'r3'
  AND report_data->>'title' LIKE '%사전상담 브리핑%';
