import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

from services.supabase_client import get_supabase
from agents.text_refiner import preprocess_stt_dialog, refine_stt_text
from agents.translator import translate_to_korean
from agents.cta_analyzer import analyze_cta
from agents.intent_extractor import extract_intent
from agents.classifier import classify_consultation
from agents.validator import validate_classification
from agents.rag_agent import search_relevant_faq
from agents.report_writer import write_report
from agents.report_reviewer import review_report
from agents.r1_cs_writer import write_r1_report
from agents.r2_director_writer import write_r2_report
from agents.r3_director_writer import write_r3_report
from services.ippeo_callback import notify_report_ready

logger = logging.getLogger(__name__)


def _build_fallback_r4(customer_name: str, classification: str) -> dict:
    """R4 환자용 폴백 리포트 (일본어, 10섹션 구조 유지)"""
    category_ja = "皮膚科" if classification == "dermatology" else "美容整形"
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y年%m月%d日")

    return {
        "title": f"{customer_name}様 ご相談リポート",
        "date": today,
        "section1_key_summary": {
            "points": [
                "今回のご相談内容だけでは、詳細なリポートを作成するための情報が不足しておりました。",
                "ご不便をおかけし申し訳ございません。",
            ]
        },
        "section2_cause_analysis": {
            "intro": "ご相談内容の情報量が限られていたため、原因・背景の詳細な分析が難しい状況です。",
            "causes": [
                "相談時間が短かった、または具体的な症状・ご希望の共有が少なかった可能性があります。",
            ],
            "conclusion": "次回のご相談では、気になる部位やご希望を具体的にお伝えいただくと、より的確な分析が可能です。",
        },
        "section3_recommendation": {
            "primary": {
                "label": "次回ご相談のおすすめ",
                "items": [
                    "気になる部位の写真をご準備ください。",
                    f"{category_ja}に関する具体的なお悩みを事前にメモしておくとスムーズです。",
                    "過去の施術歴や服用中のお薬がある場合はお知らせください。",
                ],
            },
            "secondary": {"label": "", "items": []},
            "goal": "追加のご相談をいただければ、詳細なリポートをお届けいたします。",
        },
        "section4_recovery": {
            "timeline": [],
            "note": "具体的な施術プランが決まった段階で、回復スケジュールをご案内いたします。",
        },
        "section5_scar_info": {
            "points": ["施術内容が確定した際に、傷跡に関する詳しいご案内をいたします。"],
        },
        "section6_precautions": {
            "points": ["次回のご相談までに特別な注意事項はございません。"],
        },
        "section7_risks": {
            "points": ["施術プランが具体化した段階で、リスクについて詳しくご説明いたします。"],
        },
        "section8_cost_estimate": {
            "items": ["ご相談内容が不足しているため、費用目安のご案内は控えさせていただきます。"],
            "note": "次回ご相談時に具体的な費用範囲をお伝えいたします。",
        },
        "section9_visit_date": {
            "date": None,
            "note": "追加のご相談後にご来院スケジュールをご提案いたします。",
        },
        "section10_ippeo_message": {
            "paragraphs": [
                f"{customer_name}様、今回は十分な情報をお届けできず申し訳ございません。",
                "追加のご相談をいただければ、より詳しい分析結果とご提案をリポートとしてお届けいたします。",
                "お気軽にもう一度ご相談ください。IPPEOがしっかりサポートいたします。",
            ],
            "final_summary": "次回のご相談で、より充実したリポートをお届けいたします。お待ちしております。",
        },
    }


