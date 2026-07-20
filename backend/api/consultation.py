import asyncio
import logging
import os
import tempfile
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile
from typing import Optional
from models.schemas import ConsultationCreate, ConsultationBulkCreate, ClassifyRequest, CTAUpdateRequest, GenerateReportsRequest, ConsultationUpdateRequest
from services.supabase_client import get_supabase
from services.task_queue import enqueue_pipeline_task
from agents.pipeline import run_pipeline, resume_pipeline

logger = logging.getLogger(__name__)

ALLOWED_AUDIO_EXTENSIONS = {".m4a", ".wav", ".mp3", ".aac", ".flac", ".ogg"}


async def _run_pipelines_parallel(consultation_ids: list[str], concurrency: int = 5):
    """파이프라인을 동시성 제한하여 병렬 실행"""
    semaphore = asyncio.Semaphore(concurrency)

    async def _run_one(cid: str):
        async with semaphore:
            await run_pipeline(cid)

    await asyncio.gather(*[_run_one(cid) for cid in consultation_ids], return_exceptions=True)

router = APIRouter(prefix="/api/consultations", tags=["consultations"])


@router.post("")
async def create_consultation(data: ConsultationCreate):
    db = get_supabase()

    result = db.table("consultations").insert(
        {
            "customer_id": data.customer_id,
            "customer_name": data.customer_name,
            "customer_email": data.customer_email,
            "customer_line_id": data.customer_line_id,
            "original_text": data.original_text,
            "status": "registered",
        }
    ).execute()

    consultation = result.data[0]

    return {"id": consultation["id"], "status": "registered"}


@router.post("/bulk")
async def create_consultations_bulk(data: ConsultationBulkCreate):
    if len(data.consultations) > 100:
        raise HTTPException(status_code=400, detail="최대 100건까지 일괄 등록 가능합니다")

    if len(data.consultations) == 0:
        raise HTTPException(status_code=400, detail="등록할 상담 데이터가 없습니다")

    db = get_supabase()
    rows = [
        {
            "customer_id": c.customer_id,
            "customer_name": c.customer_name,
            "customer_email": c.customer_email,
            "customer_line_id": c.customer_line_id,
            "original_text": c.original_text,
            "status": "registered",
        }
        for c in data.consultations
    ]

    result = db.table("consultations").insert(rows).execute()

    created_ids = [consultation["id"] for consultation in result.data]

    return {"created": len(created_ids), "ids": created_ids}


@router.post("/generate-reports")
async def generate_reports(data: GenerateReportsRequest, background_tasks: BackgroundTasks):
    """선택한 상담건에 대해 AI 리포트 생성 파이프라인 실행"""
    if len(data.consultation_ids) == 0:
        raise HTTPException(status_code=400, detail="생성할 상담 ID가 없습니다")
    if len(data.consultation_ids) > 50:
        raise HTTPException(status_code=400, detail="최대 50건까지 일괄 생성 가능합니다")

    db = get_supabase()

    result = db.table("consultations").select("id, status").in_("id", data.consultation_ids).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="해당 상담을 찾을 수 없습니다")

    found_ids = {row["id"] for row in result.data}
    missing = set(data.consultation_ids) - found_ids
    if missing:
        raise HTTPException(status_code=404, detail=f"찾을 수 없는 상담 ID: {list(missing)}")

    valid_statuses = {"registered", "report_failed", "processing", "report_generating"}
    triggered_ids = []
    skipped = []

    for row in result.data:
        if row["status"] in valid_statuses:
            db.table("consultations").update({"status": "processing"}).eq("id", row["id"]).execute()
            triggered_ids.append(row["id"])
        else:
            skipped.append({
                "id": row["id"],
                "status": row["status"],
                "reason": "이미 처리 중이거나 완료된 상담입니다",
            })

    # Cloud Tasks로 건별 실행 (동시 처리는 큐 설정 max-concurrent-dispatches로 제한).
    # 발행 실패/로컬 개발 시에만 기존 BackgroundTasks 병렬 실행으로 폴백.
    if triggered_ids:
        fallback_ids = []
        for cid in triggered_ids:
            if not await enqueue_pipeline_task(cid):
                fallback_ids.append(cid)
        if fallback_ids:
            background_tasks.add_task(_run_pipelines_parallel, fallback_ids, 5)

    return {
        "triggered": len(triggered_ids),
        "triggered_ids": triggered_ids,
        "skipped": skipped,
    }


