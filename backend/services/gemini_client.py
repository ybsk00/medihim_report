import asyncio
import json
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


def repair_json(text: str) -> str:
    """Gemini가 반환한 불완전한 JSON을 복구 시도.
    - 제어 문자 제거
    - markdown 코드 블록 제거
    - 후행 콤마 제거
    - 누락된 콤마 삽입 (}"  → }," / ]"  → ]," / ""  → "," 패턴)
    - 닫히지 않은 괄호 보정
    """
    s = _clean_json_text(text).strip()

    # markdown 코드 블록 제거
    if s.startswith("```"):
        s = re.sub(r'^```(?:json)?\s*', '', s)
        s = re.sub(r'\s*```\s*$', '', s)

    # 후행 콤마 제거: ,} → } / ,] → ]
    s = re.sub(r',\s*([}\]])', r'\1', s)

    # 누락된 콤마 삽입: }\s*" → }," / ]\s*" → ]," / "\s*" → ","  (문자열 값 사이)
    s = re.sub(r'(})\s*(")', r'\1,\2', s)
    s = re.sub(r'(])\s*(")', r'\1,\2', s)
    # "value"\n"key" 패턴 (줄바꿈으로 구분된 연속 문자열 — 배열 내부)
    s = re.sub(r'(")\s*\n\s*(")', r'\1,\2', s)

    # 닫히지 않은 괄호 보정
    open_braces = s.count('{') - s.count('}')
    open_brackets = s.count('[') - s.count(']')
    if open_braces > 0:
        s += '}' * open_braces
    if open_brackets > 0:
        s += ']' * open_brackets

    return s


def safe_parse_json(text: str) -> dict | list:
    """JSON 파싱 시도 → 실패하면 repair 후 재시도.
    모든 에이전트가 공통으로 사용하는 안전한 JSON 파서."""
    cleaned = _clean_json_text(text)
    # 1차: 그대로 파싱
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2차: repair 후 파싱
    repaired = repair_json(text)
    try:
        data = json.loads(repaired)
        logger.warning("[JSON Repair] Successfully repaired malformed JSON from Gemini")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"[JSON Repair] Failed even after repair: {str(e)[:200]}")
        raise


async def generate_json(prompt: str, system_instruction: str = "", max_retries: int = 3) -> str:
    """JSON 생성 + 파싱 검증. 파싱 실패 시 Gemini 재호출."""
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=system_instruction,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )
    last_error = None
    for attempt in range(max_retries):
        response = await _retry_generate(model, prompt)
        raw_text = _clean_json_text(response.text)
        # repair + 파싱 검증
        try:
            safe_parse_json(raw_text)
            return raw_text  # 파싱 가능한 JSON 확인됨
        except json.JSONDecodeError as e:
            last_error = e
            if attempt < max_retries - 1:
                logger.warning(
                    f"[generate_json] JSON parse failed on attempt {attempt + 1}/{max_retries}, "
                    f"retrying: {str(e)[:100]}"
                )
                await asyncio.sleep(2 * (attempt + 1))
                continue
    # 모든 재시도 실패 시, repair된 결과라도 반환 시도
    logger.error(f"[generate_json] All {max_retries} attempts failed, returning last repaired text")
    return repair_json(response.text)


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
