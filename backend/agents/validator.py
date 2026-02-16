import json
from services.gemini_client import generate_json

SYSTEM_INSTRUCTION = """당신은 의료 상담 분류 검증 전문가입니다.
분류 에이전트의 결과를 검증하여 최종 분류를 확정하거나, 관리자 검토가 필요한 경우 unclassified로 플래그합니다.

검증 기준:
- 신뢰도 0.8 이상 + 명확 키워드 매칭 → 확정
- 경계 시술이거나 신뢰도 0.8 미만 → 재검토
- 재검토 후에도 불확실 → unclassified"""


async def validate_classification(
    classification_result: dict,
    translated_text: str,
    intent_extraction: dict,
) -> dict:
    if isinstance(classification_result, list):
        classification_result = classification_result[0] if classification_result else {}
    confidence = classification_result.get("confidence", 0.0)
    classification = classification_result.get("classification", "unclassified")

    # 높은 신뢰도이고 unclassified가 아니면 바로 확정
    if confidence >= 0.85 and classification != "unclassified":
        return {
            "classification": classification,
            "confidence": confidence,
            "reason": classification_result.get("reason", ""),
            "validated": True,
        }

    # 낮은 신뢰도이거나 경계 시술 → LLM에 재검증 요청
    prompt = f"""이전 분류 결과를 검증해주세요.

이전 분류: {classification} (신뢰도: {confidence})
이전 근거: {classification_result.get('reason', '')}

의도 추출 결과:
{json.dumps(intent_extraction, ensure_ascii=False)}

상담 내용:
{translated_text}

이 분류가 정확한지 검증해주세요.
확실하지 않다면 "unclassified"로 반환하세요.

JSON 형식:
{{
    "classification": "dermatology" 또는 "plastic_surgery" 또는 "unclassified",
    "confidence": 0.0~1.0,
    "reason": "검증 근거 설명",
    "validated": true 또는 false
}}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    data = json.loads(result)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data
