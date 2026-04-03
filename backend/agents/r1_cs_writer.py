# [비활성화] 1차 상담리포트 - 사전상담 CS용. 추후 활성화 예정
import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """당신은 1차 상담리포트 전문 작성자입니다. (CS 사전상담용)
CS 담당자가 고객과의 사전 상담 내용을 간결하게 요약하는 리포트를 한국어로 작성합니다.

톤 & 매너:
- 간결하고 명확한 서술
- 고객의 요청과 상담 내용을 객관적으로 정리
- 각 항목 1~2문 이내
- 상담에서 실제 언급된 내용만 기재

구성 (3섹션):
1. 상담 개요 — 고객명, 상담일, 분류, 상담 요약
2. 고객 요구사항 — 핵심 고민, 희망 시술, 기대사항
3. 후속 조치 — 다음 단계 안내, 추가 확인 필요사항"""


async def write_r1_report(
    original_text: str,
    translated_text: str,
    intent_extraction: dict,
    classification: str,
    customer_name: str,
    input_lang: str = "ja",
) -> dict:
    category_label = "성형외과" if classification == "plastic_surgery" else "피부과"

    # 상담 원문
    if input_lang == "ko":
        consultation_section = f"== 상담 원문 (한국어) ==\n{original_text}"
    else:
        consultation_section = f"== 상담 원문 (일본어) ==\n{original_text}\n\n== 한국어 번역 ==\n{translated_text}"

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    date_str = f"{now_kst.year}년 {now_kst.month}월 {now_kst.day}일"

    prompt = f"""다음 상담 정보를 바탕으로 CS 사전상담 요약 리포트를 JSON 형식으로 작성하세요.
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

== 출력 JSON 형식 ==
{{
    "title": "{customer_name} 고객 — {category_label} 1차 상담리포트",
    "date": "{date_str}",

    "section1_consultation_overview": {{
        "name": "{customer_name}",
        "classification": "{category_label}",
        "consultation_date": "{date_str}",
        "summary": "상담 내용 요약 2~3문"
    }},

    "section2_customer_needs": {{
        "main_concerns": ["핵심 고민 1", "핵심 고민 2"],
        "desired_procedures": ["희망 시술 1"],
        "expectations": "고객 기대사항 1~2문"
    }},

    "section3_follow_up": {{
        "next_steps": ["다음 단계 1", "다음 단계 2"],
        "additional_checks": ["추가 확인 필요사항 1"]
    }}
}}

중요 규칙:
- 상담에서 언급된 내용만 기재
- 각 항목 1~2문 이내 간결하게
- 3섹션 모두 필수"""

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