@router.get("")
async def list_consultations(
    classification: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    db = get_supabase()
    query = db.table("consultations").select("*", count="exact")

    if classification:
        query = query.eq("classification", classification)
    if status:
        query = query.eq("status", status)

    offset = (page - 1) * page_size
    query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)

    result = query.execute()
    return {
        "data": result.data,
        "total": result.count,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{consultation_id}")
async def get_consultation(consultation_id: str):
    db = get_supabase()
    result = db.table("consultations").select("*").eq("id", consultation_id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Consultation not found")

    return result.data


@router.put("/{consultation_id}")
async def update_consultation(consultation_id: str, data: ConsultationUpdateRequest):
    """고객 정보 수정 (이름, 이메일, LINE ID, 플랫폼 ID)"""
    db = get_supabase()

    update_data = {}
    if data.customer_name is not None:
        update_data["customer_name"] = data.customer_name
    if data.customer_email is not None:
        update_data["customer_email"] = data.customer_email
    if data.customer_line_id is not None:
        update_data["customer_line_id"] = data.customer_line_id
    if data.customer_id is not None:
        update_data["customer_id"] = data.customer_id

    if not update_data:
        raise HTTPException(status_code=400, detail="수정할 데이터가 없습니다")

    result = db.table("consultations").update(update_data).eq("id", consultation_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Consultation not found")

    return result.data[0]


@router.put("/{consultation_id}/classify")
async def classify_consultation(
    consultation_id: str,
    data: ClassifyRequest,
    background_tasks: BackgroundTasks,
):
    db = get_supabase()

    # 상담 존재 확인
    consultation = db.table("consultations").select("status").eq("id", consultation_id).single().execute()
    if not consultation.data:
        raise HTTPException(status_code=404, detail="Consultation not found")

    if consultation.data["status"] != "classification_pending":
        raise HTTPException(status_code=400, detail="Consultation is not pending classification")

    # 수동 분류 후 파이프라인 재개
    background_tasks.add_task(resume_pipeline, consultation_id, data.classification)

    return {"id": consultation_id, "status": "report_generating"}


@router.post("/delete")
async def delete_consultations_post(data: GenerateReportsRequest):
    """선택한 상담 삭제 (POST로 body 전달)"""
    if not data.consultation_ids:
        raise HTTPException(status_code=400, detail="삭제할 상담 ID가 없습니다")

    db = get_supabase()

    # agent_logs 먼저 삭제 (FK)
    for cid in data.consultation_ids:
        db.table("agent_logs").delete().eq("consultation_id", cid).execute()

    # reports 삭제 (CASCADE로 자동 처리되지만 명시적으로)
    for cid in data.consultation_ids:
        db.table("reports").delete().eq("consultation_id", cid).execute()

    # consultations 삭제
    result = db.table("consultations").delete().in_("id", data.consultation_ids).execute()

    return {"deleted": len(result.data), "ids": [r["id"] for r in result.data]}


@router.put("/{consultation_id}/cta")
async def update_cta(consultation_id: str, data: CTAUpdateRequest):
    db = get_supabase()

    result = db.table("consultations").update(
        {"cta_level": data.cta_level}
    ).eq("id", consultation_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Consultation not found")

    return {"id": consultation_id, "cta_level": data.cta_level}


@router.post("/upload-audio")
async def upload_audio_consultation(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    customer_name: str = Form(...),
    customer_email: str = Form(""),
    customer_line_id: str = Form(""),
    customer_id: str = Form(""),
):
    """음성 파일 업로드 → STT + 감정 분석 → 상담 등록.

    지원 포맷: M4A, WAV, MP3, AAC, FLAC, OGG
    """
    # 확장자 검증
    _, ext = os.path.splitext(audio_file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 오디오 포맷입니다: {ext}. 지원: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
        )

    # 임시 파일에 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await audio_file.read()
        tmp.write(content)
        tmp_path = tmp.name

    logger.info(f"[UploadAudio] File saved: {tmp_path} ({len(content)} bytes, ext={ext})")

    try:
        # STT + 감정 분석 동시 수행
        from agents.speech_emotion_analyzer import stt_with_emotion

        result = await stt_with_emotion(tmp_path)
        transcription = result.get("transcription", "")
        detected_language = result.get("detected_language", "ja")
        emotion_analysis = result.get("emotion_analysis", {})

        if not transcription:
            raise HTTPException(status_code=422, detail="음성에서 텍스트를 추출할 수 없었습니다")

        # DB에 상담 등록
        db = get_supabase()
        input_lang = "ko" if detected_language == "ko" else "ja"

        insert_data = {
            "customer_id": customer_id or None,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_line_id": customer_line_id or None,
            "original_text": transcription,
            "input_language": input_lang,
            "voice_emotion_analysis": emotion_analysis,
            "status": "registered",
        }

        consultation = db.table("consultations").insert(insert_data).execute()
        consultation_id = consultation.data[0]["id"]

        logger.info(
            f"[UploadAudio] Consultation created: {consultation_id}, "
            f"lang={detected_language}, voice_cta={emotion_analysis.get('voice_cta', {}).get('level', 'N/A')}"
        )

        return {
            "id": consultation_id,
            "status": "registered",
            "detected_language": detected_language,
            "transcription_length": len(transcription),
            "voice_emotion_analysis": emotion_analysis,
        }

    finally:
        # 임시 파일 정리
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/{consultation_id}/analyze-audio")
async def analyze_audio_for_existing(
    consultation_id: str,
    audio_file: UploadFile = File(...),
):
    """기존 상담에 음성 파일로 감정 분석 추가 (STT 없이 감정 분석만).

    이미 텍스트가 등록된 상담에 음성 감정 분석을 추가할 때 사용.
    """
    db = get_supabase()

    # 상담 존재 확인
    existing = db.table("consultations").select("id").eq("id", consultation_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Consultation not found")

    # 확장자 검증
    _, ext = os.path.splitext(audio_file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 오디오 포맷: {ext}",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await audio_file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from agents.speech_emotion_analyzer import analyze_speech_emotion

        emotion_analysis = await analyze_speech_emotion(tmp_path)

        # DB 업데이트
        db.table("consultations").update(
            {"voice_emotion_analysis": emotion_analysis}
        ).eq("id", consultation_id).execute()

        logger.info(
            f"[AnalyzeAudio] Emotion analysis added: {consultation_id}, "
            f"voice_cta={emotion_analysis.get('voice_cta', {}).get('level', 'N/A')}"
        )

        return {
            "id": consultation_id,
            "voice_emotion_analysis": emotion_analysis,
        }

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
