-- ============================================
-- 분류 키워드 사전 초기 데이터
-- ============================================

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
