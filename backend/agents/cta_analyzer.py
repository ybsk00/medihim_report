import json
from services.gemini_client import generate_json

SYSTEM_INSTRUCTION = """あなたはCRM分析の専門家です。カウンセリングの対話から以下を分析してください:

1. 話者分離: 相談者(counselor)とお客様(customer)の発話を分離
2. CTA分析: お客様の発話のみを分析して購買意欲レベルを判定

CTA判定基準:
- Hot: 具体的な日程・費用の質問 (例: "7月に可能ですか？", "費用はいくら？", "回復期間は？")
- Warm: 関心はあるが比較・悩み中 (例: "他の病院では〜", "もう少し調べたい", "家族と相談します")
- Cool: 情報探索段階 (例: "ちょっと気になって", "まだ具体的には", "いつか機会があれば")"""


async def analyze_cta(
    original_text: str, translated_text: str
) -> dict:
    prompt = f"""以下の相談内容を分析してください。

JSON形式で返してください:
{{
    "speaker_segments": [
        {{"speaker": "counselor", "text": "日本語の発話"}},
        {{"speaker": "customer", "text": "日本語の発話"}}
    ],
    "translated_segments": [
        {{"speaker": "counselor", "text": "한국어 번역"}},
        {{"speaker": "customer", "text": "한국어 번역"}}
    ],
    "customer_utterances": "고객 발화만 추출한 텍스트 (한국어)",
    "cta_level": "hot" or "warm" or "cool",
    "cta_signals": ["根拠となる日本語のお客様発話1", "根拠となる日本語のお客様発話2"]
}}

日本語原文:
{original_text}

韓国語翻訳:
{translated_text}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    data = json.loads(result)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data
