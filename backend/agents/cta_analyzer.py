from services.gemini_client import generate_json, safe_parse_json

SYSTEM_INSTRUCTION_JA = """あなたはCRM分析の専門家です。カウンセリングの対話から以下を分析してください:

1. 話者分離: 相談者(counselor)とお客様(customer)の発話を分離
2. CTA分析: お客様の発話のみを分析して購買意欲レベルを判定

CTA判定基準:
- Hot: 具体的な日程・費用の質問 (例: "7月に可能ですか？", "費用はいくら？", "回復期間は？")
- Warm: 関心はあるが比較・悩み中 (例: "他の病院では〜", "もう少し調べたい", "家族と相談します")
- Cool: 情報探索段階 (例: "ちょっと気になって", "まだ具体的には", "いつか機会があれば")"""

SYSTEM_INSTRUCTION_KO = """당신은 CRM 분석 전문가입니다. 상담 대화에서 다음을 분석해주세요:

1. 화자 분리: 상담사(counselor)와 고객(customer)의 발화를 분리
2. CTA 분석: 고객 발화만 분석하여 구매 의향 레벨 판정

CTA 판정 기준:
- Hot: 구체적인 일정/비용 질문 (예: "7월에 가능한가요?", "비용이 얼마인가요?", "회복 기간은?")
- Warm: 관심 있지만 비교/고민 중 (예: "다른 병원에서는~", "좀 더 알아보고 싶어요", "가족과 상의할게요")
- Cool: 정보 탐색 단계 (예: "좀 궁금해서요", "아직 구체적으로는", "언젠가 기회가 되면")"""


async def analyze_cta(
    original_text: str,
    translated_text: str,
    input_lang: str = "ja",
    pre_extracted_segments: list[dict] | None = None,
    pre_customer_utterances: str | None = None,
) -> dict:
    # 전처리에서 이미 화자 분리가 된 경우 → CTA 분석만 수행
    if pre_extracted_segments and pre_customer_utterances:
        return await _analyze_cta_only(
            pre_extracted_segments, pre_customer_utterances, input_lang
        )

    if input_lang == "ko":
        # 한국어 입력: 한국어 대화를 직접 분석
        prompt = f"""다음 한국어 상담 대화를 분석해주세요.

JSON 형식으로 반환:
{{
    "speaker_segments": [
        {{"speaker": "counselor", "text": "상담사 발화 (한국어)"}},
        {{"speaker": "customer", "text": "고객 발화 (한국어)"}}
    ],
    "translated_segments": [
        {{"speaker": "counselor", "text": "상담사 발화 (한국어)"}},
        {{"speaker": "customer", "text": "고객 발화 (한국어)"}}
    ],
    "customer_utterances": "고객 발화만 추출한 텍스트 (한국어)",
    "cta_level": "hot" or "warm" or "cool",
    "cta_signals": ["근거가 되는 고객 발화1 (한국어)", "근거가 되는 고객 발화2 (한국어)"]
}}

상담 내용 (한국어):
{original_text}"""
        system = SYSTEM_INSTRUCTION_KO
    else:
        # 기존 일본어 입력
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
        system = SYSTEM_INSTRUCTION_JA

    result = await generate_json(prompt, system)
    data = safe_parse_json(result)
    if isinstance(data, list):
        data = data[0] if data else {}
    return data


async def _analyze_cta_only(
    segments: list[dict],
    customer_utterances: str,
    input_lang: str,
) -> dict:
    """전처리에서 화자 분리 완료 → CTA 레벨만 LLM으로 분석."""
    prompt = f"""다음은 의료 상담에서 추출된 고객(환자) 발화 목록입니다.
이 발화들만 분석하여 고객의 구매 의향(CTA) 레벨을 판정해주세요.

CTA 판정 기준:
- Hot: 구체적인 일정/비용 질문 (예: "7월에 가능한가요?", "비용이 얼마?", "회복 기간은?")
- Warm: 관심 있지만 비교/고민 중 (예: "다른 병원에서는~", "좀 더 알아보고", "가족과 상의")
- Cool: 정보 탐색 단계 (예: "좀 궁금해서", "아직 구체적으로는", "언젠가 기회가 되면")

고객 발화:
{customer_utterances}

JSON 형식으로 반환:
{{
    "cta_level": "hot" 또는 "warm" 또는 "cool",
    "cta_signals": ["판단 근거가 되는 고객 발화1", "판단 근거가 되는 고객 발화2"]
}}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION_KO)
    data = safe_parse_json(result)
    if isinstance(data, list):
        data = data[0] if data else {}

    # 전처리에서 추출한 세그먼트 병합
    data["speaker_segments"] = segments
    data["customer_utterances"] = customer_utterances
    if "translated_segments" not in data:
        data["translated_segments"] = segments
    return data