def _build_fallback_r4_ko(customer_name: str, classification: str) -> dict:
    """R4 환자용 폴백 리포트 (한국어 번역본, 10섹션 구조 유지)"""
    category_ko = "피부과" if classification == "dermatology" else "미용성형"
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y년 %m월 %d일")

    return {
        "title": f"{customer_name}님 상담 리포트",
        "date": today,
        "section1_key_summary": {
            "points": [
                "이번 상담 내용만으로는 상세한 리포트를 작성하기 위한 정보가 부족하였습니다.",
                "불편을 드려 죄송합니다.",
            ]
        },
        "section2_cause_analysis": {
            "intro": "상담 내용의 정보량이 제한적이어서 원인·배경의 상세한 분석이 어려운 상황입니다.",
            "causes": [
                "상담 시간이 짧았거나, 구체적인 증상·희망 사항의 공유가 적었을 가능성이 있습니다.",
            ],
            "conclusion": "다음 상담에서는 신경 쓰이는 부위나 희망 사항을 구체적으로 전달해 주시면 보다 정확한 분석이 가능합니다.",
        },
        "section3_recommendation": {
            "primary": {
                "label": "다음 상담 시 권장사항",
                "items": [
                    "신경 쓰이는 부위의 사진을 준비해 주세요.",
                    f"{category_ko}에 관한 구체적인 고민을 사전에 메모해 두시면 원활합니다.",
                    "과거 시술 이력이나 복용 중인 약물이 있으시면 알려주세요.",
                ],
            },
            "secondary": {"label": "", "items": []},
            "goal": "추가 상담을 해주시면 상세한 리포트를 제공해 드리겠습니다.",
        },
        "section4_recovery": {
            "timeline": [],
            "note": "구체적인 시술 계획이 정해진 단계에서 회복 스케줄을 안내해 드리겠습니다.",
        },
        "section5_scar_info": {
            "points": ["시술 내용이 확정되면 흉터에 관한 자세한 안내를 드리겠습니다."],
        },
        "section6_precautions": {
            "points": ["다음 상담까지 특별한 주의사항은 없습니다."],
        },
        "section7_risks": {
            "points": ["시술 계획이 구체화된 단계에서 리스크에 대해 자세히 설명드리겠습니다."],
        },
        "section8_cost_estimate": {
            "items": ["상담 내용이 부족하여 비용 안내를 드리기 어렵습니다."],
            "note": "다음 상담 시 구체적인 비용 범위를 안내해 드리겠습니다.",
        },
        "section9_visit_date": {
            "date": None,
            "note": "추가 상담 후 내원 스케줄을 제안해 드리겠습니다.",
        },
        "section10_ippeo_message": {
            "paragraphs": [
                f"{customer_name}님, 이번에는 충분한 정보를 전달드리지 못해 죄송합니다.",
                "추가 상담을 해주시면 보다 자세한 분석 결과와 제안을 리포트로 전달드리겠습니다.",
                "편하게 다시 한번 상담해 주세요. IPPEO가 확실히 서포트하겠습니다.",
            ],
            "final_summary": "다음 상담에서 보다 충실한 리포트를 전달드리겠습니다. 기다리고 있겠습니다.",
        },
    }


def _build_fallback_r1(customer_name: str, classification: str) -> dict:
    """R1 사전상담 폴백 리포트 (한국어, 4섹션)"""
    category_ko = "피부과" if classification == "dermatology" else "성형외과"
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")

    return {
        "title": f"{customer_name} 고객 — {category_ko} 사전상담 리포트",
        "date": today,
        "section1_customer_profile": {
            "name": customer_name,
            "consultation_date": today,
            "classification": category_ko,
            "summary": "상담 정보가 부족하여 상세 리포트 생성에 실패했습니다.",
        },
        "section2_customer_needs": {
            "main_concerns": ["상담 내용 부족으로 파악 불가"],
            "desired_outcome": "추가 상담이 필요합니다.",
            "mentioned_procedures": [],
            "urgency": "미정",
        },
        "section3_consultation_context": {
            "current_state": "정보 없음",
            "key_questions": [],
            "emotional_tone": "파악 불가",
        },
        "section4_next_steps": {
            "recommended_topics": [
                "구체적인 고민 부위와 증상 확인",
                "과거 시술/수술 이력 확인",
                "희망하는 결과와 기대치 파악",
            ],
            "additional_checks": ["알레르기 이력", "현재 복용 약물"],
            "notes": "추가 상담 시 구체적인 정보 확보가 필요합니다.",
        },
    }


def _build_fallback_r2(customer_name: str, classification: str) -> dict:
    """R2 의사용 폴백 리포트 (한국어, 5섹션)"""
    category_ko = "피부과" if classification == "dermatology" else "성형외과"
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")

    return {
        "title": f"{customer_name} 환자 — {category_ko} 의사용 상담리포트",
        "date": today,
        "section1_patient_summary": {
            "name": customer_name,
            "classification": category_ko,
            "consultation_date": today,
            "chief_complaint": "상담 정보가 부족하여 주소 파악이 어렵습니다.",
            "consultation_history": None,
        },
        "section2_medical_assessment": {
            "current_condition": "정보 부족으로 평가 불가.",
            "relevant_history": None,
            "key_findings": ["추가 상담을 통한 정보 확보가 필요합니다."],
        },
        "section3_treatment_options": {
            "recommended_procedures": [],
            "alternative_approaches": [],
            "contraindications": [],
        },
        "section4_clinical_considerations": {
            "risk_factors": ["정보 부족으로 위험 요소 평가 불가"],
            "expected_outcome": "구체적인 상담 후 평가 가능합니다.",
            "recovery_overview": "시술 계획 확정 후 안내 가능합니다.",
        },
        "section5_pre_consultation_notes": {
            "recommended_tests": [],
            "patient_readiness": "미분석",
            "doctor_notes": "추가 상담을 통해 구체적인 증상과 희망 사항을 확인해주세요.",
        },
    }


