# 벡터DB 구축 가이드 — YouTube 자막 → FAQ → pgvector

## 대상 채널 4개

| # | 채널명 | 카테고리 | YouTube Channel ID | 핸들 | 구독자 |
|---|--------|---------|-------------------|------|--------|
| 1 | 오프라이드 oh-pride (오가나) | 피부과 | `UC8av1CNslnPQS3N08rkzzhQ` | @ohpride | 30만+ |
| 2 | Dr. Judy 닥터주디 피부과전문의 | 피부과 | `UC5lOe8buRS42zIjN0H4o_WA` | @DrJudy-judy | 24만+ |
| 3 | 나나TV - 나나성형외과 | 성형외과 | `UCQdXdttJJTiHwCczJGkgRIg` | @nanatv_nana | 구독자 다수 |
| 4 | 에이트성형외과 EIGHT EFFECT | 성형외과 | (아래 스크립트로 자동 조회) | @EIGHTEFFECT | 3.4만+ |

> ⚠️ 에이트성형외과 Channel ID는 핸들(@EIGHTEFFECT)로 YouTube API를 통해 자동 조회합니다.

---

## STEP 1: YouTube Data API v3 설정

### 1-1. Google Cloud Console 프로젝트 생성

1. https://console.cloud.google.com 접속
2. 상단 프로젝트 선택 → **[새 프로젝트]**
   - 프로젝트 이름: `ippo-youtube`
   - [만들기] 클릭
3. 생성된 프로젝트 선택

### 1-2. YouTube Data API v3 활성화

1. 좌측 메뉴 → **API 및 서비스** → **라이브러리**
2. 검색: `YouTube Data API v3`
3. **[사용]** 클릭하여 활성화

### 1-3. API 키 발급

1. 좌측 메뉴 → **API 및 서비스** → **사용자 인증 정보**
2. 상단 **[+ 사용자 인증 정보 만들기]** → **API 키**
3. 생성된 API 키 복사
4. (선택) **키 제한** 설정:
   - API 제한 → YouTube Data API v3만 허용
   - 애플리케이션 제한 → 없음 (서버에서 사용하므로)

### 1-4. .env에 추가

```env
YOUTUBE_API_KEY=AIzaSy.....발급받은_키
```

### 1-5. 할당량 (Quota) 확인

- 기본 무료 할당량: **하루 10,000 단위**
- 채널 영상 목록 조회 (search.list): 100 단위/요청
- 영상 상세 조회 (videos.list): 1 단위/요청
- **자막 추출은 YouTube API가 아닌 `youtube-transcript-api` 파이썬 라이브러리** 사용 (할당량 무관)

> 💡 영상 목록 조회만 API 사용, 자막 추출은 별도 라이브러리라서 할당량 걱정 없습니다.

---

## STEP 2: 전체 파이프라인 아키텍처

```
[채널 ID 4개]
     │
     ▼
┌─────────────────────┐
│ ① 영상 목록 수집     │  YouTube Data API v3
│   (채널별 전체 영상)   │  → youtube_sources 테이블에 저장
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ ② 자막 추출          │  youtube-transcript-api (무료, 무제한)
│   (자동생성 한국어 자막) │  → raw_transcript 컬럼에 저장
│   자막 없으면 → SKIP   │  → status: 'skipped'
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ ③ 자막 정제 (LLM)     │  Gemini API
│   오탈자 수정          │  → refined_transcript 컬럼에 저장
│   의료용어 교정         │
│   문장 단위 정리        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ ④ FAQ 변환 (LLM)      │  Gemini API
│   환자 Q + 의사 A 쌍   │  → faq_vectors 테이블에 저장
│   시술명 태깅           │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ ⑤ 임베딩 + 벡터 저장   │  Gemini Embedding (768차원)
│   question 기준 임베딩   │  → faq_vectors.embedding 컬럼
│   Supabase pgvector    │
└─────────────────────┘
```

---

## STEP 3: 파이썬 코드 — 전체 파이프라인

### 3-0. 필요 패키지

```bash
pip install google-generativeai supabase youtube-transcript-api google-api-python-client python-dotenv
```

### 3-1. 환경 설정 (config.py)

