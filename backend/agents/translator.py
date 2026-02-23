import logging

from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """あなたは医療通訳の専門家です。日本語の医療相談内容を韓国語に正確に翻訳してください。

翻訳ルール:
- 医療用語（施術名、部位名）は正確に翻訳すること
- 患者のニュアンス（不安、希望の程度など）を保持すること
- 固有名詞は原文を併記すること
- 自然な韓国語にすること"""


def detect_language(text: str) -> str:
    """일본어/한국어 문자 비율로 언어 감지.
    일본어(히라가나+가타카나) 비율이 30% 이상이면 일본어, 아니면 한국어.
    한일 혼합 대화(의사가 가끔 일본어 사용)를 정확히 판별."""
    japanese_chars = sum(
        1 for c in text
        if ('\u3040' <= c <= '\u309F')   # 히라가나
        or ('\u30A0' <= c <= '\u30FF')   # 가타카나
    )
    korean_chars = sum(
        1 for c in text
        if ('\uAC00' <= c <= '\uD7AF')   # 완성형 한글
        or ('\u1100' <= c <= '\u11FF')   # 한글 자모
        or ('\u3130' <= c <= '\u318F')   # 호환용 한글 자모
    )
    total_cjk = japanese_chars + korean_chars
    if total_cjk == 0:
        result = "ko"  # CJK 문자 없으면 기본 한국어
    else:
        ja_ratio = japanese_chars / total_cjk
        result = "ja" if ja_ratio > 0.3 else "ko"

    logger.info(
        f"[Language] Detected '{result}' "
        f"(ja={japanese_chars}, ko={korean_chars}, ratio={japanese_chars}/{total_cjk}="
        f"{(japanese_chars/total_cjk*100 if total_cjk else 0):.1f}%)"
    )
    return result


async def translate_to_korean(text: str) -> tuple[str, str]:
    """번역 + 언어 감지. 한국어 입력이면 번역 스킵.

    Returns:
        (translated_text, detected_language)
    """
    lang = detect_language(text)

    if lang == "ko":
        logger.info("[Translator] Korean input detected — skipping translation")
        return text, "ko"

    # 기존 일본어 → 한국어 번역
    prompt = f"""以下の日本語テキストを韓国語に翻訳してください。

JSON形式で返してください:
{{"translated_text": "翻訳結果"}}

日本語原文:
{text}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    data = safe_parse_json(result)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data.get("translated_text", ""), "ja"