def _build_fallback_r3(customer_name: str, classification: str) -> dict:
    """R3 상담실장용 폴백 리포트 (한국어, 6섹션 — 가격/옵션/고려사항)"""
    category_ko = "피부과" if classification == "dermatology" else "성형외과"
    today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")

    return {
        "title": f"{customer_name} 환자 — {category_ko} 상담실장 리포트",
        "date": today,
        "section1_consultation_summary": {
            "name": customer_name,
            "classification": category_ko,
            "consultation_date": today,
            "round_summary": "상담 정보가 부족하여 상세 리포트 생성에 실패했습니다.",
            "cta_level": "—",
        },
        "section2_procedure_plan": {
            "primary_procedures": [],
            "additional_options": [],
        },
        "section3_cost_estimate": {
            "items": [],
            "package_options": [],
            "total_estimate": "정보 부족으로 견적 산출 불가",
            "note": "추가 상담 후 비용 견적을 안내해 드리겠습니다.",
        },
        "section4_scheduling": {
            "preferred_date": "미정",
            "treatment_timeline": "시술 계획 확정 후 안내 가능합니다.",
            "follow_up_plan": [],
        },
        "section5_considerations": {
            "patient_concerns": ["상담 내용 부족으로 파악 불가"],
            "negotiation_points": [],
            "risk_communication": "시술 계획이 구체화된 후 리스크를 전달해주세요.",
        },
        "section6_action_items": {
            "before_visit": ["추가 상담 일정 조율"],
            "during_consultation": ["구체적인 고민과 예산 범위 확인"],
            "after_consultation": ["리포트 재생성 요청"],
        },
    }



async def _log_agent(
    consultation_id: str,
    agent_name: str,
    input_data: dict | None,
    output_data: dict | None,
    duration_ms: int,
    status: str,
    error_message: str | None = None,
):
    db = get_supabase()
    db.table("agent_logs").insert(
        {
            "consultation_id": consultation_id,
            "agent_name": agent_name,
            "input_data": input_data,
            "output_data": output_data,
            "duration_ms": duration_ms,
            "status": status,
            "error_message": error_message,
        }
    ).execute()


async def _update_consultation(consultation_id: str, data: dict):
    db = get_supabase()
    db.table("consultations").update(data).eq("id", consultation_id).execute()


async def _save_fallback_by_round(
    consultation_id: str, customer_name: str, classification: str, consultation_round: int,
):
    """회차별 폴백 리포트 저장"""
    if consultation_round == 1:
        fb = _build_fallback_r1(customer_name, classification)
        await _save_report(consultation_id, "r1", fb, [], 0, 3)
    elif consultation_round == 2:
        fb = _build_fallback_r2(customer_name, classification)
        await _save_report(consultation_id, "r2", fb, [], 0, 3)
    else:
        fb_r4 = _build_fallback_r4(customer_name, classification)
        fb_r4_ko = _build_fallback_r4_ko(customer_name, classification)
        await _save_report(consultation_id, "r4", fb_r4, [], 0, 3, report_data_ko=fb_r4_ko)
        fb_r3 = _build_fallback_r3(customer_name, classification)
        await _save_report(consultation_id, "r3", fb_r3, [], 0, 3)


async def _find_previous_round_report(
    ippeo_consultation_id: str, target_round: int, report_type: str,
) -> dict | None:
    """같은 ippeo_consultation_id의 이전 회차 리포트 조회"""
    if not ippeo_consultation_id:
        return None
    db = get_supabase()
    prev_consultation = (
        db.table("consultations")
        .select("id")
        .eq("ippeo_consultation_id", ippeo_consultation_id)
        .eq("consultation_round", target_round)
        .limit(1)
        .execute()
    )
    if not prev_consultation.data:
        return None
    prev_report = (
        db.table("reports")
        .select("report_data")
        .eq("consultation_id", prev_consultation.data[0]["id"])
        .eq("report_type", report_type)
        .limit(1)
        .execute()
    )
    return prev_report.data[0]["report_data"] if prev_report.data else None


