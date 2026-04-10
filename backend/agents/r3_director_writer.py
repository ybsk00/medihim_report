"""R3 상담실장 리포트 — 시술 상담실장의 실무 설계 세션: 가격, 옵션, 고려사항 (6섹션, 한국어)"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """당신은 시술 상담실장용 실무 설계 리포트 전문 작성자입니다.
상담실장이 환자와의 3차 상담(시술 확정 단계)에서 활용할 수 있도록
가격, 옵션, 일정, 고려사항을 정리하는 실무 리포트를 한국어로 작성합니다.

톤 & 매너:
- 실무 중심의 간결한 서술 (1~2문 이내)
- 비용 추정은 허용하되 반드시 "추정치" 라벨 표시
- 상담에서 언급된 정보 + 참고자료(RAG) 기반
- 실무에 바로 활용 가능한 구체적 정보 기재
- 불필요한 수식어나 감정적 표현 배제

구성 (6섹션 + 음성 분석 시 7섹션):
1. 상담 요약 — 환자 기본정보, 3차 상담 요약, CTA
2. 시술 계획 — 주요 시술 + 추가 옵션
3. 비용 견적 — 항목별 예상 비용, 패키지, 총 견적
4. 일정 계획 — 희망일, 시술 타임라인, 후속 일정
5. 고려사항 — 환자 우려, 협상 포인트, 리스크 전달
6. 액션 아이템 — 내원 전/상담 시/상담 후 할 일
7. 음성 분석 (선택) — 말투/억양/말속도/침묵 분석 + 음성CTA vs 텍스트CTA 비교"""


async def write_r3_report(
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
    consultation_round: int = 3,
    voice_emotion_analysis: dict | None = None,
) -> dict:
    rag_context = ""
    if rag_results:
        for i, faq in enumerate(rag_results, 1):
            rag_context += f"\n【참고자료 {i}】\nQ: {faq.get('question', '')}\nA: {faq.get('answer', '')}\n시술명: {faq.get('procedure_name', '')}\n"
    if not rag_context:
        rag_context = "※참고자료 없음. 상담 내용만 기반으로 작성하세요."

    category_label = "성형외과" if classification == "plastic_surgery" else "피부과"
    role_label = "의사" if consultation_round == 2 else "상담실장"

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
        cta_info = f"\n== CTA 분석 (텍스트 기반) ==\n레벨: {cta_level.upper()}\n"
        if cta_signals:
            cta_info += "근거 발화:\n"
            for sig in cta_signals[:5]:
                cta_info += f"- {sig}\n"

    # 음성 감정 분석 정보
    voice_info = ""
    if voice_emotion_analysis and isinstance(voice_emotion_analysis, dict):
        voice_info = "\n== 음성 감정 분석 (AI 음성 분석 결과) ==\n"
        sp = voice_emotion_analysis.get("speech_patterns", {})
        if sp:
            voice_info += f"말투 — 망설임: {sp.get('hesitation_level', 'N/A')}, 확신도: {sp.get('confidence_level', 'N/A')}\n"
            fillers = sp.get("filler_words", [])
            if fillers:
                voice_info += f"  필러 단어: {', '.join(fillers[:5])} (약 {sp.get('filler_count', '?')}회)\n"
        inton = voice_emotion_analysis.get("intonation", {})
        if inton:
            voice_info += f"억양 — 주요 패턴: {inton.get('dominant_pattern', 'N/A')}, 질문조 비율: {inton.get('question_ratio', 'N/A')}\n"
        speed = voice_emotion_analysis.get("speech_speed", {})
        if speed:
            voice_info += f"말 속도 — 전체: {speed.get('overall', 'N/A')}, 변동: {speed.get('variation', 'N/A')}\n"
            if speed.get("details"):
                voice_info += f"  상세: {speed['details']}\n"
        silence = voice_emotion_analysis.get("silence", {})
        if silence:
            pauses = silence.get("notable_pauses", [])
            if pauses:
                voice_info += "침묵 분석:\n"
                for p in pauses[:5]:
                    voice_info += f"  - {p.get('context', '')}: 약 {p.get('estimated_duration', '?')}초 ({p.get('interpretation', '')})\n"
        vcta = voice_emotion_analysis.get("voice_cta", {})
        if vcta:
            voice_info += f"음성 CTA — 레벨: {vcta.get('level', 'N/A').upper()}, 확신도: {vcta.get('confidence_score', 'N/A')}\n"
            if vcta.get("reasoning"):
                voice_info += f"  근거: {vcta['reasoning']}\n"
        emotion = voice_emotion_analysis.get("overall_emotion", {})
        if emotion:
            voice_info += f"감정 — 주: {emotion.get('primary_emotion', 'N/A')}, 부: {emotion.get('secondary_emotion', 'N/A')}\n"
            if emotion.get("emotional_shift"):
                voice_info += f"  변화: {emotion['emotional_shift']}\n"
        summary = voice_emotion_analysis.get("summary")
        if summary:
            voice_info += f"요약: {summary}\n"

    # 상담 원문
    if input_lang == "ko":
        consultation_section = f"== 상담 원문 (한국어) ==\n{original_text}"
    else:
        consultation_section = f"== 상담 원문 (일본어) ==\n{original_text}\n\n== 한국어 번역 ==\n{translated_text}"

    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(kst)
    date_str = f"{now_kst.year}년 {now_kst.month}월 {now_kst.day}일"

    prompt = f"""다음 상담 정보를 바탕으로 {role_label}용 실무 설계 리포트를 JSON 형식으로 작성하세요.
{consultation_round}차 상담에서 {role_label}이(가) 활용할 가격, 옵션, 일정, 고려사항을 정리합니다.