```python
# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# 대상 채널 정보
TARGET_CHANNELS = [
    {
        "channel_id": "UC8av1CNslnPQS3N08rkzzhQ",
        "name": "오프라이드 oh-pride",
        "category": "dermatology"
    },
    {
        "channel_id": "UC5lOe8buRS42zIjN0H4o_WA",
        "name": "닥터주디 피부과전문의",
        "category": "dermatology"
    },
    {
        "channel_id": "UCQdXdttJJTiHwCczJGkgRIg",
        "name": "나나TV - 나나성형외과",
        "category": "plastic_surgery"
    },
    {
        "channel_id": "",  # 아래 resolve_handle_to_channel_id()로 자동 조회
        "handle": "@EIGHTEFFECT",
        "name": "에이트성형외과 EIGHT EFFECT",
        "category": "plastic_surgery"
    }
]
```

### 3-2. 채널 핸들 → Channel ID 자동 변환

```python
# backend/services/youtube_service.py (일부)
from googleapiclient.discovery import build
from config import YOUTUBE_API_KEY

youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def resolve_handle_to_channel_id(handle: str) -> str:
    """@핸들로 Channel ID 조회"""
    # handle에서 @ 제거
    clean_handle = handle.lstrip("@")
    
    response = youtube.search().list(
        part="snippet",
        q=clean_handle,
        type="channel",
        maxResults=1
    ).execute()
    
    if response["items"]:
        return response["items"][0]["snippet"]["channelId"]
    return None
```

### 3-3. ① 채널별 영상 목록 수집

```python
# backend/services/youtube_service.py
import time
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def fetch_channel_videos(channel_id: str, category: str, channel_name: str):
    """
    채널의 전체 영상 목록을 YouTube API로 수집하여 DB에 저장.
    YouTube API는 pageToken으로 페이지네이션.
    """
    next_page_token = None
    total_fetched = 0
    
    while True:
        response = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            type="video",
            order="date",
            maxResults=50,  # 최대 50개/요청
            pageToken=next_page_token
        ).execute()
        
        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            
            # 중복 체크 후 DB 저장
            existing = supabase.table("youtube_sources").select("id").eq("video_id", video_id).execute()
            
            if not existing.data:
                supabase.table("youtube_sources").insert({
                    "video_id": video_id,
                    "title": title,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "channel_name": channel_name,
                    "category": category,
                    "status": "pending"
                }).execute()
                total_fetched += 1
        
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
        
        time.sleep(0.5)  # API 속도 조절
    
    print(f"[{channel_name}] {total_fetched}개 영상 수집 완료")
    return total_fetched


def fetch_all_channels():
    """모든 대상 채널의 영상 수집"""
    from config import TARGET_CHANNELS
    
    for ch in TARGET_CHANNELS:
        channel_id = ch["channel_id"]
        
        # 핸들만 있는 경우 Channel ID 조회
        if not channel_id and ch.get("handle"):
            channel_id = resolve_handle_to_channel_id(ch["handle"])
            if channel_id:
                print(f"[{ch['name']}] 핸들 {ch['handle']} → Channel ID: {channel_id}")
            else:
                print(f"[{ch['name']}] 핸들로 Channel ID를 찾을 수 없습니다!")
                continue
        
        fetch_channel_videos(channel_id, ch["category"], ch["name"])
```

### 3-4. ② 자막 추출

```python
# backend/services/youtube_service.py (계속)
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled, 
    NoTranscriptFound,
    VideoUnavailable
)

def fetch_transcript(video_id: str) -> str | None:
    """
    YouTube 자동생성 자막 추출.
    한국어 자막 우선 → 없으면 영어 → 없으면 None.
    """
    try:
        # 한국어 자막 시도
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 1순위: 한국어 수동/자동 자막
        try:
            transcript = transcript_list.find_transcript(["ko"])
        except:
            # 2순위: 자동 생성된 한국어 자막
            try:
                transcript = transcript_list.find_generated_transcript(["ko"])
            except:
                return None
        
        # 자막 텍스트 합치기
        entries = transcript.fetch()
        full_text = " ".join([entry["text"] for entry in entries])
        return full_text
        
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return None
    except Exception as e:
        print(f"[자막 추출 실패] {video_id}: {e}")
        return None


def extract_all_transcripts():
    """
    pending 상태의 모든 영상에서 자막 추출.
    자막 있으면 → 'transcript_fetched'
    자막 없으면 → 'skipped'
    """
    pending = supabase.table("youtube_sources")\
        .select("*")\
        .eq("status", "pending")\
        .execute()
    
    total = len(pending.data)
    success = 0
    skipped = 0
    
    for i, video in enumerate(pending.data):
        video_id = video["video_id"]
        print(f"[{i+1}/{total}] 자막 추출 중: {video['title'][:40]}...")
        
        transcript = fetch_transcript(video_id)
        
        if transcript and len(transcript) > 100:  # 100자 이상만 유효
            supabase.table("youtube_sources").update({
                "raw_transcript": transcript,
                "status": "transcript_fetched"
            }).eq("video_id", video_id).execute()
            success += 1
        else:
            supabase.table("youtube_sources").update({
                "status": "skipped"
            }).eq("video_id", video_id).execute()
            skipped += 1
        
        time.sleep(0.3)  # 속도 조절
    
    print(f"\n자막 추출 완료: 성공 {success}개, 스킵 {skipped}개 / 총 {total}개")
```