async def run_pipeline(consultation_id: str):
    db = get_supabase()

    # 상담 데이터 조회
    result = db.table("consultations").select("*").eq("id", consultation_id).single().execute()
    consultation = result.data

    original_text = consultation["original_text"]
    customer_name = consultation["customer_name"]
    consultation_round = consultation.get("consultation_round") or 1
    ippeo_consultation_id = consultation.get("ippeo_consultation_id") or ""

    try:
        # ========================================
        # Step 0: STT 텍스트 전처리 (규칙 기반, LLM 불필요)
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 0: Preprocessing start")
        start = time.time()
        preprocess_result = preprocess_stt_dialog(original_text)
        duration = int((time.time() - start) * 1000)

        has_labels = preprocess_result["has_speaker_labels"]
        pre_segments = preprocess_result.get("speaker_segments")
        pre_customer = preprocess_result.get("customer_utterances")
        cleaned_text = preprocess_result["cleaned_text"]
        logger.info(
            f"[Pipeline:{consultation_id[:8]}] Step 0: Preprocess done ({duration}ms, "
            f"labels={has_labels}, {len(original_text)}→{len(cleaned_text)} chars)"
        )
        await _log_agent(
            consultation_id, "preprocessor",
            {"original_len": len(original_text)},
            {"cleaned_len": len(cleaned_text), "has_labels": has_labels},
            duration, "success",
        )

        # ========================================
        # Step 1: 언어 감지 + 번역 (한국어면 스킵)
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 1: Translation start")
        start = time.time()
        translated_text, input_lang = await translate_to_korean(cleaned_text)
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 1: Translation done ({duration}ms, lang={input_lang})")

        await _log_agent(consultation_id, "translator", {"input_lang": input_lang}, {"translated_text": translated_text[:200]}, duration, "success")
        await _update_consultation(consultation_id, {
            "translated_text": translated_text,
            "input_language": input_lang,
        })

        # ========================================
        # Step 1.5: STT 텍스트 정제 (LLM 기반, 15000자 이하만)
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 1.5: STT refinement start")
        start = time.time()
        refined_text = await refine_stt_text(translated_text)
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 1.5: Refinement done ({duration}ms)")
        await _log_agent(
            consultation_id, "text_refiner",
            {"input_len": len(translated_text)},
            {"output_len": len(refined_text), "skipped": refined_text == translated_text},
            duration, "success",
        )

        # 정제된 텍스트를 이후 단계에서 사용
        text_for_analysis = refined_text

        # ========================================
        # Step 2: 화자 분리 + CTA 분석
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 2: CTA analysis start")
        start = time.time()
        cta_result = await analyze_cta(
            cleaned_text, text_for_analysis,
            input_lang=input_lang,
            pre_extracted_segments=pre_segments,
            pre_customer_utterances=pre_customer,
        )
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 2: CTA done ({duration}ms)")

        await _log_agent(consultation_id, "cta_analyzer", None, cta_result, duration, "success")
        # CTA 레벨 소문자 정규화
        raw_cta = cta_result.get("cta_level", "cool")
        cta_level = raw_cta.lower() if isinstance(raw_cta, str) else "cool"
        if cta_level not in ("hot", "warm", "cool"):
            cta_level = "cool"
        await _update_consultation(consultation_id, {
            "speaker_segments": cta_result.get("speaker_segments"),
            "customer_utterances": cta_result.get("customer_utterances", ""),
            "cta_level": cta_level,
            "cta_signals": cta_result.get("cta_signals"),
        })

        # ========================================
        # Step 3: 의도 추출 (정제된 한국어 텍스트 사용)
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 3: Intent extraction start")
        start = time.time()
        intent = await extract_intent(text_for_analysis)
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 3: Intent done ({duration}ms)")

        await _log_agent(consultation_id, "intent_extractor", None, intent, duration, "success")
        await _update_consultation(consultation_id, {"intent_extraction": intent})

        # ========================================
        # Step 4: 분류
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 4: Classification start")
        start = time.time()
        classification_result = await classify_consultation(translated_text, intent)
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 4: Classification done ({duration}ms)")

        await _log_agent(consultation_id, "classifier", None, classification_result, duration, "success")

        # ========================================
        # Step 5: 검증
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 5: Validation start")
        start = time.time()
        validation = await validate_classification(classification_result, translated_text, intent)
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 5: Validation done ({duration}ms)")

        final_classification = validation.get("classification", "unclassified")
        confidence = validation.get("confidence", 0.0)
        reason = validation.get("reason", "")

        await _log_agent(consultation_id, "validator", None, validation, duration, "success")
        await _update_consultation(consultation_id, {
            "classification": final_classification,
            "classification_confidence": confidence,
            "classification_reason": reason,
        })

        # 미분류면 폴백 리포트 생성 후 콜백 전송 (회차별 분기)
        if final_classification == "unclassified":
            logger.info(f"[Pipeline:{consultation_id[:8]}] Unclassified (round={consultation_round}) → generating fallback reports")
            await _save_fallback_by_round(consultation_id, customer_name, "plastic_surgery", consultation_round)
            logger.info(f"[Pipeline:{consultation_id[:8]}] Unclassified fallback saved (round={consultation_round})")
            await _update_consultation(consultation_id, {
                "status": "report_ready",
                "error_message": "[폴백] 상담 내용이 부족하여 분류 불가 — 폴백 리포트 생성",
            })
            try:
                await notify_report_ready(consultation_id)
                logger.info(f"[Pipeline:{consultation_id[:8]}] Unclassified callback sent")
            except Exception as cb_err:
                logger.warning(f"[Pipeline:{consultation_id[:8]}] Unclassified callback failed: {cb_err}")
            return

        # ========================================
        # Step 6~ : 회차별 리포트 생성 (round=1→R1, round=2→R2, round>=3→R3+R4)
        # ========================================
        await _generate_all_reports(
            consultation_id, cleaned_text, text_for_analysis,
            intent, final_classification, customer_name,
            cta_level=cta_level,
            cta_signals=cta_result.get("cta_signals"),
            speaker_segments=cta_result.get("speaker_segments"),
            input_lang=input_lang,
            consultation_round=consultation_round,
            ippeo_consultation_id=ippeo_consultation_id,
        )

    except Exception as e:
        logger.error(f"[Pipeline:{consultation_id[:8]}] FAILED (round={consultation_round}), saving fallback reports: {str(e)}", exc_info=True)
        await _log_agent(consultation_id, "pipeline", None, None, 0, "failed", str(e))

        # 폴백 리포트 저장 (회차별 분기)
        fallback_classification = consultation.get("classification") or "plastic_surgery"
        try:
            await _save_fallback_by_round(consultation_id, customer_name, fallback_classification, consultation_round)
            logger.info(f"[Pipeline:{consultation_id[:8]}] Fallback saved (round={consultation_round})")
            await _update_consultation(consultation_id, {
                "status": "report_ready",
                "error_message": f"[폴백] {str(e)}",
            })
            # 폴백이라도 이뽀에 콜백 전송
            try:
                await notify_report_ready(consultation_id)
            except Exception as cb_err:
                logger.warning(f"[Pipeline:{consultation_id[:8]}] Fallback callback failed: {cb_err}")
        except Exception as fallback_err:
            logger.error(f"[Pipeline:{consultation_id[:8]}] Fallback save failed: {fallback_err}")
            await _update_consultation(consultation_id, {
                "status": "report_failed",
                "error_message": str(e),
            })


