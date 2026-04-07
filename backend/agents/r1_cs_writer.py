"""R1 사전상담 리포트 — 상담실장이 본 상담 전 참고하는 고객 정보 + 니즈 요약 (4섹션, 한국어)"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """당신은 사전상담 리포트 전문 작성자입니다.
상담실장이 본 상담에 들어가기 전, 고객이 누구이고 무엇을 원하는지 빠르게 파악할 수 있도록
사전상담 내용을 4섹션으로 정리합니다.

톤 & 매너:
- 간결하고 객관적인 서술 (1~2문 이내)
- 고객의 요청과 상태를 중립적으로 정리
- 상담에서 실제 언급된 내용만 기재 (AI 추측 금지)
- 불필요한 수식어나 감정적 표현 배제

구성 (4섹션):
1. 고객 프로필 — 기본 정보 + 상담 경위
2. 고객 니즈 — 핵심 고민, 희망 결과, 언급 시술, 긴급도
3. 상담 맥락 — 현재 상태, 고객 질문, 감정/태도
4. 사전 준비사항 — 다음 상담 추천 주제, 추가 확인, 참고사항"""


async def write_r1_report(
    original_text: str,
    translated_text: str,
    intent_extraction: dict,
    classification: str,
    customer_name: str,
    input_lang: str = "ja",
    admin_direction: str | None = None,
) -> dict:
    category_label = "성형외과" if classification == "plastic_surgery" else "피부과"

    # 상담 원문
    if input_lang == "ko":
        consultation_section = f"== 상담 원문 (한국어) ==\n{original_text}"
    else:
        consultation_section = f"== 상담 원문 (일본어) ==\n{original_text}\n\n== 한국어 번역 ==\n{translated_text}"

    admin_direction_section = ""
    if admin_direction:
        admin_direction_section = f"""
== 관리자 수정 지시 (최우선 반영) ==
{admin_direction}
"""

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    date_str = f"{now_kst.year}년 {now_kst.month}월 {now_kst.day}일"

    prompt = f"""다음 사전상담 정보를 바탕으로, 상담실장이 본 상담 전 참고할 수 있는 사전상담 리포트를 JSON 형식으로 작성하세요.
각 항목은 1~2문 이내로 간결하게 작성하세요.

== 분류 ==
{category_label}

== 고객명 ==
{customer_name}

== 상담일 ==
{date_str}

{consultation_section}

== 의도 추출 결과 ==
{json.dumps(intent_extraction, ensure_ascii=False)}
{admin_direction_section}
== 출력 JSON 형식 ==
{{
    "title": "{customer_name} 고객 — {category_label} 사전상담 리포트",
    "date": "{date_str}",

    "section1_customer_profile": {{
        "name": "{customer_name}",
        "consultation_date": "{date_str}",
        "classification": "{category_label}",
        "summary": "상담 경위/배경 요약 1~2문"
    }},

    "section2_customer_needs": {{
        "main_concerns": ["핵심 고민 1", "핵심 고민 2"],
        "desired_outcome": "고객이 원하는 최종 결과 1~2문",
        "mentioned_procedures": ["고객이 언급한 시술명"],
        "urgency": "급함/보통/여유 (내원 시기 관련 언급 기반, 없으면 '미정')"
    }},

    "section3_consultation_context": {{
        "current_state": "현재 상태/과거 시술 이력 1~2문 (언급 없으면 '정보 없음')",
        "key_questions": ["고객이 질문한 내용 1", "질문 2"],
        "emotional_tone": "고객의 태도/감정 상태 1문 (불안, 적극적, 탐색적 등)"
    }},

    "section4_next_steps": {{
        "recommended_topics": ["다음 상담에서 다뤄야 할 주제 1", "주제 2"],
        "additional_checks": ["추가 확인 필요사항 1"],
        "notes": "특이사항/참고사항 1~2문 (없으면 null)"
    }}
}}

중요 규칙:
- 상담에서 언급된 내용만 기재 (AI 추측 금지)
- 각 항목 1~2문 이내 간결하게
- 4섹션 모두 필수
- 비용/가격 정보는 포함하지 않음"""

    report = None
    for parse_attempt in range(2):
        result = await generate_json(prompt, SYSTEM_INSTRUCTION)
        try:
            report = safe_parse_json(result)
            if isinstance(report, list):
                report = report[0] if report else {}
            break
        except json.JSONDecodeError as e:
            logger.warning(f"[R1Writer] JSON parse error (attempt {parse_attempt + 1}): {str(e)[:100]}")
            if parse_attempt == 0:
                await asyncio.sleep(3)
            else:
                raise ValueError(f"R1 Report JSON parse failed after 2 attempts: {str(e)}")

    report["date"] = date_str
    return report
