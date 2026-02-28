import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """당신은 병원 운영 브리핑 전문 작성자입니다.
상담실장이 시술 준비 및 환자 응대에 참고할 수 있는 운영 리포트를 한국어로 작성합니다.

톤 & 매너:
- 실무 중심의 간결한 서술
- 구체적인 리소스, 일정, 비용 정보 포함
- 비용 추정은 허용하되 반드시 "추정치" 라벨을 표시
- 의사 리포트(R1)의 소견을 기반으로 확장
- 각 항목 1~2문 이내

구성 (5섹션):
1. 시술 요약 — R1 기반 의사 소견 + 추천 시술 목록
2. 필요 리소스 — 장비, 재료, 인력, 예상 시간
3. 비용 계획 — AI 추정 허용 (추정치 라벨 필수)
4. 일정 계획 — 사전 검사, 시술일, 입원 기간, 후속 일정
5. 환자 준비도 — CTA 레벨, 결정 요인, 장벽, 권장 조치"""


async def write_r2_report(
    r1_report_data: dict,
    intent_extraction: dict,
    classification: str,
    rag_results: list[dict],
    customer_name: str,
    cta_level: str | None = None,
    cta_signals: list | None = None,
    admin_direction: str | None = None,
) -> dict:
    rag_context = ""
    if rag_results:
        for i, faq in enumerate(rag_results, 1):
            rag_context += f"\n【참고자료 {i}】\nQ: {faq.get('question', '')}\nA: {faq.get('answer', '')}\n시술명: {faq.get('procedure_name', '')}\n"
    if not rag_context:
        rag_context = "※참고자료 없음."

    category_label = "성형외과" if classification == "plastic_surgery" else "피부과"

    admin_direction_section = ""
    if admin_direction:
        admin_direction_section = f"""
== 관리자 수정 지시 (최우선 반영) ==
{admin_direction}
"""

    cta_info = ""
    if cta_level:
        cta_info = f"CTA 레벨: {cta_level.upper()}"
        if cta_signals:
            cta_info += "\n근거 발화: " + " / ".join(cta_signals[:3])

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    date_str = f"{now_kst.year}년 {now_kst.month}월 {now_kst.day}일"

    prompt = f"""다음 정보를 바탕으로 상담실장용 운영 리포트를 JSON 형식으로 작성하세요.
R1 의사 리포트의 소견을 기반으로, 실무 관점에서 시술 준비 및 환자 응대 정보를 정리합니다.

== 분류 ==
{category_label}

== 환자명 ==
{customer_name}

== R1 의사 리포트 (참조) ==
{json.dumps(r1_report_data, ensure_ascii=False, indent=2)}

== 의도 추출 결과 ==
{json.dumps(intent_extraction, ensure_ascii=False)}

== CTA 정보 ==
{cta_info}

== 참고자료 ==
{rag_context}
{admin_direction_section}
== 출력 JSON 형식 ==
{{
    "title": "{customer_name} 환자 — {category_label} 운영 브리핑",
    "date": "{date_str}",

    "section1_procedure_summary": {{
        "doctor_opinion": "R1 기반 의사 소견 요약 1~2문",
        "recommended_procedures": [
            {{
                "name": "시술명",
                "priority": "primary/secondary",
                "note": "간단 설명 1문"
            }}
        ]
    }},

    "section2_resource_requirements": {{
        "equipment": ["필요 장비 1", "필요 장비 2"],
        "materials": ["재료 1", "재료 2"],
        "staff": "필요 인력 (예: 집도의 1명, 간호사 2명)",
        "estimated_duration": "예상 시술 시간 (예: 1~2시간)"
    }},

    "section3_cost_planning": {{
        "items": [
            {{
                "procedure": "시술명",
                "estimated_cost": "추정 비용 범위 (예: 200~400만원)",
                "is_estimate": true
            }}
        ],
        "total_estimate": "총 추정 비용 범위",
        "note": "추정치 안내 문구 (예: 실제 비용은 진료 후 확정)"
    }},

    "section4_scheduling": {{
        "patient_preferred_date": "환자 희망일 (언급 없으면 '미정')",
        "pre_tests": ["사전 검사 1", "사전 검사 2"],
        "hospitalization": "입원 기간 (해당시, 없으면 null)",
        "follow_up": ["후속 일정 1", "후속 일정 2"]
    }},

    "section5_patient_readiness": {{
        "cta_level": "{cta_level or '미분석'}",
        "decision_factors": ["결정 요인 1", "결정 요인 2"],
        "barriers": ["장벽 1", "장벽 2"],
        "recommended_actions": ["권장 조치 1", "권장 조치 2"]
    }}
}}

중요 규칙:
- 비용 추정은 허용하되, is_estimate: true와 "추정치" 표시 필수
- R1 의사 소견과 모순되지 않도록 작성
- 각 항목 1~2문 이내 간결하게
- 5섹션 모두 필수
- 실무에 바로 활용 가능한 구체적 정보 기재"""

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
