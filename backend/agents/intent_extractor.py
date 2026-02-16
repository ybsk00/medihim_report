import json
from services.gemini_client import generate_json

SYSTEM_INSTRUCTION = """당신은 의료 상담 분석 전문가입니다. 한국어로 번역된 상담 내용에서 환자의 의도를 구조화하여 추출해주세요.

추출 항목:
- main_concerns: 환자의 핵심 고민 (최대 5개)
- desired_direction: 환자가 원하는 방향 (1~2줄)
- unwanted: 환자가 원하지 않는 것
- mentioned_procedures: 언급된 시술명
- body_parts: 관련 부위
- keywords: 핵심 키워드 (벡터 검색용, 최대 10개)"""


async def extract_intent(translated_text: str) -> dict:
    prompt = f"""다음 상담 내용에서 환자의 의도를 추출해주세요.

JSON 형식으로 반환:
{{
    "main_concerns": ["고민1", "고민2", "고민3"],
    "desired_direction": "환자가 원하는 방향 설명",
    "unwanted": "원하지 않는 것",
    "mentioned_procedures": ["시술명1", "시술명2"],
    "body_parts": ["부위1", "부위2"],
    "keywords": ["키워드1", "키워드2", "키워드3"]
}}

상담 내용 (한국어):
{translated_text}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    data = json.loads(result)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data
