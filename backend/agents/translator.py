import json
from services.gemini_client import generate_json

SYSTEM_INSTRUCTION = """あなたは医療通訳の専門家です。日本語の医療相談内容を韓国語に正確に翻訳してください。

翻訳ルール:
- 医療用語（施術名、部位名）は正確に翻訳すること
- 患者のニュアンス（不安、希望の程度など）を保持すること
- 固有名詞は原文を併記すること
- 自然な韓国語にすること"""


async def translate_to_korean(japanese_text: str) -> str:
    prompt = f"""以下の日本語テキストを韓国語に翻訳してください。

JSON形式で返してください:
{{"translated_text": "翻訳結果"}}

日本語原文:
{japanese_text}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    data = json.loads(result)
    return data.get("translated_text", "")