### 3-5. ③ 자막 정제 (Gemini LLM)

```python
# backend/services/youtube_service.py (계속)
import google.generativeai as genai
from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

REFINE_PROMPT = """당신은 한국어 의료 콘텐츠 전문 교정자입니다.
아래는 YouTube 의료 영상의 자동생성 자막입니다. 다음 작업을 수행하세요:

1. **오탈자 수정**: 자동 자막 특성상 오타가 많습니다. 문맥에 맞게 교정하세요.
2. **의료 용어 교정**: 
   - "울세라" → "울쎄라"
   - "하이후" → "하이푸" (HIFU)
   - "보톡스" → "보톡스" (맞으면 유지)
   - "필라" → "필러"
   - "레이져" → "레이저"
   - 기타 잘못된 의료 용어를 올바르게 교정
3. **문장 단위 정리**: 자연스러운 문장으로 재구성하세요.
4. **불필요한 내용 제거**: "구독 좋아요", "광고", "인트로/아웃트로 인사" 등 의료 정보와 무관한 부분은 제거하세요.
5. **의료 정보만 남기기**: 시술 설명, 효과, 부작용, 회복기간, 주의사항 등 의료 정보 위주로 정리하세요.

원본 자막:
{transcript}

정제된 텍스트를 반환하세요. 마크다운이나 제목 없이 순수 텍스트만 반환하세요."""


def refine_transcript(raw_transcript: str) -> str:
    """LLM으로 자막 정제"""
    # 너무 긴 자막은 청크로 나누기 (Gemini 입력 제한 고려)
    MAX_CHARS = 15000
    
    if len(raw_transcript) <= MAX_CHARS:
        response = model.generate_content(
            REFINE_PROMPT.format(transcript=raw_transcript)
        )
        return response.text
    
    # 긴 자막은 청크 분할 후 각각 정제
    chunks = [raw_transcript[i:i+MAX_CHARS] for i in range(0, len(raw_transcript), MAX_CHARS)]
    refined_parts = []
    
    for chunk in chunks:
        response = model.generate_content(
            REFINE_PROMPT.format(transcript=chunk)
        )
        refined_parts.append(response.text)
        time.sleep(1)  # API 속도 조절
    
    return "\n\n".join(refined_parts)


def refine_all_transcripts():
    """transcript_fetched 상태의 모든 영상 자막 정제"""
    fetched = supabase.table("youtube_sources")\
        .select("*")\
        .eq("status", "transcript_fetched")\
        .execute()
    
    total = len(fetched.data)
    
    for i, video in enumerate(fetched.data):
        print(f"[{i+1}/{total}] 정제 중: {video['title'][:40]}...")
        
        try:
            refined = refine_transcript(video["raw_transcript"])
            
            supabase.table("youtube_sources").update({
                "refined_transcript": refined,
                "status": "refined"
            }).eq("video_id", video["video_id"]).execute()
            
        except Exception as e:
            print(f"  → 정제 실패: {e}")
            supabase.table("youtube_sources").update({
                "status": "failed"
            }).eq("video_id", video["video_id"]).execute()
        
        time.sleep(1.5)  # Gemini API 속도 조절 (무료 티어: 15 RPM)
    
    print(f"\n정제 완료: {total}개")
```

