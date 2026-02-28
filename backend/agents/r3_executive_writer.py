import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """당신은 병원 경영진용 종합 분석 리포트 전문 작성자입니다.
경영진이 환자 케이스를 전략적으로 판단할 수 있도록 마케팅, 의료, 환자관리 3기둥 분석과
경영진 요약을 한국어로 작성합니다.

톤 & 매너:
- 경영 전략적 관점에서 간결하고 핵심적으로 서술
- 데이터 기반 판단 근거 제시
- 액션 아이템은 구체적이고 실행 가능하게
- 각 항목 1~2문 이내
- R1(의사) + R2(상담실장) 리포트를 종합하여 경영 관점으로 재구성

구성 (4섹션 — 3기둥 + 요약):
1. 마케팅 분석 — CTA, 니즈, 방문 가능성, 전환 요인, 접근 전략
2. 의료 분석 — 분류, 시술 복잡도, 리소스 요약, 리스크 수준
3. 환자 관리 전략 — 후속 전략, 업셀 기회, 방문 유도, 유의사항
4. 경영진 요약 — 한 줄 요약 + 액션 아이템 3개"""


async def write_r3_report(
    r1_report_data: dict,
    r2_report_data: dict,
    intent_extraction: dict,
    classification: str,
    customer_name: str,
    cta_level: str | None = None,
    cta_signals: list | None = None,
    admin_direction: str | None = None,
) -> dict:
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

    prompt = f"""다음 정보를 바탕으로 병원 경영진용 종합 분석 리포트를 JSON 형식으로 작성하세요.
R1(의사) + R2(상담실장) 리포트를 종합하여 경영 전략적 관점에서 분석합니다.

== 분류 ==
{category_label}

== 환자명 ==
{customer_name}

== R1 의사 리포트 ==
{json.dumps(r1_report_data, ensure_ascii=False, indent=2)}

== R2 상담실장 리포트 ==
{json.dumps(r2_report_data, ensure_ascii=False, indent=2)}

== 의도 추출 결과 ==
{json.dumps(intent_extraction, ensure_ascii=False)}

== CTA 정보 ==
{cta_info}
{admin_direction_section}
== 출력 JSON 형식 ==
{{
    "title": "{customer_name} 환자 — {category_label} 종합 분석",
    "date": "{date_str}",

    "pillar1_marketing": {{
        "cta_assessment": "CTA 레벨 및 판단 근거 1~2문",
        "patient_needs": ["핵심 니즈 1", "핵심 니즈 2", "핵심 니즈 3"],
        "visit_likelihood": "방문 가능성 평가 (높음/보통/낮음 + 근거 1문)",
        "conversion_factors": ["전환 촉진 요인 1", "전환 촉진 요인 2"],
        "approach_strategy": "접근 전략 1~2문"
    }},

    "pillar2_medical": {{
        "classification": "{category_label}",
        "procedure_complexity": "시술 복잡도 (높음/보통/낮음 + 근거 1문)",
        "resource_summary": "필요 리소스 요약 1~2문",
        "risk_level": "리스크 수준 (높음/보통/낮음 + 근거 1문)",
        "expected_outcome": "예상 결과/만족도 1문"
    }},

    "pillar3_patient_management": {{
        "follow_up_strategy": "후속 관리 전략 1~2문",
        "upsell_opportunities": ["업셀 기회 1", "업셀 기회 2"],
        "visit_inducement": "방문 유도 방안 1~2문",
        "cautions": ["유의사항 1", "유의사항 2"]
    }},

    "executive_summary": {{
        "one_liner": "한 줄 요약 (핵심 판단 포인트)",
        "action_items": [
            "액션 아이템 1 (구체적, 실행 가능)",
            "액션 아이템 2",
            "액션 아이템 3"
        ]
    }}
}}

중요 규칙:
- R1, R2 내용과 모순되지 않도록 작성
- 경영 관점에서 투자 대비 효과(ROI) 시사점 포함
- 액션 아이템은 담당자가 바로 실행 가능한 수준으로 구체적으로
- 4섹션 모두 필수
- 각 항목 1~2문 이내 간결하게"""

    report = None
    for parse_attempt in range(2):
        result = await generate_json(prompt, SYSTEM_INSTRUCTION)
        try:
            report = safe_parse_json(result)
            if isinstance(report, list):
                report = report[0] if report else {}
            break
        except json.JSONDecodeError as e:
            logger.warning(f"[R3Writer] JSON parse error (attempt {parse_attempt + 1}): {str(e)[:100]}")
            if parse_attempt == 0:
                await asyncio.sleep(3)
            else:
                raise ValueError(f"R3 Report JSON parse failed after 2 attempts: {str(e)}")

    report["date"] = date_str
    return report
