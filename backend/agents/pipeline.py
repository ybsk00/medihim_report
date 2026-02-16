import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

from services.supabase_client import get_supabase
from agents.translator import translate_to_korean
from agents.cta_analyzer import analyze_cta
from agents.intent_extractor import extract_intent
from agents.classifier import classify_consultation
from agents.validator import validate_classification
from agents.rag_agent import search_relevant_faq
from agents.report_writer import write_report
from agents.report_reviewer import review_report

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
        # Step 1: 번역 (일본어 → 한국어)
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 1: Translation start")
        start = time.time()
        translated_text = await translate_to_korean(original_text)
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 1: Translation done ({duration}ms)")

        await _log_agent(consultation_id, "translator", None, {"translated_text": translated_text[:200]}, duration, "success")
        await _update_consultation(consultation_id, {"translated_text": translated_text})

        # ========================================
        # Step 2: 화자 분리 + CTA 분석
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 2: CTA analysis start")
        start = time.time()
        cta_result = await analyze_cta(original_text, translated_text)
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 2: CTA done ({duration}ms)")

        await _log_agent(consultation_id, "cta_analyzer", None, cta_result, duration, "success")
        await _update_consultation(consultation_id, {
            "speaker_segments": cta_result.get("speaker_segments"),
            "customer_utterances": cta_result.get("customer_utterances", ""),
            "cta_level": cta_result.get("cta_level", "cool"),
            "cta_signals": cta_result.get("cta_signals"),
        })

        # ========================================
        # Step 3: 의도 추출
        # ========================================
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 3: Intent extraction start")
        start = time.time()
        intent = await extract_intent(translated_text)
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
        # Step 6~ : 리포트 생성 (분류 확정 후)
        # ========================================
        await _generate_report(consultation_id, original_text, translated_text, intent, final_classification, customer_name)

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

    # 수동 분류 업데이트
    await _update_consultation(consultation_id, {
        "classification": classification,
        "is_manually_classified": True,
        "status": "report_generating",
    })

    try:
        await _generate_report(consultation_id, original_text, translated_text, intent, classification, customer_name)
    except Exception as e:
        await _update_consultation(consultation_id, {
            "status": "report_failed",
            "error_message": str(e),
        })


async def _generate_report(
    consultation_id: str,
    original_text: str,
    translated_text: str,
    intent: dict,
    classification: str,
    customer_name: str,
):
    db = get_supabase()

    await _update_consultation(consultation_id, {"status": "report_generating"})

    # ========================================
    # Step 6: RAG 검색
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

    # ========================================
    # Step 7: 리포트 작성 (최대 3회 시도)
    # ========================================
    report_data = None
    review_count = 0
    max_retries = 3

    for attempt in range(max_retries):
        # 리포트 생성
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 7: Report write attempt {attempt + 1}/{max_retries}")
        start = time.time()
        report_data = await write_report(
            original_text, translated_text, intent, classification, rag_results, customer_name,
        )
        duration = int((time.time() - start) * 1000)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 7: Report written ({duration}ms)")
        await _log_agent(consultation_id, "report_writer", None, {"attempt": attempt + 1}, duration, "success")

        # 리포트 검토
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 7: Report review attempt {attempt + 1}")
        start = time.time()
        review = await review_report(report_data, rag_results)
        duration = int((time.time() - start) * 1000)
        review_count = attempt + 1
        passed = review.get("passed", False)
        logger.info(f"[Pipeline:{consultation_id[:8]}] Step 7: Review done ({duration}ms, passed={passed})")
        await _log_agent(consultation_id, "report_reviewer", None, review, duration, "success")

        if passed:
            break

        # 3회차가 아니면 피드백으로 재생성 시도
        if attempt < max_retries - 1:
            feedback = review.get('feedback', '')
            logger.info(f"[Pipeline:{consultation_id[:8]}] Review failed, feedback: {feedback[:100]}")
            original_text_with_feedback = (
                original_text + f"\n\n[レビューフィードバック: {feedback}]"
            )
            original_text = original_text_with_feedback

    # ========================================
    # Step 8: DB에 리포트 저장
    # ========================================
    access_token = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=30)

    db.table("reports").insert(
        {
            "consultation_id": consultation_id,
            "report_data": report_data,
            "rag_context": rag_results,
            "review_count": review_count,
            "review_passed": review_count <= max_retries,
            "access_token": access_token,
            "access_expires_at": expires_at.isoformat(),
            "status": "draft",
        }
    ).execute()

    await _update_consultation(consultation_id, {"status": "report_ready"})


async def regenerate_report(report_id: str, direction: str):
    """관리자 피드백 기반 리포트 재생성"""
    db = get_supabase()

    # 1. 기존 리포트 + 상담 데이터 조회
    report_result = db.table("reports").select("*").eq("id", report_id).single().execute()
    report = report_result.data
    if not report:
        raise ValueError(f"Report {report_id} not found")

    consultation_id = report["consultation_id"]
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

    await _update_consultation(consultation_id, {"status": "report_generating"})

    try:
        # 2. RAG 재검색: 기존 키워드 + 관리자 방향에서 추출한 키워드
        existing_keywords = intent.get("keywords", []) if intent else []
        direction_keywords = direction.split()
        combined_keywords = list(set(existing_keywords + direction_keywords))

        start = time.time()
        rag_results = await search_relevant_faq(combined_keywords, classification)
        duration = int((time.time() - start) * 1000)

        await _log_agent(
            consultation_id, "rag_agent_regen",
            {"keywords": combined_keywords, "direction": direction},
            {"result_count": len(rag_results)},
            duration, "success",
        )

        # 3. 리포트 작성 + 검토 루프 (최대 3회)
        report_data = None
        review_count = 0
        max_retries = 3

        for attempt in range(max_retries):
            start = time.time()
            report_data = await write_report(
                original_text, translated_text, intent, classification,
                rag_results, customer_name,
                admin_direction=direction,
            )
            duration = int((time.time() - start) * 1000)
            await _log_agent(
                consultation_id, "report_writer_regen",
                None, {"attempt": attempt + 1, "direction": direction[:100]},
                duration, "success",
            )

            start = time.time()
            review = await review_report(report_data, rag_results)
            duration = int((time.time() - start) * 1000)
            review_count = attempt + 1
            await _log_agent(
                consultation_id, "report_reviewer_regen",
                None, review, duration, "success",
            )

            if review.get("passed", False):
                break

            if attempt < max_retries - 1:
                original_text = (
                    original_text + f"\n\n[レビューフィードバック: {review.get('feedback', '')}]"
                )

        # 4. 기존 리포트 레코드 업데이트 (overwrite)
        access_token = report.get("access_token") or uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)

        db.table("reports").update({
            "report_data": report_data,
            "report_data_ko": None,  # 한국어 캐시 초기화
            "rag_context": rag_results,
            "review_count": review_count,
            "review_passed": review_count <= max_retries,
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