== 분류 ==
{category_label}

== 환자명 ==
{customer_name}

== 상담일 ==
{date_str}

{consultation_section}
{speaker_info}
{cta_info}
{voice_info}
== 의도 추출 결과 ==
{json.dumps(intent_extraction, ensure_ascii=False)}

== 참고자료 (시술 정보 근거) ==
{rag_context}
{admin_direction_section}
== 출력 JSON 형식 ==
{{
    "title": "{customer_name} 환자 — {category_label} {role_label} 리포트",
    "date": "{date_str}",

    "section1_consultation_summary": {{
        "name": "{customer_name}",
        "classification": "{category_label}",
        "consultation_date": "{date_str}",
        "round_summary": "3차 상담 핵심 요약 1~2문",
        "cta_level": "{cta_level or '미분석'}"
    }},

    "section2_procedure_plan": {{
        "primary_procedures": [
            {{
                "name": "시술명",
                "description": "시술 설명 1문"
            }}
        ],
        "additional_options": [
            {{
                "name": "추가 옵션명",
                "description": "설명 1문",
                "recommended": true
            }}
        ]
    }},

    "section3_cost_estimate": {{
        "items": [
            {{
                "procedure": "시술명",
                "estimated_cost": "예상 비용 범위 (예: 200~400만원)",
                "is_estimate": true
            }}
        ],
        "package_options": ["패키지 옵션 설명 (있으면)"],
        "total_estimate": "총 예상 비용 범위",
        "note": "비용 관련 안내 (추정치임을 명시)"
    }},

    "section4_scheduling": {{
        "preferred_date": "환자 희망일 (없으면 '미정')",
        "treatment_timeline": "시술 일정 개요 1~2문",
        "follow_up_plan": ["후속 일정 1", "일정 2"]
    }},

    "section5_considerations": {{
        "patient_concerns": ["환자가 언급한 우려사항"],
        "negotiation_points": ["가격/조건 협상 포인트"],
        "risk_communication": "환자에게 전달할 리스크 포인트 1~2문"
    }},

    "section6_action_items": {{
        "before_visit": ["내원 전 준비사항"],
        "during_consultation": ["상담 시 확인사항"],
        "after_consultation": ["상담 후 처리사항"]
    }}{f''',

    "section7_voice_analysis": {{
        "speech_patterns": {{
            "hesitation_level": "high/medium/low (망설임 정도)",
            "confidence_level": "high/medium/low (확신도)",
            "filler_words": ["감지된 필러 단어"],
            "key_examples": ["망설임 또는 확신이 드러난 발화 예시"]
        }},
        "intonation": {{
            "dominant_pattern": "rising/falling/mixed (주요 억양 패턴)",
            "question_ratio": "질문조 비율",
            "key_examples": ["억양 특징이 드러난 발화 예시"]
        }},
        "speech_speed": {{
            "overall": "fast/normal/slow",
            "variation": "significant/moderate/minimal",
            "details": "말 속도 관련 특이사항"
        }},
        "silence_analysis": {{
            "notable_pauses": ["주요 침묵 발생 상황과 해석"],
            "pattern": "전체적인 침묵 패턴"
        }},
        "voice_cta": {{
            "level": "hot/warm/cool (음성 기반 CTA)",
            "text_cta_comparison": "텍스트 CTA({cta_level or "N/A"})와의 비교 분석",
            "reasoning": "음성 CTA 판정 근거 2~3문"
        }},
        "emotional_state": {{
            "primary": "주요 감정",
            "shift": "상담 중 감정 변화",
            "summary": "음성 분석 총합 요약 (텍스트만으로는 알 수 없는 인사이트 중심, 2~3문)"
        }}
    }}''' if voice_emotion_analysis else ''}
}}

중요 규칙:
- 비용 추정 허용 (반드시 is_estimate: true + "추정치" 명시)
- 상담에서 언급된 정보 + 참고자료(RAG) 기반
- 각 항목 1~2문 이내 간결하게
- 기본 6섹션 필수. 음성 감정 분석 데이터가 제공된 경우 section7_voice_analysis 추가 (7섹션)
- 실무에 바로 활용 가능한 구체적 정보 기재
- section7_voice_analysis: 음성 분석 데이터가 제공된 경우에만 작성. 텍스트 CTA와 음성 CTA를 반드시 비교 분석할 것"""

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