### 3-6. ④ FAQ 변환 (Gemini LLM)

```python
# backend/services/youtube_service.py (계속)
import json

FAQ_PROMPT = """당신은 의료 콘텐츠에서 FAQ를 추출하는 전문가입니다.
아래 정제된 의료 영상 텍스트에서 환자 관점의 FAQ를 추출하세요.

카테고리: {category_kr}

규칙:
1. 각 FAQ는 환자가 실제로 궁금해할 만한 질문이어야 합니다.
2. 답변은 영상 내용을 기반으로 의료진 설명을 2~3문장으로 정리하세요.
3. 관련 시술명을 태깅하세요.
4. 영상 하나당 3~8개의 FAQ를 추출하세요.
5. 영상에 의료 정보가 거의 없으면 빈 배열 []을 반환하세요.

반드시 아래 JSON 형식으로만 반환하세요 (마크다운 코드블록 없이):
[
  {{
    "question": "환자 관점의 질문",
    "answer": "의료진 설명 (2~3문장, 근거 포함)",
    "procedure_name": "관련 시술명 (없으면 null)"
  }}
]

텍스트:
{text}"""


def generate_faqs(refined_text: str, category: str) -> list:
    """정제된 텍스트에서 FAQ 추출"""
    category_kr = "피부과" if category == "dermatology" else "성형외과"
    
    response = model.generate_content(
        FAQ_PROMPT.format(category_kr=category_kr, text=refined_text)
    )
    
    # JSON 파싱 (마크다운 코드블록 제거)
    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    
    try:
        faqs = json.loads(text)
        return faqs if isinstance(faqs, list) else []
    except json.JSONDecodeError:
        print(f"  → JSON 파싱 실패")
        return []


def generate_all_faqs():
    """refined 상태의 모든 영상에서 FAQ 생성"""
    refined = supabase.table("youtube_sources")\
        .select("*")\
        .eq("status", "refined")\
        .execute()
    
    total = len(refined.data)
    total_faqs = 0
    
    for i, video in enumerate(refined.data):
        print(f"[{i+1}/{total}] FAQ 생성 중: {video['title'][:40]}...")
        
        try:
            faqs = generate_faqs(video["refined_transcript"], video["category"])
            
            if faqs:
                # DB에 FAQ 저장 (임베딩은 다음 단계)
                for faq in faqs:
                    supabase.table("faq_vectors").insert({
                        "category": video["category"],
                        "question": faq["question"],
                        "answer": faq["answer"],
                        "procedure_name": faq.get("procedure_name"),
                        "youtube_video_id": video["video_id"],
                        "youtube_title": video["title"],
                        "youtube_url": video["url"],
                        "embedding": [0.0] * 768  # 임시 더미 벡터 (다음 단계에서 업데이트)
                    }).execute()
                
                total_faqs += len(faqs)
            
            # 영상 상태 업데이트
            supabase.table("youtube_sources").update({
                "status": "faq_generated",
                "faq_count": len(faqs)
            }).eq("video_id", video["video_id"]).execute()
            
        except Exception as e:
            print(f"  → FAQ 생성 실패: {e}")
            supabase.table("youtube_sources").update({
                "status": "failed"
            }).eq("video_id", video["video_id"]).execute()
        
        time.sleep(1.5)
    
    print(f"\nFAQ 생성 완료: 총 {total_faqs}개 FAQ / {total}개 영상")
```

### 3-7. ⑤ 임베딩 + 벡터 저장

