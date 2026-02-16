import json
from services.gemini_client import generate_json

SYSTEM_INSTRUCTION = """당신은 일본어→한국어 의료 문서 번역 전문가입니다.
일본어 리포트 JSON을 동일한 구조의 한국어 버전으로 번역하세요.

번역 규칙:
- 의료 용어는 정확하게 번역
- 원본 JSON 구조를 그대로 유지
- 자연스러운 한국어 어투 사용
- 제안형 표현 유지 ("~로 이해되었습니다", "~을 추천드립니다")
- citation 내의 title은 한국어로 번역할 것 (논문 제목을 한국어로)
- citation 내의 URL, journal, year는 번역하지 않고 원문 그대로 유지
- citation 내의 stat(통계 수치)은 한국어로 번역할 것"""


async def translate_report_to_korean(report_data: dict) -> dict:
    prompt = f"""다음 일본어 리포트 JSON을 한국어로 번역하세요.
JSON 구조는 그대로 유지하고 텍스트만 한국어로 번역하세요.

원본 JSON:
{json.dumps(report_data, ensure_ascii=False, indent=2)}

한국어 번역된 동일 구조의 JSON을 반환하세요."""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    data = json.loads(result)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data
