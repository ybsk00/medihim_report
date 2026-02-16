import json
from fastapi import APIRouter, HTTPException
from models.schemas import YouTubeAddRequest
from services.supabase_client import get_supabase
from services.youtube_service import extract_video_id, fetch_transcript
from services.gemini_client import generate_json, get_embedding

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


@router.post("/add")
async def add_youtube_source(data: YouTubeAddRequest):
    video_id = extract_video_id(data.video_url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    db = get_supabase()

    # 중복 확인
    existing = db.table("youtube_sources").select("id").eq("video_id", video_id).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Video already registered")

    result = db.table("youtube_sources").insert({
        "video_id": video_id,
        "url": f"https://youtube.com/watch?v={video_id}",
        "category": data.category,
        "status": "pending",
    }).execute()

    return {"id": result.data[0]["id"], "video_id": video_id}


@router.post("/process")
async def process_youtube_sources():
    db = get_supabase()

    # pending 상태인 영상 조회
    sources = db.table("youtube_sources").select("*").eq("status", "pending").execute()

    results = []
    for source in sources.data:
        video_id = source["video_id"]
        category = source["category"]

        # 1. 자막 추출
        transcript = fetch_transcript(video_id)
        if not transcript:
            db.table("youtube_sources").update({"status": "skipped"}).eq("id", source["id"]).execute()
            results.append({"video_id": video_id, "status": "skipped", "reason": "No transcript"})
            continue

        db.table("youtube_sources").update({
            "raw_transcript": transcript,
            "status": "transcript_fetched",
        }).eq("id", source["id"]).execute()

        # 2. 자막 정제
        refine_prompt = f"""다음 YouTube 자동 자막을 정제해주세요.
- 오탈자 수정
- 의료 용어 교정 (울세라→울쎄라, 하이후→하이푸 등)
- 문장 단위로 정리

원본 자막:
{transcript[:3000]}

JSON 형식으로 반환:
{{"refined_text": "정제된 텍스트"}}"""

        refined_result = await generate_json(refine_prompt)
        refined_data = json.loads(refined_result)
        refined_text = refined_data.get("refined_text", transcript)

        db.table("youtube_sources").update({
            "refined_transcript": refined_text,
            "status": "refined",
        }).eq("id", source["id"]).execute()

        # 3. FAQ 변환
        faq_prompt = f"""이 의료 영상 자막에서 FAQ를 추출해주세요.
각 FAQ는 다음 형식으로 작성:
- question: 환자 관점의 질문 (예: "코끝이 뾰족해 보이는 이유는?")
- answer: 의료진 설명 (근거 포함, 2~3문장)
- procedure_name: 관련 시술명

JSON 배열로 반환:
{{"faqs": [{{"question": "...", "answer": "...", "procedure_name": "..."}}]}}

정제된 자막:
{refined_text[:3000]}"""

        faq_result = await generate_json(faq_prompt)
        faq_data = json.loads(faq_result)
        faqs = faq_data.get("faqs", [])

        db.table("youtube_sources").update({
            "status": "faq_generated",
            "faq_count": len(faqs),
        }).eq("id", source["id"]).execute()

        # 4. 임베딩 + 저장
        for faq in faqs:
            embed_text = f"{faq['question']} {faq['answer']}"
            embedding = await get_embedding(embed_text)

            db.table("faq_vectors").insert({
                "category": category,
                "question": faq["question"],
                "answer": faq["answer"],
                "procedure_name": faq.get("procedure_name", ""),
                "embedding": embedding,
                "youtube_video_id": video_id,
                "youtube_url": f"https://youtube.com/watch?v={video_id}",
            }).execute()

        db.table("youtube_sources").update({"status": "embedded"}).eq("id", source["id"]).execute()

        results.append({
            "video_id": video_id,
            "status": "embedded",
            "faq_count": len(faqs),
        })

    return {"processed": len(results), "results": results}


@router.get("/sources")
async def list_youtube_sources():
    db = get_supabase()
    result = (
        db.table("youtube_sources")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return {"data": result.data}
