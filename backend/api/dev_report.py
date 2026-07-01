"""DEV 전용: 리포트를 디자인용 라벨 블록 JSON으로 제공.

메디힘 새 개발사가 아이프레임 대신 JSON을 받아 자체 디자인을 입히는 용도.
콜백의 json_url(DEV에만 포함)이 이 엔드포인트를 가리킨다.

- 운영(PROD) 무관: 추가 엔드포인트일 뿐, 기존 API/아이프레임에 영향 없음.
- DB 읽기 전용: report_data를 변환만 한다. 열람 추적(email_opened_at) 갱신하지 않음.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from services.supabase_client import get_supabase
from services.dev_report_format import to_design_blocks

router = APIRouter(prefix="/api/dev/report", tags=["dev_report"])


@router.get("/{lang}/{token}.json")
async def get_dev_report_json(lang: str, token: str):
    """토큰으로 리포트 조회 → 디자인용 블록 JSON 반환.

    lang: ja | ko  (r3는 lang 무관하게 한국어 데이터 사용)
    """
    db = get_supabase()

    report = (
        db.table("reports")
        .select(
            "id, report_data, report_data_ko, report_type, status, "
            "consultations(customer_name, consultation_round)"
        )
        .eq("access_token", token)
        .single()
        .execute()
    )

    if not report.data:
        raise HTTPException(status_code=404, detail="Report not found")

    # 아이프레임 embed와 동일한 가시성 기준 (승인 전 미리보기 허용)
    if report.data["status"] not in ("draft", "approved", "sent"):
        raise HTTPException(status_code=403, detail="Report is not available")

    report_type = report.data.get("report_type", "r4")

    # 언어 선택: ko 요청 + 한국어 캐시 있으면 ko, 아니면 원본
    use_lang = "ko" if lang == "ko" else "ja"
    report_data = report.data["report_data"]
    if use_lang == "ko" and report.data.get("report_data_ko"):
        report_data = report.data["report_data_ko"]

    consultation = report.data.get("consultations") or {}
    customer_name = consultation.get("customer_name") or ""
    consultation_round = consultation.get("consultation_round") or 3

    blocks = to_design_blocks(
        report_data=report_data,
        report_type=report_type,
        customer_name=customer_name,
        consultation_round=consultation_round,
        lang=use_lang,
    )

    # 한글/일본어가 \uXXXX로 이스케이프되지 않도록 (개발사 가독성)
    return JSONResponse(content=blocks, media_type="application/json; charset=utf-8")