async def resume_pipeline(consultation_id: str, classification: str):
    """관리자 수동 분류 후 파이프라인 재개"""
    db = get_supabase()

    result = db.table("consultations").select("*").eq("id", consultation_id).single().execute()
    consultation = result.data

    original_text = consultation["original_text"]
    translated_text = consultation["translated_text"]
    intent = consultation["intent_extraction"]
    if isinstance(intent, list):
        intent = intent[0] if intent else {}
    customer_name = consultation["customer_name"]
    input_lang = consultation.get("input_language", "ja")
    cta_level = consultation.get("cta_level")
    cta_signals = consultation.get("cta_signals")
    speaker_segments = consultation.get("speaker_segments")
    consultation_round = consultation.get("consultation_round") or 1
    ippeo_consultation_id_val = consultation.get("ippeo_consultation_id") or ""

    # 수동 분류 업데이트
    await _update_consultation(consultation_id, {
        "classification": classification,
        "is_manually_classified": True,
        "status": "report_generating",
    })

    try:
        await _generate_all_reports(
            consultation_id, original_text, translated_text,
            intent, classification, customer_name,
            cta_level=cta_level,
            cta_signals=cta_signals,
            speaker_segments=speaker_segments,
            input_lang=input_lang,
            consultation_round=consultation_round,
            ippeo_consultation_id=ippeo_consultation_id_val,
        )
    except Exception as e:
        await _update_consultation(consultation_id, {
            "status": "report_failed",
            "error_message": str(e),
        })


async def _save_report(
    consultation_id: str,
    report_type: str,
    report_data: dict,
    rag_results: list[dict],
    review_count: int,
    max_retries: int,
    report_data_ko: dict | None = None,
):
    """리포트 저장 (upsert: consultation_id + report_type 기준)"""
    db = get_supabase()

    access_token = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)

    # 기존 리포트가 있는지 확인
    existing = (
        db.table("reports")
        .select("id")
        .eq("consultation_id", consultation_id)
        .eq("report_type", report_type)
        .execute()
    )

    record = {
        "report_data": report_data,
        "report_data_ko": report_data_ko,
        "rag_context": rag_results,
        "review_count": review_count,
        "review_passed": review_count <= max_retries,
        "status": "draft",
    }

    if existing.data:
        # 기존 레코드 업데이트
        db.table("reports").update(record).eq("id", existing.data[0]["id"]).execute()
        logger.info(f"[Pipeline] Updated existing {report_type.upper()} report for {consultation_id[:8]}")
    else:
        # 신규 생성
        record.update({
            "consultation_id": consultation_id,
            "report_type": report_type,
            "access_token": access_token,
            "access_expires_at": expires_at.isoformat(),
        })
        db.table("reports").insert(record).execute()
        logger.info(f"[Pipeline] Created new {report_type.upper()} report for {consultation_id[:8]}")


async def _write_and_review(
    consultation_id: str,
    report_type: str,
    write_fn,
    write_kwargs: dict,
    rag_results: list[dict],
    max_retries: int = 3,
) -> dict | None:
    """리포트 작성 + 검토 루프 (공통 헬퍼)"""
    report_data = None
    review_count = 0

    for attempt in range(max_retries):
        logger.info(f"[Pipeline:{consultation_id[:8]}] {report_type.upper()} write attempt {attempt + 1}/{max_retries}")
        start = time.time()
        report_data = await write_fn(**write_kwargs)
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] {report_type.upper()} written ({duration}ms)")
        await _log_agent(consultation_id, f"{report_type}_writer", None, {"attempt": attempt + 1}, duration, "success")

        # 리포트 검토
        logger.info(f"[Pipeline:{consultation_id[:8]}] {report_type.upper()} review attempt {attempt + 1}")
        start = time.time()
        review = await review_report(report_data, rag_results, report_type=report_type)
        duration = int((time.time() - start) * 1000)
        review_count = attempt + 1
        passed = review.get("passed", False)
        logger.info(f"[Pipeline:{consultation_id[:8]}] {report_type.upper()} review done ({duration}ms, passed={passed})")
        await _log_agent(consultation_id, f"{report_type}_reviewer", None, review, duration, "success")

        if passed:
            break

        if attempt < max_retries - 1:
            feedback = review.get("feedback", "")
            logger.info(f"[Pipeline:{consultation_id[:8]}] {report_type.upper()} review failed, feedback: {feedback[:100]}")
            # 피드백을 write_kwargs에 반영
            if "admin_direction" in write_kwargs:
                existing = write_kwargs["admin_direction"] or ""
                write_kwargs["admin_direction"] = f"{existing}\n[리뷰 피드백: {feedback}]".strip()
            else:
                write_kwargs["admin_direction"] = f"[리뷰 피드백: {feedback}]"

    # DB 저장
    await _save_report(consultation_id, report_type, report_data, rag_results, review_count, max_retries)
    return report_data


