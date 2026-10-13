"""R2 의사용 리포트 — 의사가 시술 상담 전 참고하는 의료 분석 리포트 (5섹션, 한국어)"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """당신은 의사용 상담리포트 전문 작성자입니다.
의사가 환자 시술 상담 전에 임상적 판단을 빠르게 세울 수 있도록, 깊이 있는 의료 분석 리포트를 한국어로 작성합니다.

톤 & 매너:
- 의료 전문 용어를 정확하게 사용 (해부학적 구조, 시술 술기, 적응증/금기 등)
- 단순 나열이 아닌 임상적 추론을 담은 충실한 서술 (항목당 2~4문장)
- 상담에서 언급된 내용 + 참고자료(RAG)를 적극 종합하여 근거 제시
- 진단이 아닌 '소견' 수준으로 기재하되, 판단의 근거와 임상적 함의를 명확히
- 불필요한 미사여구는 배제하되, 임상 인사이트를 위한 분석은 충분히 전개

분석 깊이 가이드:
- 환자의 주소(主訴)를 해부학적·기능적 원인 가설과 연결하여 해석
- 추천 시술은 "무엇을" 넘어 "왜 이 환자에게 적합한지" 근거(해부학적 조건, 과거 이력, 환자 목표)를 제시
- 금기·위험요소는 일반론이 아니라 이 환자의 조건에 비추어 구체화
- RAG 참고자료의 의료 근거를 환자 상황에 맞게 재해석하여 반영

구성 (5섹션):
1. 환자 요약 — 기본정보, 주소(主訴), 이전 상담 이력과 그 임상적 맥락
2. 의학적 평가 — 현재 상태, 관련 병력, 핵심 소견 및 원인 가설
3. 시술 옵션 — 추천 시술(근거 포함), 대안, 환자별 금기사항
4. 임상 고려사항 — 위험 요소, 예상 결과, 회복 개요
5. 진료 전 참고 — 추천 검사, 환자 준비도, 의사 메모"""


async def write_r2_report(
    original_text: str,
    translated_text: str,
    intent_extraction: dict,
    classification: str,
    rag_results: list[dict],
    customer_name: str,
    cta_level: str | None = None,
    cta_signals: list | None = None,
    r1_report_data: dict | None = None,
    admin_direction: str | None = None,
    input_lang: str = "ja",
    voice_emotion_analysis: dict | None = None,
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

    # 이전 회차(1차) R1 참조 데이터
    r1_section = ""
    if r1_report_data:
        r1_section = f"""
== 1차 사전상담 리포트 (참조) ==
{json.dumps(r1_report_data, ensure_ascii=False, indent=2)}
"""
    else:
        r1_section = "\n== 1차 사전상담 리포트 ==\n※ 이전 상담 데이터 없음. 현재 상담 내용만으로 작성하세요.\n"

    # CTA 정보
    cta_info = ""
    if cta_level:
        cta_info = f"CTA 레벨: {cta_level.upper()}"
        if cta_signals:
            cta_info += "\n근거 발화: " + " / ".join(cta_signals[:3])

    # 상담 원문
    if input_lang == "ko":
        consultation_section = f"== 상담 원문 (한국어) ==\n{original_text}"
    else:
        consultation_section = f"== 상담 원문 (일본어) ==\n{original_text}\n\n== 한국어 번역 ==\n{translated_text}"

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    date_str = f"{now_kst.year}년 {now_kst.month}월 {now_kst.day}일"

    prompt = f"""다음 정보를 바탕으로 의사용 2차 상담리포트를 JSON 형식으로 작성하세요.
의사가 환자 시술 상담 전에 참고할 수 있는 의료 분석 리포트입니다.

== 분류 ==
{category_label}

== 환자명 ==
{customer_name}

== 상담일 ==
{date_str}

{consultation_section}
{r1_section}
== 의도 추출 결과 ==
{json.dumps(intent_extraction, ensure_ascii=False)}

== CTA 정보 ==
{cta_info}

== 참고자료 (의료 근거용) ==
{rag_context}
{admin_direction_section}
== 출력 JSON 형식 ==
{{
    "title": "{customer_name} 환자 — {category_label} 의사용 상담리포트",
    "date": "{date_str}",

    "section1_patient_summary": {{
        "name": "{customer_name}",
        "classification": "{category_label}",
        "consultation_date": "{date_str}",
        "chief_complaint": "주소(主訴) + 환자가 호소한 핵심 문제의 임상적 정리 2~3문장",
        "consultation_history": "이전 상담(1차) 요약과 그 임상적 시사점 2~3문장 (없으면 null)"
    }},

    "section2_medical_assessment": {{
        "current_condition": "현재 상태 평가 + 해부학적/기능적 원인 가설 2~4문장",
        "relevant_history": "관련 병력/과거 시술과 그것이 현재 평가·시술 계획에 주는 임상적 영향 (없으면 null)",
        "key_findings": ["의학적 소견 1 — 관찰/추정과 그 근거 (1~2문)", "소견 2 (1~2문)"]
    }},

    "section3_treatment_options": {{
        "recommended_procedures": [
            {{
                "name": "시술명",
                "rationale": "이 환자에게 적합한 이유 — 해부학적 조건/과거 이력/환자 목표와 연결한 근거 2~3문장",
                "priority": "primary 또는 secondary"
            }}
        ],
        "alternative_approaches": ["대안 시술명 + 어떤 경우 고려하는지 (있으면)"],
        "contraindications": ["이 환자 조건에 비춘 금기/주의사항 + 이유 (있으면)"]
    }},

    "section4_clinical_considerations": {{
        "risk_factors": ["위험 요소 1 — 이 환자에게 왜 유의해야 하는지 (1~2문)", "위험 요소 2 (1~2문)"],
        "expected_outcome": "예상 결과 + 한계/변수까지 2~3문장",
        "recovery_overview": "회복 기간 개요 + 주요 단계별 특징 2~3문장"
    }},

    "section5_pre_consultation_notes": {{
        "recommended_tests": ["추천 검사 + 목적 (1문)", "검사 2"],
        "patient_readiness": "환자 준비도/의지 평가 + 근거 2~3문장 (CTA·발화 기반, 없으면 '미분석')",
        "doctor_notes": "상담 시 의사가 짚어야 할 포인트·소통 전략 2~3문장"
    }}
}}

중요 규칙:
- 상담에서 언급된 내용 + 참고자료(RAG)를 적극 종합하여 작성
- 진단이 아닌 '소견' 수준으로 기재하되, 판단 근거와 임상적 함의를 명확히
- 각 항목은 단순 요약이 아니라 임상적 추론을 담아 충실하게 (항목당 2~4문장). 단, 근거 없는 일반론으로 늘리지 말 것
- 5섹션 모두 필수
- 비용 정보는 포함하지 않음 (의사용 리포트는 의료 관점만)"""

    report = None
    for parse_attempt in range(2):
        result = await generate_json(prompt, SYSTEM_INSTRUCTION)
        try:
            report = safe_parse_json(result)
            if isinstance(report, list):
                report = report[0] if report else {}
            break
        except json.JSONDecodeError as e:
            logger.warning(f"[R2Writer] JSON parse error (attempt {parse_attempt + 1}): {str(e)[:100]}")
            if parse_attempt == 0:
                await asyncio.sleep(3)
            else:
                raise ValueError(f"R2 Report JSON parse failed after 2 attempts: {str(e)}")

    report["date"] = date_str
    return report