```python
# backend/services/youtube_service.py (계속)

def generate_embedding(text: str) -> list[float]:
    """Gemini Embedding 768차원 벡터 생성"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]  # 768차원 float 배열


def embed_all_faqs():
    """
    임시 더미 벡터(모두 0)인 FAQ들을 찾아서 실제 임베딩으로 업데이트.
    question을 기준으로 임베딩 생성 (검색 시 환자 질문과 매칭하기 위함).
    """
    # 더미 벡터인 FAQ 조회 (embedding의 첫 값이 0인 것)
    # Supabase에서 벡터 필터가 어려우므로, youtube_sources 상태 기준으로 처리
    
    sources = supabase.table("youtube_sources")\
        .select("video_id")\
        .eq("status", "faq_generated")\
        .execute()
    
    total_embedded = 0
    
    for source in sources.data:
        video_id = source["video_id"]
        
        # 이 영상의 FAQ들 조회
        faqs = supabase.table("faq_vectors")\
            .select("id, question")\
            .eq("youtube_video_id", video_id)\
            .execute()
        
        for faq in faqs.data:
            try:
                embedding = generate_embedding(faq["question"])
                
                supabase.table("faq_vectors").update({
                    "embedding": embedding
                }).eq("id", faq["id"]).execute()
                
                total_embedded += 1
                
            except Exception as e:
                print(f"  → 임베딩 실패 (FAQ {faq['id']}): {e}")
            
            time.sleep(0.3)  # Gemini Embedding API 속도 조절
        
        # 영상 상태 업데이트
        supabase.table("youtube_sources").update({
            "status": "embedded"
        }).eq("video_id", video_id).execute()
    
    print(f"\n임베딩 완료: {total_embedded}개 FAQ 벡터화")
```

### 3-8. 전체 파이프라인 실행 스크립트

```python
# backend/scripts/build_vector_db.py
"""
벡터DB 구축 전체 파이프라인 실행 스크립트.
한 번에 실행하면 4개 채널의 모든 영상을 수집 → 자막 추출 → 정제 → FAQ → 임베딩 완료.

사용법:
  python -m scripts.build_vector_db
  
또는 단계별 실행:
  python -m scripts.build_vector_db --step 1  # 영상 수집만
  python -m scripts.build_vector_db --step 2  # 자막 추출만
  python -m scripts.build_vector_db --step 3  # 자막 정제만
  python -m scripts.build_vector_db --step 4  # FAQ 생성만
  python -m scripts.build_vector_db --step 5  # 임베딩만
"""
import sys
import argparse
from services.youtube_service import (
    fetch_all_channels,
    extract_all_transcripts,
    refine_all_transcripts,
    generate_all_faqs,
    embed_all_faqs
)

def run_pipeline(step=None):
    steps = {
        1: ("영상 목록 수집", fetch_all_channels),
        2: ("자막 추출", extract_all_transcripts),
        3: ("자막 정제 (LLM)", refine_all_transcripts),
        4: ("FAQ 변환 (LLM)", generate_all_faqs),
        5: ("임베딩 + 벡터 저장", embed_all_faqs),
    }
    
    if step:
        name, func = steps[step]
        print(f"\n{'='*50}")
        print(f"  STEP {step}: {name}")
        print(f"{'='*50}\n")
        func()
    else:
        # 전체 실행
        for step_num, (name, func) in steps.items():
            print(f"\n{'='*50}")
            print(f"  STEP {step_num}/5: {name}")
            print(f"{'='*50}\n")
            func()
            print(f"\n  ✅ STEP {step_num} 완료!\n")
        
        # 최종 통계 출력
        print_stats()


def print_stats():
    """최종 벡터DB 통계 출력"""
    from services.youtube_service import supabase
    
    print(f"\n{'='*50}")
    print(f"  📊 벡터DB 구축 최종 통계")
    print(f"{'='*50}")
    
    # 채널별 통계
    for category, label in [("dermatology", "💊 피부과"), ("plastic_surgery", "🏥 성형외과")]:
        sources = supabase.table("youtube_sources")\
            .select("status", count="exact")\
            .eq("category", category)\
            .execute()
        
        embedded = supabase.table("youtube_sources")\
            .select("*", count="exact")\
            .eq("category", category)\
            .eq("status", "embedded")\
            .execute()
        
        skipped = supabase.table("youtube_sources")\
            .select("*", count="exact")\
            .eq("category", category)\
            .eq("status", "skipped")\
            .execute()
        
        faqs = supabase.table("faq_vectors")\
            .select("*", count="exact")\
            .eq("category", category)\
            .execute()
        
        print(f"\n  {label}")
        print(f"    총 영상: {sources.count}개")
        print(f"    임베딩 완료: {embedded.count}개")
        print(f"    스킵 (자막없음): {skipped.count}개")
        print(f"    생성된 FAQ: {faqs.count}개")
    
    total_faqs = supabase.table("faq_vectors").select("*", count="exact").execute()
    print(f"\n  🎯 전체 FAQ 벡터: {total_faqs.count}개")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, choices=[1,2,3,4,5], help="실행할 단계 (1-5)")
    args = parser.parse_args()
    
    run_pipeline(args.step)
```

