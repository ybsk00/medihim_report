import json
from services.gemini_client import generate_json
from services.supabase_client import get_supabase

SYSTEM_INSTRUCTION = """당신은 의료 상담 분류 전문가입니다.
상담 내용을 분석하여 피부과(dermatology) 또는 성형외과(plastic_surgery)로 분류하세요.

분류 원칙:
1. 단일 분류 원칙: 피부과 OR 성형외과. 혼합 분류 불가.
2. 핵심 의도(주소)가 기준.
3. 경계 시술(보톡스, 필러)은 동반 키워드로 판단.
4. 맥락 단서 없으면 unclassified."""


async def classify_consultation(
    translated_text: str, intent_extraction: dict
) -> dict:
    db = get_supabase()

    # DB에서 키워드 사전 조회
    keywords_result = db.table("classification_keywords").select("*").execute()
    keywords = keywords_result.data

    # 키워드 목록 정리
    plastic_keywords = [k["keyword"] for k in keywords if k["category"] == "plastic_surgery"]
    derma_keywords = [k["keyword"] for k in keywords if k["category"] == "dermatology"]
    boundary_keywords = [k for k in keywords if k["category"] == "boundary"]

    prompt = f"""다음 상담 내용을 피부과(dermatology) 또는 성형외과(plastic_surgery)로 분류하세요.

== 분류 키워드 사전 ==
성형외과 키워드: {', '.join(plastic_keywords)}
피부과 키워드: {', '.join(derma_keywords)}
경계 시술: {json.dumps([b['keyword'] for b in boundary_keywords], ensure_ascii=False)}

== 경계 시술 분류 규칙 ==
보톡스/필러가 언급된 경우:
- 성형 맥락 동반 (코 높이기, 턱 끝, 윤곽, 이마 볼륨, 리프팅 실) → 성형외과
- 피부 관리 맥락 동반 (레이저, 하이푸, 울쎄라, 피부결, 주름 개선, 탄력, 리쥬란) → 피부과
- 맥락 단서 없음 → unclassified

== 의도 추출 결과 ==
{json.dumps(intent_extraction, ensure_ascii=False)}

== 상담 내용 (한국어) ==
{translated_text}

JSON 형식으로 반환:
{{
    "classification": "dermatology" 또는 "plastic_surgery" 또는 "unclassified",
    "confidence": 0.0~1.0,
    "reason": "분류 근거 설명 (한국어)"
}}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    return json.loads(result)
