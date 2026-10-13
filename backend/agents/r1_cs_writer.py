"""R1 사전상담 리포트 — 상담실장이 본 상담 전 참고하는 고객 정보 + 니즈 요약 (4섹션, 한국어)"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)


def _build_voice_section(voice_emotion_analysis: dict | None) -> str:
    """음성 감정 분석 데이터를 프롬프트 섹션으로 변환"""
    if not voice_emotion_analysis or not isinstance(voice_emotion_analysis, dict):
        return ""
    v = voice_emotion_analysis
    lines = ["\n== 음성 감정 분석 (AI 음성 분석 결과) =="]
    sp = v.get("speech_patterns", {})
    if sp:
        lines.append(f"말투 — 망설임: {sp.get('hesitation_level', 'N/A')}, 확신도: {sp.get('confidence_level', 'N/A')}")
        fillers = sp.get("filler_words", [])
        if fillers:
            lines.append(f"  필러: {', '.join(fillers[:5])} (약 {sp.get('filler_count', '?')}회)")
    inton = v.get("intonation", {})
    if inton:
        lines.append(f"억양 — 패턴: {inton.get('dominant_pattern', 'N/A')}, 질문조: {inton.get('question_ratio', 'N/A')}")
    speed = v.get("speech_speed", {})
    if speed:
        lines.append(f"말 속도 — 전체: {speed.get('overall', 'N/A')}, 변동: {speed.get('variation', 'N/A')}")
    silence = v.get("silence", {})
    if silence and silence.get("notable_pauses"):
        lines.append("침묵:")
        for p in silence["notable_pauses"][:3]:
            lines.append(f"  - {p.get('context', '')}: 약 {p.get('estimated_duration', '?')}초 ({p.get('interpretation', '')})")
    vcta = v.get("voice_cta", {})
    if vcta:
        lines.append(f"음성 CTA — {vcta.get('level', 'N/A').upper()} (확신도: {vcta.get('confidence_score', 'N/A')})")
    emotion = v.get("overall_emotion", {})
    if emotion:
        lines.append(f"감정 — 주: {emotion.get('primary_emotion', 'N/A')}, 변화: {emotion.get('emotional_shift', 'N/A')}")
    summary = v.get("summary")
    if summary:
        lines.append(f"요약: {summary}")
    lines.append("※ 위 음성 분석을 section3_consultation_context의 emotional_tone에 반영하세요.")
    return "\n".join(lines)


SYSTEM_INSTRUCTION = """당신은 사전상담 리포트 전문 작성자입니다.
상담실장이 본 상담에 들어가기 전, 고객이 누구이고 무엇을 원하는지 깊이 있게 파악하고
상담 전략을 세울 수 있도록 사전상담 내용을 4섹션으로 분석·정리합니다.

톤 & 매너:
- 단순 나열이 아닌 분석과 해석을 담은 충실한 서술 (항목당 2~4문장, 맥락·근거 포함)
- 객관성을 유지하되, 상담실장이 본 상담을 설계할 수 있을 만큼 구체적으로
- 상담에서 실제 언급·관찰된 내용에 근거할 것. 사실 창작은 금지하되, 합리적 해석은 "~로 보임/추정됨"으로 명시
- 불필요한 미사여구는 배제하되, 인사이트를 위한 분석적 서술은 충분히 전개

분석 깊이 가이드:
- 고객이 "무엇을" 원하는지뿐 아니라 "왜" 원하는지, 어떤 망설임·기대·불안이 있는지 추론
- 과거 시술 이력은 단순 나열이 아니라 현재 니즈와의 연관성·만족도까지 해석
- 음성 감정 데이터가 있으면 텍스트만으로는 알 수 없는 심리 신호를 통합 해석
- 상담실장이 "이 고객을 어떻게 응대해야 하는가"에 대한 실질적 단서를 제공

