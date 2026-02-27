from services.gemini_client import generate_json, safe_parse_json

SYSTEM_INSTRUCTION = """당신은 의료 상담 분석 전문가입니다. 한국어로 번역된 상담 내용에서 환자의 의도를 구조화하여 추출해주세요.

추출 항목:
- main_concerns: 환자의 핵심 고민 (최대 5개)
- desired_direction: 환자가 원하는 방향 (1~2줄)
- unwanted: 환자가 원하지 않는 것
- mentioned_procedures: 언급된 시술명
- body_parts: 관련 부위
- keywords: 핵심 키워드 (벡터 검색용, 최대 10개)
- hospital_mentions: 상담에서 언급된 병원/클리닉별 정보 (아래 구조 참조)

hospital_mentions 추출 규칙:
- 상담 대화에서 병원명, 클리닉명이 구체적으로 언급된 경우에만 추출
- 각 병원별로 언급된 시술, 장점, 가격, 회복기간 등을 분리하여 기록
- 상담에서 실제 언급된 내용만 기재 (AI 추측/창작 금지)
- 병원 언급이 없으면 빈 배열 [] 반환"""


async def extract_intent(translated_text: str) -> dict:
    prompt = f"""다음 상담 내용에서 환자의 의도를 추출해주세요.

JSON 형식으로 반환:
{{
    "main_concerns": ["고민1", "고민2", "고민3"],
    "desired_direction": "환자가 원하는 방향 설명",
    "unwanted": "원하지 않는 것",
    "mentioned_procedures": ["시술명1", "시술명2"],
    "body_parts": ["부위1", "부위2"],
    "keywords": ["키워드1", "키워드2", "키워드3"],
    "hospital_mentions": [
        {{
            "name": "병원/클리닉명",
            "procedures": ["해당 병원에서 언급된 시술명"],
            "advantages": ["해당 병원의 장점/특징"],
            "price_info": "언급된 가격 정보 (없으면 null)",
            "recovery_info": "언급된 회복기간 (없으면 null)",
            "other_details": "기타 언급된 사항 (없으면 null)"
        }}
    ]
}}

주의: hospital_mentions는 상담에서 병원명이 구체적으로 언급된 경우에만 추출합니다.
병원 언급이 없으면 빈 배열 []로 반환하세요.
상담에서 실제 언급된 내용만 기재하고, AI가 추측하거나 창작하지 마세요.

상담 내용 (한국어):
{translated_text}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    data = safe_parse_json(result)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data