async def _generate_all_reports(
    consultation_id: str,
    original_text: str,
    translated_text: str,
    intent: dict,
    classification: str,
    customer_name: str,
    cta_level: str | None = None,
    cta_signals: list | None = None,
    speaker_segments: list | None = None,
    input_lang: str = "ja",
    consultation_round: int = 3,
    ippeo_consultation_id: str = "",
):
    """회차별 리포트 생성. round=1→R1, round=2→R2, round>=3→R3+R4."""
    db = get_supabase()

    await _update_consultation(consultation_id, {"status": "report_generating"})

    # ========================================
    # Step 6: RAG 검색 (1회, 모든 회차 공유)
    # ========================================
    logger.info(f"[Pipeline:{consultation_id[:8]}] Step 6: RAG search start (round={consultation_round})")
    start = time.time()
    keywords = intent.get("keywords", [])
    rag_results = await search_relevant_faq(keywords, classification)
    duration = int((time.time() - start) * 1000)
    logger.info(f"[Pipeline:{consultation_id[:8]}] Step 6: RAG done ({duration}ms, {len(rag_results)} results)")

    await _log_agent(
        consultation_id, "rag_agent", {"keywords": keywords, "category": classification},
        {"result_count": len(rag_results)}, duration, "success",
    )

    # ========================================
    # 회차별 분기
    # ========================================
    if consultation_round == 1:
        await _generate_round1_r1(
            consultation_id, original_text, translated_text,
            intent, classification, customer_name, rag_results, input_lang,
        )
    elif consultation_round == 2:
        await _generate_round2_r2(
            consultation_id, original_text, translated_text,
            intent, classification, customer_name, rag_results,
            cta_level, cta_signals, ippeo_consultation_id, input_lang,
        )
    else:
        await _generate_round3_r3_r4(
            consultation_id, original_text, translated_text,
            intent, classification, customer_name, rag_results,
            cta_level, cta_signals, speaker_segments, input_lang,
        )

    # ========================================
    # Step 8: consultation status 업데이트 + 이뽀 콜백
    # ========================================
    await _update_consultation(consultation_id, {"status": "report_ready"})

    # 이뽀 앱에 report_ready 콜백 전송
    try:
        await notify_report_ready(consultation_id)
    except Exception as cb_err:
        logger.warning(f"[Pipeline:{consultation_id[:8]}] Callback failed (non-blocking): {cb_err}")


async def _generate_round1_r1(
    consultation_id, original_text, translated_text,
    intent, classification, customer_name, rag_results, input_lang,
):
    """1차 상담 → R1 사전상담 리포트 생성"""
    try:
        await _write_and_review(
            consultation_id, "r1", write_r1_report,
            {"original_text": original_text, "translated_text": translated_text,
             "intent_extraction": intent, "classification": classification,
             "customer_name": customer_name, "input_lang": input_lang},
            rag_results)
        logger.info(f"[Pipeline:{consultation_id[:8]}] R1 complete")
    except Exception as e:
        logger.error(f"[Pipeline:{consultation_id[:8]}] R1 failed, saving fallback: {str(e)}", exc_info=True)
        await _log_agent(consultation_id, "r1_writer", None, None, 0, "failed", str(e))
        fallback_r1 = _build_fallback_r1(customer_name, classification)
        await _save_report(consultation_id, "r1", fallback_r1, rag_results, 0, 3)
        logger.info(f"[Pipeline:{consultation_id[:8]}] R1 fallback saved")


async def _generate_round2_r2(
    consultation_id, original_text, translated_text,
    intent, classification, customer_name, rag_results,
    cta_level, cta_signals, ippeo_consultation_id, input_lang,
):
    """2차 상담 → R2 의사용 리포트 생성 (1차 R1 데이터 참조)"""
    # 이전 회차(1차) R1 리포트 조회
    r1_data = await _find_previous_round_report(ippeo_consultation_id, 1, "r1")
    if r1_data:
        logger.info(f"[Pipeline:{consultation_id[:8]}] R2: Found previous R1 data")
    else:
        logger.info(f"[Pipeline:{consultation_id[:8]}] R2: No previous R1 data, generating independently")

    try:
        await _write_and_review(
            consultation_id, "r2", write_r2_report,
            {"original_text": original_text, "translated_text": translated_text,
             "intent_extraction": intent, "classification": classification,
             "rag_results": rag_results, "customer_name": customer_name,
             "cta_level": cta_level, "cta_signals": cta_signals,
             "r1_report_data": r1_data, "input_lang": input_lang},
            rag_results)
        logger.info(f"[Pipeline:{consultation_id[:8]}] R2 complete")
    except Exception as e:
        logger.error(f"[Pipeline:{consultation_id[:8]}] R2 failed, saving fallback: {str(e)}", exc_info=True)
        await _log_agent(consultation_id, "r2_writer", None, None, 0, "failed", str(e))
        fallback_r2 = _build_fallback_r2(customer_name, classification)
        await _save_report(consultation_id, "r2", fallback_r2, rag_results, 0, 3)
        logger.info(f"[Pipeline:{consultation_id[:8]}] R2 fallback saved")


