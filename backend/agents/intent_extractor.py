from services.gemini_client import generate_json, safe_parse_json

SYSTEM_INSTRUCTION = """당신은 의료 상담 분석 전문가입니다. 한국어로 번역된 상담 내용에서 환자의 의도를 구조화하여 추출해주세요.

추출 항목:
- main_concerns: 환자의 핵심 고민 (최대 5개)
- desired_direction: 환자가 원하는 방향 (1~2줄)
- unwanted: 환자가 원하지 않는 것
- mentioned_procedures: 언급된 시술명
- body_parts: 관련 부위
- keywords: 핵심 키워드 (벡터 검색용, 최대 10개)
- cost_mentions: 상담에서 언급된 모든 비용/가격 정보 (병원 유무와 무관하게 추출)
- visit_schedule: 상담에서 언급된 내원 일정/날짜 정보
- hospital_mentions: 상담에서 언급된 병원/클리닉별 정보 (아래 구조 참조)

cost_mentions 추출 규칙:
- 상담사 또는 고객이 언급한 모든 금액/비용 정보를 빠짐없이 추출
- 병원명이 없어도 시술 비용이 언급되면 반드시 추출
- "만원", "만 원", "万ウォン", "万円" 등 금액 표현을 정확히 캡처
- 추가 비용, 포함 항목, 할인 정보도 함께 기록
- 상담에서 실제 언급된 금액만 기재 (AI 추측/창작 금지)
- 비용 언급이 없으면 빈 배열 [] 반환

visit_schedule 추출 규칙:
- 상담에서 구체적인 날짜, 월, 시기가 언급된 경우 추출
- 예: "3月15日", "来月", "春休み中", "7월에 방문", "다음 달" 등
- 날짜 언급이 없으면 null 반환

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
    "cost_mentions": [
        {{
            "item": "시술명 또는 비용 항목",
            "amount": "언급된 금액 (원문 그대로, 예: 약 150만~200만원)",
            "context": "누가 언급했는지 간단히 (예: 상담사가 설명)"
        }}
    ],
    "visit_schedule": {{
        "mentioned_dates": ["언급된 구체적 날짜 (예: 3月15日, 7월)"],
        "preferred_timing": "선호 시기 (예: 봄방학 중, 없으면 null)",
        "context": "일정 관련 맥락 (예: 고객이 3월 중 방문 희망)"
    }},
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

주의:
- cost_mentions는 상담에서 금액/비용이 언급된 경우 병원 유무와 무관하게 모두 추출합니다. 비용 언급이 없으면 빈 배열 []로 반환하세요.
- visit_schedule은 날짜/시기 언급이 없으면 null로 반환하세요.
- hospital_mentions는 상담에서 병원명이 구체적으로 언급된 경우에만 추출합니다. 병원 언급이 없으면 빈 배열 []로 반환하세요.
- 상담에서 실제 언급된 내용만 기재하고, AI가 추측하거나 창작하지 마세요.

상담 내용 (한국어):
{translated_text}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    data = safe_parse_json(result)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data
