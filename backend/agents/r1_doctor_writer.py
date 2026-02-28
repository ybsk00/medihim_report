import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """당신은 의료 상담 브리핑 전문 작성자입니다.
의사가 환자를 진료하기 전에 참고할 수 있는 사전 브리핑 리포트를 한국어로 작성합니다.

톤 & 매너:
- 의료 전문 용어를 정확하게 사용
- 간결하고 객관적인 서술 (1~2문 이내)
- 환자의 호소 내용을 중립적으로 정리
- 불필요한 수식어나 감정적 표현 배제
- 상담에서 실제 언급된 내용만 기재

구성 (7섹션):
1. 환자 개요 — 이름, 분류, CTA 레벨, 상담일
2. 핵심 호소 — 환자의 주요 고민 3~5개
3. 언급 시술 — 상담 중 언급된 시술명과 맥락
4. 의학적 맥락 — 현재 상태, 관련 병력, 핵심 우려
5. 환자 우려사항 — 환자가 반복 언급한 우려 + 우선순위
6. 내원 의지 — CTA 레벨, 근거 발화, 예상 방문일
7. 사전 참고사항 — 예비 소견, 추천 검사, 주의점"""


async def write_r1_report(
    original_text: str,
    translated_text: str,
    intent_extraction: dict,
    classification: str,
    rag_results: list[dict],
    customer_name: str,
    cta_level: str | None = None,
    cta_signals: list | None = None,
    speaker_segments: list | None = None,
    admin_direction: str | None = None,
    input_lang: str = "ja",
) -> dict:
    rag_context = ""
    if rag_results:
        for i, faq in enumerate(rag_results, 1):
            rag_context += f"\n【참고자료 {i}】\nQ: {faq.get('question', '')}\nA: {faq.get('answer', '')}\n시술명: {faq.get('procedure_name', '')}\n"
    if not rag_context:
        rag_context = "※참고자료 없음. 상담 내용만 기반으로 작성하세요."

    category_label = "성형외과" if classification == "plastic_surgery" else "피부과"

    admin_direction_section = ""
    if admin_direction:
        admin_direction_section = f"""
== 관리자 수정 지시 (최우선 반영) ==
{admin_direction}
"""

    # 화자 분리 데이터
    speaker_info = ""
    if speaker_segments:
        speaker_info = "\n== 화자별 발화 ==\n"
        for seg in speaker_segments[:30]:
            role = "상담사" if seg.get("speaker") == "counselor" else "고객"
            speaker_info += f"[{role}] {seg.get('text', '')}\n"

    # CTA 정보
    cta_info = ""
    if cta_level:
        cta_info = f"\n== CTA 분석 ==\n레벨: {cta_level.upper()}\n"
        if cta_signals:
            cta_info += "근거 발화:\n"
            for sig in cta_signals[:5]:
                cta_info += f"- {sig}\n"

    # 상담 원문
    if input_lang == "ko":
        consultation_section = f"== 상담 원문 (한국어) ==\n{original_text}"
    else:
        consultation_section = f"== 상담 원문 (일본어) ==\n{original_text}\n\n== 한국어 번역 ==\n{translated_text}"

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    date_str = f"{now_kst.year}년 {now_kst.month}월 {now_kst.day}일"

    prompt = f"""다음 상담 정보를 바탕으로 의사용 사전 브리핑 리포트를 JSON 형식으로 작성하세요.
각 항목은 1~2문 이내로 간결하게 작성하고, 상담에서 실제 언급된 내용만 기재하세요.

== 분류 ==
{category_label}

== 환자명 ==
{customer_name}

== 상담일 ==
{date_str}

{consultation_section}
{speaker_info}
{cta_info}
== 의도 추출 결과 ==
{json.dumps(intent_extraction, ensure_ascii=False)}

== 참고자료 (내용 검증용, 직접 인용 금지) ==
{rag_context}
{admin_direction_section}
== 출력 JSON 형식 ==
{{
    "title": "{customer_name} 환자 — {category_label} 사전 브리핑",
    "date": "{date_str}",

    "section1_patient_overview": {{
        "name": "{customer_name}",
        "classification": "{category_label}",
        "cta_level": "{cta_level or '미분석'}",
        "consultation_date": "{date_str}",
        "summary": "환자 상담 요약 1문"
    }},

    "section2_chief_complaints": {{
        "summary": "핵심 호소 내용 요약 1~2문",
        "points": [
            "호소 1 (간결하게)",
            "호소 2",
            "호소 3"
        ]
    }},

    "section3_mentioned_procedures": {{
        "procedures": [
            {{
                "name": "시술명",
                "context": "상담 중 언급된 맥락 1문",
                "patient_attitude": "환자의 태도 (적극적/관심/소극적)"
            }}
        ]
    }},

    "section4_medical_context": {{
        "current_state": "현재 상태 설명 1~2문",
        "related_history": "관련 병력/과거 시술 (있을 경우, 없으면 null)",
        "key_concerns": [
            "핵심 의학적 우려 1",
            "핵심 의학적 우려 2"
        ]
    }},

    "section5_patient_concerns": {{
        "concerns": [
            {{
                "concern": "우려사항",
                "priority": "high/medium/low"
            }}
        ]
    }},

    "section6_visit_intent": {{
        "cta_level": "{cta_level or '미분석'}",
        "evidence": ["근거 발화 1 (원문)", "근거 발화 2"],
        "expected_visit": "예상 방문 시기 (언급이 없으면 '미정')"
    }},

    "section7_doctor_notes": {{
        "preliminary_opinion": "예비 소견 1~2문",
        "recommended_tests": ["추천 검사 1", "추천 검사 2"],
        "cautions": ["주의점 1", "주의점 2"]
    }}
}}

중요 규칙:
- 상담에서 언급된 내용만 기재 (AI 추측 금지)
- 비용/가격 정보는 포함하지 않음
- 의료 전문 용어 정확하게 사용
- 각 항목 1~2문 이내 간결하게
- 7섹션 모두 필수"""

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