---

## STEP 4: CLAUDE.md 업데이트 사항

아래 내용을 기존 CLAUDE.md의 환경변수 섹션과 YouTube 파이프라인 섹션에 반영하세요:

```
# .env 추가
YOUTUBE_API_KEY=AIzaSy.....  # Google Cloud Console에서 발급

# 대상 채널 4개
오프라이드 oh-pride:       UC8av1CNslnPQS3N08rkzzhQ  (피부과)
닥터주디 피부과전문의:      UC5lOe8buRS42zIjN0H4o_WA  (피부과)
나나TV 나나성형외과:        UCQdXdttJJTiHwCczJGkgRIg  (성형외과)
에이트성형외과 EIGHT EFFECT: @EIGHTEFFECT 핸들로 자동조회 (성형외과)
```

---

## STEP 5: 예상 소요 시간 & 비용

### 소요 시간 (4개 채널 기준)

| 단계 | 예상 시간 | 병목 |
|------|----------|------|
| ① 영상 수집 | 5~10분 | YouTube API 할당량 |
| ② 자막 추출 | 30~60분 | 영상 수 (예: 1,000개) |
| ③ 자막 정제 | 2~4시간 | Gemini API 속도 제한 |
| ④ FAQ 변환 | 2~4시간 | Gemini API 속도 제한 |
| ⑤ 임베딩 | 1~2시간 | Gemini Embedding API |
| **합계** | **약 6~10시간** | 전체 자동 실행 |

### 비용

| 항목 | 비용 |
|------|------|
| YouTube Data API | 무료 (일 10,000 단위 할당량 내) |
| youtube-transcript-api | 무료 (비공식 라이브러리) |
| Gemini API (정제+FAQ) | 무료 티어: 15 RPM, 충분 |
| Gemini Embedding | 무료 티어: 1,500 RPM |
| Supabase pgvector | 무료 플랜 내 |
| **합계** | **무료** (모두 무료 티어 내) |

> 💡 Gemini 무료 티어 속도 제한(15 RPM)으로 3~4단계가 가장 오래 걸립니다.
> 유료 API 키 사용 시 1~2시간으로 단축 가능합니다.

---

## STEP 6: 벡터DB 검증 쿼리

구축 완료 후 제대로 동작하는지 확인:

```sql
-- 1. 카테고리별 FAQ 수 확인
SELECT category, COUNT(*) as faq_count 
FROM faq_vectors 
GROUP BY category;

-- 2. 시술명별 FAQ 수 확인
SELECT procedure_name, COUNT(*) as cnt 
FROM faq_vectors 
WHERE procedure_name IS NOT NULL 
GROUP BY procedure_name 
ORDER BY cnt DESC 
LIMIT 20;

-- 3. 유사도 검색 테스트 (예: "코끝이 뾰족해 보이는 이유")
-- Supabase Dashboard > SQL Editor에서 실행:
SELECT 
  question, 
  answer, 
  procedure_name,
  1 - (embedding <=> (
    -- 여기에 "코끝이 뾰족해 보이는 이유"의 임베딩 벡터를 넣어야 함
    -- 실제로는 API에서 search_faq() RPC 호출
  )) as similarity
FROM faq_vectors
WHERE category = 'plastic_surgery'
ORDER BY embedding <=> '[벡터]'
LIMIT 5;
```

---

## 주의사항

1. **오프라이드 채널 주의**: 럭셔리/자동차/부동산 브이로그도 많음. 제목에 "피부", "시술", "레이저" 등이 포함된 영상만 필터링하는 로직 추가 권장.
2. **Gemini 무료 티어 RPM 제한**: 15 RPM → `time.sleep(4)` 이상 권장. 429 에러 시 자동 재시도 로직 필요.
3. **자막 품질**: 자동생성 자막이라 품질이 낮을 수 있음. 정제 단계(STEP 3)가 매우 중요.
4. **FAQ 품질 검수**: 초기 구축 후 일부 FAQ를 샘플링하여 수동 검수 권장.
5. **증분 업데이트**: 최초 구축 후 주기적으로 새 영상만 추가 처리하는 로직이 필요 (status='pending'인 것만 처리하므로 자동으로 됨).
