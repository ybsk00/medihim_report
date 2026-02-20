import json
from services.gemini_client import generate_json, safe_parse_json

SYSTEM_INSTRUCTION = """당신은 일본어→한국어 의료 문서 번역 전문가입니다.
일본어 리포트 JSON을 동일한 구조의 한국어 버전으로 번역하세요.

번역 규칙:
- 의료 용어는 정확하게 번역
- 원본 JSON 구조를 그대로 유지 (9섹션 구조)
- 자연스러운 한국어 어투 사용
- 중립적·정리형 어투 유지 ("~입니다", "~로 판단됩니다", "~이 권장됩니다")
- 날짜, 숫자는 원문 그대로 유지"""


async def translate_report_to_korean(report_data: dict) -> dict:
    prompt = f"""다음 일본어 리포트 JSON을 한국어로 번역하세요.
JSON 구조는 그대로 유지하고 텍스트만 한국어로 번역하세요.

원본 JSON:
{json.dumps(report_data, ensure_ascii=False, indent=2)}

한국어 번역된 동일 구조의 JSON을 반환하세요."""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    data = safe_parse_json(result)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data
