-- 010: 음성 감정 분석 결과 저장 컬럼 추가
-- consultations 테이블에 음성 분석 데이터 저장

ALTER TABLE consultations
ADD COLUMN IF NOT EXISTS voice_emotion_analysis JSONB;

-- 구조:
-- {
--   "speech_patterns": { "hesitation_level", "confidence_level", "filler_words", "examples" },
--   "intonation": { "dominant_pattern", "question_ratio", "examples" },
--   "speech_speed": { "overall", "variation", "details" },
--   "silence": { "notable_pauses", "overall_silence_pattern" },
--   "voice_cta": { "level": "hot/warm/cool", "confidence_score": 0.0~1.0, "reasoning" },
--   "overall_emotion": { "primary_emotion", "secondary_emotion", "emotional_shift" },
--   "summary": "..."
-- }

COMMENT ON COLUMN consultations.voice_emotion_analysis IS '음성 감정 분석 결과 (Gemini 멀티모달). 말투/억양/말속도/침묵 분석 + 음성 CTA 판정';
