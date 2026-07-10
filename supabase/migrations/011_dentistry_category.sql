-- ============================================
-- 011: 치과(dentistry) 카테고리 확장
-- ============================================
-- 5개 CHECK 제약에 'dentistry' 추가 (가산적, 기존 값 무영향)
-- + 치과 명확 키워드 + 경계 미백 규칙 seed
-- search_faq RPC는 category 파라미터 방식이라 변경 불필요.

-- 1. consultations.classification
ALTER TABLE consultations DROP CONSTRAINT IF EXISTS consultations_classification_check;
ALTER TABLE consultations ADD CONSTRAINT consultations_classification_check
  CHECK (classification IN ('dermatology', 'plastic_surgery', 'dentistry', 'unclassified'));

-- 2. faq_vectors.category
ALTER TABLE faq_vectors DROP CONSTRAINT IF EXISTS faq_vectors_category_check;
ALTER TABLE faq_vectors ADD CONSTRAINT faq_vectors_category_check
  CHECK (category IN ('dermatology', 'plastic_surgery', 'dentistry'));

-- 3. youtube_sources.category
ALTER TABLE youtube_sources DROP CONSTRAINT IF EXISTS youtube_sources_category_check;
ALTER TABLE youtube_sources ADD CONSTRAINT youtube_sources_category_check
  CHECK (category IN ('dermatology', 'plastic_surgery', 'dentistry'));

-- 4. classification_keywords.category
ALTER TABLE classification_keywords DROP CONSTRAINT IF EXISTS classification_keywords_category_check;
ALTER TABLE classification_keywords ADD CONSTRAINT classification_keywords_category_check
  CHECK (category IN ('dermatology', 'plastic_surgery', 'dentistry', 'boundary'));

-- 5. 치과 명확 키워드 seed
INSERT INTO classification_keywords (category, keyword) VALUES
('dentistry', '임플란트'),
('dentistry', '치아교정'),
('dentistry', '투명교정'),
('dentistry', '라미네이트'),
('dentistry', '크라운'),
('dentistry', '신경치료'),
('dentistry', '충치치료'),
('dentistry', '스케일링'),
('dentistry', '치주치료'),
('dentistry', '잇몸치료'),
('dentistry', '치아미백'),
('dentistry', '사랑니'),
('dentistry', '발치'),
('dentistry', '틀니'),
('dentistry', '브릿지'),
('dentistry', '부정교합');

-- 6. 경계 규칙: 미백 (치아 맥락 → 치과, 피부 맥락 → 피부과)
INSERT INTO classification_keywords (category, keyword, context_keywords) VALUES
('boundary', '미백', '{"dentistry": ["치아", "잇몸", "구강", "치아미백", "누런 치아"], "dermatology": ["피부", "톤", "잡티", "색소", "피부톤"]}');