async def _generate_round3_r3_r4(
    consultation_id, original_text, translated_text,
    intent, classification, customer_name, rag_results,
    cta_level, cta_signals, speaker_segments, input_lang,
):
    """3차 상담 → R3 상담실장 + R4 소비자 리포트 생성 (기존 로직)"""
    db = get_supabase()

    # R3: 상담실장 리포트 (가격/견적/고려사항)
    try:
        await _write_and_review(
            consultation_id, "r3", write_r3_report,
            {"original_text": original_text, "translated_text": translated_text,
             "intent_extraction": intent, "classification": classification,
             "rag_results": rag_results, "customer_name": customer_name,
             "cta_level": cta_level, "cta_signals": cta_signals,
             "speaker_segments": speaker_segments, "input_lang": input_lang},
            rag_results)
        logger.info(f"[Pipeline:{consultation_id[:8]}] R3 complete")
    except Exception as e:
        logger.error(f"[Pipeline:{consultation_id[:8]}] R3 failed, saving fallback: {str(e)}", exc_info=True)
        await _log_agent(consultation_id, "r3_writer", None, None, 0, "failed", str(e))
        fallback_r3 = _build_fallback_r3(customer_name, classification)
        await _save_report(consultation_id, "r3", fallback_r3, rag_results, 0, 3)
        logger.info(f"[Pipeline:{consultation_id[:8]}] R3 fallback saved")

    # R4: 소비자 리포트 (일본어) — 기존 로직 그대로
    hospital_mentions = intent.get("hospital_mentions", []) if intent else []

    try:
        r4_report_data = None
        r4_review_count = 0
        max_retries = 3
        accumulated_feedback = None

        for attempt in range(max_retries):
            logger.info(f"[Pipeline:{consultation_id[:8]}] R4 write attempt {attempt + 1}/{max_retries}")
            start = time.time()
            r4_report_data = await write_report(
                original_text, translated_text, intent, classification,
                rag_results, customer_name,
                admin_direction=accumulated_feedback,
                input_lang=input_lang,
                hospital_mentions=hospital_mentions,
            )
            duration = int((time.time() - start) * 1000)
            logger.info(f"[Pipeline:{consultation_id[:8]}] R4 written ({duration}ms)")
            await _log_agent(consultation_id, "r4_writer", None, {"attempt": attempt + 1}, duration, "success")

            start = time.time()
            review = await review_report(r4_report_data, rag_results, report_type="r4")
            duration = int((time.time() - start) * 1000)
            r4_review_count = attempt + 1
            passed = review.get("passed", False)
            logger.info(f"[Pipeline:{consultation_id[:8]}] R4 review done ({duration}ms, passed={passed})")
            await _log_agent(consultation_id, "r4_reviewer", None, review, duration, "success")

            if passed:
                break

            if attempt < max_retries - 1:
                feedback = review.get("feedback", "")
                if accumulated_feedback:
                    accumulated_feedback = f"{accumulated_feedback}\n[レビューフィードバック: {feedback}]"
                else:
                    accumulated_feedback = f"[レビューフィードバック: {feedback}]"

        await _save_report(consultation_id, "r4", r4_report_data, rag_results, r4_review_count, max_retries)
        logger.info(f"[Pipeline:{consultation_id[:8]}] R4 complete")

        # R4 한국어 번역 자동 생성
        try:
            from agents.korean_translator import translate_report_to_korean
            logger.info(f"[Pipeline:{consultation_id[:8]}] R4 Korean translation start")
            start = time.time()
            r4_data_ko = await translate_report_to_korean(r4_report_data)
            duration = int((time.time() - start) * 1000)
            logger.info(f"[Pipeline:{consultation_id[:8]}] R4 Korean translation done ({duration}ms)")

            existing_r4 = (
                db.table("reports")
                .select("id")
                .eq("consultation_id", consultation_id)
                .eq("report_type", "r4")
                .execute()
            )
            if existing_r4.data:
                db.table("reports").update({"report_data_ko": r4_data_ko}).eq("id", existing_r4.data[0]["id"]).execute()
                logger.info(f"[Pipeline:{consultation_id[:8]}] R4 report_data_ko saved")
        except Exception as ko_err:
            logger.warning(f"[Pipeline:{consultation_id[:8]}] R4 Korean translation failed (non-blocking): {ko_err}")

    except Exception as e:
        logger.error(f"[Pipeline:{consultation_id[:8]}] R4 failed, saving fallback: {str(e)}", exc_info=True)
        await _log_agent(consultation_id, "r4_writer", None, None, 0, "failed", str(e))
        fallback_r4 = _build_fallback_r4(customer_name, classification)
        fallback_r4_ko = _build_fallback_r4_ko(customer_name, classification)
        await _save_report(consultation_id, "r4", fallback_r4, rag_results, 0, 3, report_data_ko=fallback_r4_ko)
        logger.info(f"[Pipeline:{consultation_id[:8]}] R4 fallback saved")



