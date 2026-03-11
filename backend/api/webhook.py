"""이뽀 앱 → AI 서버 Webhook 수신 API (v1.1 스펙)"""

import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Request

from api.auth_webhook import verify_webhook, verify_api_key
from models.schemas import IppeoConsultationRequest
from services.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


async def _download_stt_text(url: str) -> str:
    """S3 Presigned URL에서 STT 텍스트 파일 다운로드 (10분 유효)"""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


async def _process_consultation(data: dict):
    """백그라운드: 상담 등록 → 파이프라인 실행 (R1 + R4 자동 생성)"""
    db = get_supabase()
    consultation_id = None

    try:
        # 1. STT 텍스트 확보
        stt_text = data.get("stt_text", "")

        # stt_file_url이 있으면 다운로드 (S3 Presigned URL)
        if data.get("stt_file_url"):
            stt_text = await _download_stt_text(data["stt_file_url"])

        if not stt_text or not stt_text.strip():
            raise ValueError("STT 텍스트가 비어있습니다.")

        logger.info(f"[Webhook] STT received: {len(stt_text)} chars")

        # 2. 기존 상담 확인 (같은 고객명 + 회차)
        consultation_round = data.get("consultation_round", 1)

        # 3. 상담 등록
        record = {
            "customer_name": data["customer_name"],
            "customer_email": data.get("customer_email", ""),
            "original_text": stt_text,
            "hospital_name": data.get("hospital_name", ""),
            "doctor_name": data.get("doctor_name", ""),
            "concern_area": data.get("concern_area", ""),
            "consultation_round": consultation_round,
            "status": "processing",
        }

        result = db.table("consultations").insert(record).execute()
        consultation_id = result.data[0]["id"]
        logger.info(f"[Webhook] Created consultation: {consultation_id}")

        # 4. 파이프라인 자동 실행 (R1 + R4)
        from agents.pipeline import run_pipeline
        await run_pipeline(consultation_id)

    except Exception as e:
        logger.error(f"[Webhook] Processing failed: {e}", exc_info=True)
        if consultation_id:
            db = get_supabase()
            db.table("consultations").update({
                "status": "report_failed",
                "error_message": str(e),
            }).eq("id", consultation_id).execute()


@router.post("/consultation")
async def receive_consultation(
    data: IppeoConsultationRequest,
    background_tasks: BackgroundTasks,
    _auth=Depends(verify_webhook),
):
    """
    이뽀 앱에서 상담 STT 데이터 수신.
    백그라운드에서 R1(의사용) + R4(환자용) 리포트 자동 생성.
    """
    logger.info(
        f"[Webhook] Received: customer={data.customer_name}, round={data.consultation_round}"
    )

    # 백그라운드에서 처리 (즉시 200 응답)
    background_tasks.add_task(_process_consultation, data.model_dump())

    return {
        "success": True,
        "message": "상담 데이터 수신 완료. 리포트 자동 생성을 시작합니다.",
    }


@router.get("/status/{consultation_id}")
async def get_report_status(
    consultation_id: str,
    _auth=Depends(verify_api_key),
):
    """상담 처리 상태 + embed URL 조회 (이뽀 앱에서 폴링)"""
    db = get_supabase()

    consultation = (
        db.table("consultations")
        .select("id, status, customer_name, error_message")
        .eq("id", consultation_id)
        .single()
        .execute()
    )

    if not consultation.data:
        return {"success": False, "error": "NOT_FOUND"}

    c = consultation.data
    result = {
        "success": True,
        "status": c["status"],
        "customer_name": c["customer_name"],
    }

    # 리포트 생성 완료 시 embed URL 포함
    if c["status"] in ("report_ready", "report_approved", "report_sent"):
        reports = (
            db.table("reports")
            .select("report_type, access_token")
            .eq("consultation_id", c["id"])
            .execute()
        )
        from config import FRONTEND_URL
        embed_base = f"{FRONTEND_URL}/embed"

        for r in reports.data or []:
            token = r["access_token"]
            if r["report_type"] == "r4":
                result["patient_report"] = {
                    "report_token": token,
                    "embed_url": {
                        "ja": f"{embed_base}/{token}?lang=ja",
                        "ko": f"{embed_base}/{token}?lang=ko",
                    }
                }
            elif r["report_type"] == "r1":
                result["doctor_report"] = {
                    "report_token": token,
                    "embed_url": {
                        "ko": f"{embed_base}/{token}?lang=ko",
                    }
                }

    if c.get("error_message"):
        result["error_message"] = c["error_message"]

    return result
