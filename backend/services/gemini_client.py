import asyncio
import logging
import re
import google.generativeai as genai
from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

_model = None
_embedding_model = "models/gemini-embedding-001"

# 재시도 대상 에러 키워드
_RETRYABLE_ERRORS = ("429", "500", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "INTERNAL", "DeadlineExceeded", "timeout")


def get_model():
    global _model
    if _model is None:
        _model = genai.GenerativeModel("gemini-2.5-flash")
    return _model


async def _retry_generate(model, prompt: str, max_retries: int = 3):
    """Gemini generate_content를 스레드 풀에서 실행 (이벤트 루프 블로킹 방지)"""
    for attempt in range(max_retries):
        try:
            # 동기 호출을 스레드 풀에서 실행하여 이벤트 루프 블로킹 방지
            response = await asyncio.to_thread(model.generate_content, prompt)
            if response and response.text:
                return response
            # 빈 응답이면 재시도
            logger.warning(f"[Gemini] Empty response on attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3 * (attempt + 1))
                continue
            raise ValueError("Gemini returned empty response after all retries")
        except Exception as e:
            err_str = str(e)
            is_retryable = any(keyword in err_str for keyword in _RETRYABLE_ERRORS)

            if is_retryable and attempt < max_retries - 1:
                wait = 5 * (attempt + 1)
                logger.warning(f"[Gemini] Retryable error on attempt {attempt + 1}/{max_retries}, waiting {wait}s: {err_str[:150]}")
                await asyncio.sleep(wait)
                continue

            logger.error(f"[Gemini] Final failure after {attempt + 1} attempts: {err_str[:200]}")
            raise


async def generate_text(prompt: str, system_instruction: str = "") -> str:
    model = get_model()
    if system_instruction:
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            system_instruction=system_instruction,
        )
    response = await _retry_generate(model, prompt)
    return response.text


def _clean_json_text(text: str) -> str:
    """JSON 문자열 내부의 유효하지 않은 제어 문자 제거"""
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)


async def generate_json(prompt: str, system_instruction: str = "") -> str:
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=system_instruction,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    response = await _retry_generate(model, prompt)
    return _clean_json_text(response.text)


def _sync_embed_content(model_name: str, content: str, task_type: str, dims: int):
    """동기 임베딩 호출 (스레드 풀에서 실행용)"""
    return genai.embed_content(
        model=model_name,
        content=content,
        task_type=task_type,
        output_dimensionality=dims,
    )


async def get_embedding(text: str) -> list[float]:
    for attempt in range(3):
        try:
            result = await asyncio.to_thread(
                _sync_embed_content, _embedding_model, text, "retrieval_document", 768
            )
            return result["embedding"]
        except Exception as e:
            if attempt < 2:
                logger.warning(f"[Gemini Embedding] Retry {attempt + 1}: {str(e)[:100]}")
                await asyncio.sleep(3 * (attempt + 1))
            else:
                raise


async def get_query_embedding(text: str) -> list[float]:
    for attempt in range(3):
        try:
            result = await asyncio.to_thread(
                _sync_embed_content, _embedding_model, text, "retrieval_query", 768
            )
            return result["embedding"]
        except Exception as e:
            if attempt < 2:
                logger.warning(f"[Gemini Query Embedding] Retry {attempt + 1}: {str(e)[:100]}")
                await asyncio.sleep(3 * (attempt + 1))
            else:
                raise