async def regenerate_report(report_id: str, direction: str):
    """관리자 피드백 기반 리포트 재생성 (리포트 타입별 적절한 writer 호출)"""
    db = get_supabase()

    # 1. 기존 리포트 + 상담 데이터 조회
    report_result = db.table("reports").select("*").eq("id", report_id).single().execute()
    report = report_result.data
    if not report:
        raise ValueError(f"Report {report_id} not found")

    consultation_id = report["consultation_id"]
    report_type = report.get("report_type", "r4")

    consultation_result = db.table("consultations").select("*").eq("id", consultation_id).single().execute()
    consultation = consultation_result.data
    if not consultation:
        raise ValueError(f"Consultation {consultation_id} not found")

    original_text = consultation["original_text"]
    translated_text = consultation["translated_text"]
    intent = consultation["intent_extraction"]
    if isinstance(intent, list):
        intent = intent[0] if intent else {}
    classification = consultation["classification"]
    customer_name = consultation["customer_name"]
    input_lang = consultation.get("input_language", "ja")
    cta_level = consultation.get("cta_level")
    cta_signals = consultation.get("cta_signals")
    speaker_segments = consultation.get("speaker_segments")

    await _update_consultation(consultation_id, {"status": "report_generating"})

    try:
        # 2. RAG 재검색
        existing_keywords = intent.get("keywords", []) if intent else []
        direction_keywords = direction.split()
        combined_keywords = list(set(existing_keywords + direction_keywords))

        start = time.time()
        rag_results = await search_relevant_faq(combined_keywords, classification)
        duration = int((time.time() - start) * 1000)

        await _log_agent(
            consultation_id, "rag_agent_regen",
            {"keywords": combined_keywords, "direction": direction, "report_type": report_type},
            {"result_count": len(rag_results)},
            duration, "success",
        )

        # 3. 리포트 타입별 재생성
        # 기존 리포트 레코드 업데이트용 공통 변수
        access_token = report.get("access_token") or uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)

        if report_type == "r3":
            # R3 상담실장 리포트 재생성
            regen_data = await _write_and_review(
                consultation_id, "r3", write_r3_report,
                {"original_text": original_text, "translated_text": translated_text,
                 "intent_extraction": intent, "classification": classification,
                 "rag_results": rag_results, "customer_name": customer_name,
                 "cta_level": cta_level, "cta_signals": cta_signals,
                 "speaker_segments": speaker_segments,
                 "admin_direction": direction, "input_lang": input_lang},
                rag_results)

            db.table("reports").update({
                "report_data": regen_data,
                "rag_context": rag_results,
                "review_count": 1,
                "review_passed": True,
                "access_token": access_token,
                "access_expires_at": expires_at.isoformat(),
                "status": "draft",
            }).eq("id", report_id).execute()

        else:  # R4 (기본)
            regen_hospital_mentions = intent.get("hospital_mentions", []) if intent else []

            r4_report_data = None
            r4_review_count = 0
            max_retries = 3
            current_direction = direction

            for attempt in range(max_retries):
                start = time.time()
                r4_report_data = await write_report(
                    original_text, translated_text, intent, classification,
                    rag_results, customer_name,
                    admin_direction=current_direction,
                    input_lang=input_lang,
                    hospital_mentions=regen_hospital_mentions,
                )
                duration = int((time.time() - start) * 1000)
                await _log_agent(
                    consultation_id, "r4_writer_regen",
                    None, {"attempt": attempt + 1, "direction": current_direction[:100]},
                    duration, "success",
                )

                start = time.time()
                review = await review_report(r4_report_data, rag_results, report_type="r4")
                duration = int((time.time() - start) * 1000)
                r4_review_count = attempt + 1
                await _log_agent(consultation_id, "r4_reviewer_regen", None, review, duration, "success")

                if review.get("passed", False):
                    break

                if attempt < max_retries - 1:
                    feedback = review.get("feedback", "")
                    current_direction = f"{direction}\n[レビューフィードバック: {feedback}]"

            db.table("reports").update({
                "report_data": r4_report_data,
                "report_data_ko": None,
                "rag_context": rag_results,
                "review_count": r4_review_count,
                "review_passed": r4_review_count <= max_retries,
                "access_token": access_token,
                "access_expires_at": expires_at.isoformat(),
                "status": "draft",
            }).eq("id", report_id).execute()

        await _update_consultation(consultation_id, {"status": "report_ready"})

    except Exception as e:
        await _update_consultation(consultation_id, {
            "status": "report_failed",
            "error_message": f"재생성 실패: {str(e)}",
        })
        db.table("reports").update({
            "status": "rejected",
            "review_notes": f"재생성 실패: {str(e)}",
        }).eq("id", report_id).execute()
        await _log_agent(consultation_id, "pipeline_regen", None, None, 0, "failed", str(e))
