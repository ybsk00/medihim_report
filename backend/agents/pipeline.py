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
# [R1-R3 비활성화] 28일 R4 테스트 후 활성화 예정
# from agents.r1_doctor_writer import write_r1_report
# from agents.r2_director_writer import write_r2_report
# from agents.r3_executive_writer import write_r3_report

logger = logging.getLogger(__name__)


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


async def run_pipeline(consultation_id: str):
    db = get_supabase()

    # 상담 데이터 조회
    result = db.table("consultations").select("*").eq("id", consultation_id).single().execute()
    consultation = result.data

    original_text = consultation["original_text"]
    customer_name = consultation["customer_name"]

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

        # 미분류면 파이프라인 중단
        if final_classification == "unclassified":
            await _update_consultation(consultation_id, {"status": "classification_pending"})
            return

        # ========================================
        # Step 6~ : R1→R2→R3→R4 리포트 일괄 생성
        # ========================================
        await _generate_all_reports(
            consultation_id, cleaned_text, text_for_analysis,
            intent, final_classification, customer_name,
            cta_level=cta_level,
            cta_signals=cta_result.get("cta_signals"),
            speaker_segments=cta_result.get("speaker_segments"),
            input_lang=input_lang,
        )

    except Exception as e:
        logger.error(f"[Pipeline:{consultation_id[:8]}] FAILED: {str(e)}", exc_info=True)
        await _update_consultation(consultation_id, {
            "status": "report_failed",
            "error_message": str(e),
        })
        await _log_agent(consultation_id, "pipeline", None, None, 0, "failed", str(e))


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
        "report_data_ko": None,
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
):
    """R1→R2→R3→R4 순차 생성. R1 실패 시 R4만 생성 (graceful degradation)."""
    db = get_supabase()

    await _update_consultation(consultation_id, {"status": "report_generating"})

    # ========================================
    # Step 6: RAG 검색 (1회, R1~R4 공유)
    # ========================================
    logger.info(f"[Pipeline:{consultation_id[:8]}] Step 6: RAG search start")
    start = time.time()
    keywords = intent.get("keywords", [])
    rag_results = await search_relevant_faq(keywords, classification)
    duration = int((time.time() - start) * 1000)
    logger.info(f"[Pipeline:{consultation_id[:8]}] Step 6: RAG done ({duration}ms, {len(rag_results)} results)")

    await _log_agent(
        consultation_id, "rag_agent", {"keywords": keywords, "category": classification},
        {"result_count": len(rag_results)}, duration, "success",
    )

    # [R1-R3 비활성화] 28일 R4 테스트 후 활성화 예정
    # r1_data = None
    # r2_data = None
    #
    # # Step 7-R1: 의사 리포트 (한국어)
    # try:
    #     r1_data = await _write_and_review(
    #         consultation_id, "r1", write_r1_report,
    #         {"original_text": original_text, "translated_text": translated_text,
    #          "intent_extraction": intent, "classification": classification,
    #          "rag_results": rag_results, "customer_name": customer_name,
    #          "cta_level": cta_level, "cta_signals": cta_signals,
    #          "speaker_segments": speaker_segments, "input_lang": input_lang},
    #         rag_results)
    #     logger.info(f"[Pipeline:{consultation_id[:8]}] R1 complete")
    # except Exception as e:
    #     logger.error(f"[Pipeline:{consultation_id[:8]}] R1 failed: {str(e)}", exc_info=True)
    #     await _log_agent(consultation_id, "r1_writer", None, None, 0, "failed", str(e))
    #
    # # Step 7-R2: 상담실장 리포트 (한국어, R1 참조)
    # if r1_data:
    #     try:
    #         r2_data = await _write_and_review(
    #             consultation_id, "r2", write_r2_report,
    #             {"r1_report_data": r1_data, "intent_extraction": intent,
    #              "classification": classification, "rag_results": rag_results,
    #              "customer_name": customer_name, "cta_level": cta_level,
    #              "cta_signals": cta_signals},
    #             rag_results)
    #         logger.info(f"[Pipeline:{consultation_id[:8]}] R2 complete")
    #     except Exception as e:
    #         logger.error(f"[Pipeline:{consultation_id[:8]}] R2 failed: {str(e)}", exc_info=True)
    #         await _log_agent(consultation_id, "r2_writer", None, None, 0, "failed", str(e))
    # else:
    #     logger.warning(f"[Pipeline:{consultation_id[:8]}] R2 skipped (R1 failed)")
    #
    # # Step 7-R3: 경영진 리포트 (한국어, R1+R2 참조)
    # if r1_data and r2_data:
    #     try:
    #         await _write_and_review(
    #             consultation_id, "r3", write_r3_report,
    #             {"r1_report_data": r1_data, "r2_report_data": r2_data,
    #              "intent_extraction": intent, "classification": classification,
    #              "customer_name": customer_name, "cta_level": cta_level,
    #              "cta_signals": cta_signals},
    #             rag_results)
    #         logger.info(f"[Pipeline:{consultation_id[:8]}] R3 complete")
    #     except Exception as e:
    #         logger.error(f"[Pipeline:{consultation_id[:8]}] R3 failed: {str(e)}", exc_info=True)
    #         await _log_agent(consultation_id, "r3_writer", None, None, 0, "failed", str(e))
    # else:
    #     logger.warning(f"[Pipeline:{consultation_id[:8]}] R3 skipped (R1 or R2 failed)")

    # ========================================
    # Step 7-R4: 고객 리포트 (일본어, 기존 로직)
    # ========================================
    # 병원 정보 추출 (intent_extraction에서)
    hospital_mentions = intent.get("hospital_mentions", []) if intent else []

    try:
        # R4는 기존 write_report 사용 (일본어)
        # 피드백 루프를 위해 original_text 복사
        r4_original = original_text
        r4_report_data = None
        r4_review_count = 0
        max_retries = 3

        for attempt in range(max_retries):
            logger.info(f"[Pipeline:{consultation_id[:8]}] R4 write attempt {attempt + 1}/{max_retries}")
            start = time.time()
            r4_report_data = await write_report(
                r4_original, translated_text, intent, classification,
                rag_results, customer_name,
                input_lang=input_lang,
                hospital_mentions=hospital_mentions,
            )
            duration = int((time.time() - start) * 1000)
            logger.info(f"[Pipeline:{consultation_id[:8]}] R4 written ({duration}ms)")
            await _log_agent(consultation_id, "r4_writer", None, {"attempt": attempt + 1}, duration, "success")

            # R4 검토 (기존 일본어 검토)
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
                r4_original = r4_original + f"\n\n[レビューフィードバック: {feedback}]"

        await _save_report(consultation_id, "r4", r4_report_data, rag_results, r4_review_count, max_retries)
        logger.info(f"[Pipeline:{consultation_id[:8]}] R4 complete")

    except Exception as e:
        logger.error(f"[Pipeline:{consultation_id[:8]}] R4 failed: {str(e)}", exc_info=True)
        await _log_agent(consultation_id, "r4_writer", None, None, 0, "failed", str(e))

    # ========================================
    # Step 8: consultation status 업데이트
    # ========================================
    await _update_consultation(consultation_id, {"status": "report_ready"})


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
        # [R1-R3 비활성화] 28일 R4 테스트 후 활성화 예정
        # if report_type == "r1":
        #     await _write_and_review(...)
        # elif report_type == "r2":
        #     ...
        # elif report_type == "r3":
        #     ...
        # else:  # r4

        if True:  # R4 only (R1-R3 비활성화 상태)
            # 병원 정보 추출 (intent_extraction에서)
            regen_hospital_mentions = intent.get("hospital_mentions", []) if intent else []

            r4_original = original_text
            r4_report_data = None
            r4_review_count = 0
            max_retries = 3

            for attempt in range(max_retries):
                start = time.time()
                r4_report_data = await write_report(
                    r4_original, translated_text, intent, classification,
                    rag_results, customer_name,
                    admin_direction=direction,
                    input_lang=input_lang,
                    hospital_mentions=regen_hospital_mentions,
                )
                duration = int((time.time() - start) * 1000)
                await _log_agent(
                    consultation_id, "r4_writer_regen",
                    None, {"attempt": attempt + 1, "direction": direction[:100]},
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
                    r4_original = r4_original + f"\n\n[レビューフィードバック: {review.get('feedback', '')}]"

            # 기존 리포트 레코드 업데이트
            access_token = report.get("access_token") or uuid.uuid4().hex
            now = datetime.now(timezone.utc)
            expires_at = now + timedelta(days=30)

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