구성 (4섹션):
1. 고객 프로필 — 기본 정보 + 상담 경위 + 고객 유형/성향 해석
2. 고객 니즈 — 표면 니즈 + 잠재 니즈, 희망 결과, 언급 시술, 긴급도와 그 근거
3. 상담 맥락 — 현재 상태, 고객 질문의 의도, 감정/태도 해석
4. 사전 준비사항 — 다음 상담 전략, 추가 확인 포인트, 주의해야 할 지점"""


async def write_r1_report(
    original_text: str,
    translated_text: str,
    intent_extraction: dict,
    classification: str,
    customer_name: str,
    input_lang: str = "ja",
    admin_direction: str | None = None,
    voice_emotion_analysis: dict | None = None,
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
각 항목은 단순 요약이 아니라 분석·해석을 담아 충실하게 작성하세요(항목당 2~4문장). 상담실장이 본 상담을 설계할 단서를 제공하는 것이 목표입니다.

== 분류 ==
{category_label}

== 고객명 ==
{customer_name}

== 상담일 ==
{date_str}

{consultation_section}

== 의도 추출 결과 ==
{json.dumps(intent_extraction, ensure_ascii=False)}
{_build_voice_section(voice_emotion_analysis)}
{admin_direction_section}
== 출력 JSON 형식 ==
{{
    "title": "{customer_name} 고객 — {category_label} 사전상담 리포트",
    "date": "{date_str}",

    "section1_customer_profile": {{
        "name": "{customer_name}",
        "consultation_date": "{date_str}",
        "classification": "{category_label}",
        "summary": "상담 경위/배경 + 고객 유형·성향 해석을 담은 2~4문장 (어떤 계기로 상담에 왔고, 어떤 태도로 접근하는 고객인지)"
    }},

    "section2_customer_needs": {{
        "main_concerns": ["핵심 고민 1 — 표면적 호소와 그 이면의 니즈를 함께 (1~2문)", "핵심 고민 2 (1~2문)"],
        "desired_outcome": "고객이 원하는 최종 결과 + 그 이유/배경까지 2~3문장",
        "mentioned_procedures": ["고객이 언급한 시술명 (가능하면 언급 맥락 한 줄 포함)"],
        "urgency": "급함/보통/여유 + 그렇게 판단한 근거 (내원 시기·발화 기반, 없으면 '미정')"
    }},

    "section3_consultation_context": {{
        "current_state": "현재 상태 + 과거 시술 이력과 현재 니즈의 연관성 해석 2~4문장 (언급 없으면 '정보 없음')",
        "key_questions": ["고객이 질문한 내용 + 그 질문이 드러내는 관심/우려 (1~2문)", "질문 2"],
        "emotional_tone": "고객의 태도/감정 상태 + 그 근거가 된 발화/신호 2~3문장 (불안, 적극적, 탐색적 등을 단정하지 말고 근거와 함께)"{''',
        "voice_analysis": {{
            "speech_patterns": "말투 분석 — 망설임/확신 정도와 주요 예시 1~2문",
            "intonation": "억양 분석 — 상승/하강 패턴과 의미 1~2문",
            "speech_speed": "말 속도 — 전체 속도와 변동 특이사항 1문",
            "silence_patterns": "침묵 분석 — 주요 침묵 발생 상황과 해석 1~2문",
            "voice_cta": "음성 CTA 레벨 + 텍스트 CTA와 비교 1~2문",
            "emotional_summary": "음성에서 감지된 감정 변화 요약 (텍스트만으로는 알 수 없는 인사이트) 2~3문"
        }}''' if voice_emotion_analysis else ''}
    }},

    "section4_next_steps": {{
        "recommended_topics": ["다음 상담에서 다뤄야 할 주제 + 왜 중요한지/어떻게 접근할지 (1~2문)", "주제 2"],
        "additional_checks": ["추가 확인 필요사항 + 이유 (1문)"],
        "notes": "상담실장이 유의할 응대 전략·특이사항 2~3문 (없으면 null)"
    }}
}}

중요 규칙:
- 상담에서 언급·관찰된 내용에 근거할 것. 사실 창작 금지. 단, 발화에 기반한 합리적 해석은 "~로 보임/추정됨"으로 명시하여 적극 제공
- 각 항목은 단순 요약이 아니라 분석·해석을 담아 충실하게 (항목당 2~4문장). 단, 의미 없는 미사여구로 늘리지 말 것
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
