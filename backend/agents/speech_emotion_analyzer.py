"""음성 감정 분석 에이전트 — Gemini 멀티모달로 음성 파일에서 감정/톤/확신도 분석"""

import asyncio
import json
import logging
import google.generativeai as genai
from config import GEMINI_API_KEY
from services.gemini_client import safe_parse_json

logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """あなたは音声分析の専門家です。医療カウンセリングの音声を分析し、
お客様の感情状態・話し方の特徴を構造化して報告してください。

分析対象:
1. 話し方（ためらい/確信）: 言い淀み、フィラー（えーと、あの）、言い直しの頻度と、断定的・明確な発言のバランス
2. イントネーション（上昇/下降）: 質問調の上昇イントネーションが多いか、断定的な下降調が多いか
3. 話速: 全体的な話速の印象（速い/普通/遅い）、緊張時と安定時の速度変化
4. 沈黙: 長い沈黙（3秒以上）の発生箇所とその文脈的意味（考慮中、不安、不満など）

総合的にお客様の購買意欲（CTA）レベルを音声特徴から判定してください:
- Hot: 確信的な話し方、速いテンポ、具体的質問時の積極的なトーン
- Warm: ためらいと関心が混在、質問は多いがトーンに迷いあり
- Cool: 消極的なトーン、長い沈黙、曖昧な応答が多い"""


async def analyze_speech_emotion(audio_file_path: str) -> dict:
    """음성 파일을 Gemini에 업로드하여 감정/톤 분석 수행.

    Args:
        audio_file_path: 로컬 음성 파일 경로 (m4a/wav/mp3)

    Returns:
        {
            "speech_patterns": { "hesitation_level", "confidence_level", "filler_words", "examples" },
            "intonation": { "dominant_pattern", "question_ratio", "examples" },
            "speech_speed": { "overall", "variation", "details" },
            "silence": { "notable_pauses", "details" },
            "voice_cta": { "level", "confidence_score", "reasoning" },
            "overall_emotion": { "primary_emotion", "secondary_emotion", "emotional_shift" },
            "summary": "..."
        }
    """
    logger.info(f"[SpeechEmotion] Uploading audio file: {audio_file_path}")

    # Gemini Files API에 음성 파일 업로드
    uploaded_file = await asyncio.to_thread(
        genai.upload_file, audio_file_path
    )
    logger.info(f"[SpeechEmotion] File uploaded: {uploaded_file.name}")

    # 파일 처리 완료 대기
    while uploaded_file.state.name == "PROCESSING":
        await asyncio.sleep(2)
        uploaded_file = await asyncio.to_thread(
            genai.get_file, uploaded_file.name
        )

    if uploaded_file.state.name == "FAILED":
        raise ValueError(f"Audio file processing failed: {uploaded_file.state.name}")

    logger.info(f"[SpeechEmotion] File ready, starting analysis")

    prompt = """この音声ファイルを分析し、お客様（患者）の音声特徴を以下のJSON形式で返してください。
カウンセラーと患者の両方が含まれている場合、患者の音声特徴に焦点を当ててください。

{
    "speech_patterns": {
        "hesitation_level": "high / medium / low（ためらいの程度）",
        "confidence_level": "high / medium / low（確信度）",
        "filler_words": ["検出されたフィラーワード（えーと、あの、うーん等）"],
        "filler_count": "フィラーワードの概算回数",
        "examples": [
            {
                "type": "hesitation または confidence",
                "quote": "該当する発話の引用（原文そのまま）",
                "context": "その発話の文脈説明"
            }
        ]
    },
    "intonation": {
        "dominant_pattern": "rising / falling / mixed（主なイントネーションパターン）",
        "question_ratio": "質問調の割合（例: 60%）",
        "examples": [
            {
                "pattern": "rising または falling",
                "quote": "該当する発話",
                "meaning": "そのイントネーションが示す心理状態"
            }
        ]
    },
    "speech_speed": {
        "overall": "fast / normal / slow（全体的な話速）",
        "variation": "significant / moderate / minimal（速度変化の程度）",
        "details": "話速に関する詳細な観察（緊張時の加速、重要な質問時の減速など）"
    },
    "silence": {
        "notable_pauses": [
            {
                "context": "沈黙が発生した文脈",
                "estimated_duration": "推定秒数",
                "interpretation": "沈黙の解釈（考慮中、不安、不満、理解処理中など）"
            }
        ],
        "overall_silence_pattern": "沈黙パターンの全体的な傾向"
    },
    "voice_cta": {
        "level": "hot / warm / cool",
        "confidence_score": 0.0〜1.0,
        "reasoning": "音声特徴に基づくCTA判定の根拠（2〜3文）"
    },
    "overall_emotion": {
        "primary_emotion": "主要な感情（例: 期待、不安、関心、無関心、緊張、安心）",
        "secondary_emotion": "副次的な感情（あれば）",
        "emotional_shift": "会話中の感情変化（例: 不安→関心→期待）"
    },
    "summary": "音声分析の総合要約（3〜4文。テキスト分析では分からない音声固有の洞察を中心に）"
}

重要:
- お客様の発話に焦点を当てること（カウンセラーの発話は背景情報として参考のみ）
- 実際に音声から検出できた特徴のみ記載すること（推測で埋めない）
- quotesは音声から実際に聞き取れた内容をそのまま記載すること"""

    # Gemini 멀티모달 호출
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )

    for attempt in range(3):
        try:
            response = await asyncio.to_thread(
                model.generate_content, [uploaded_file, prompt]
            )
            if response and response.text:
                data = safe_parse_json(response.text)
                if isinstance(data, list):
                    data = data[0] if data else {}
                logger.info(f"[SpeechEmotion] Analysis complete: voice_cta={data.get('voice_cta', {}).get('level', 'N/A')}")

                # 업로드 파일 정리
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception:
                    pass

                return data
        except Exception as e:
            logger.warning(f"[SpeechEmotion] Attempt {attempt + 1}/3 failed: {str(e)[:150]}")
            if attempt < 2:
                await asyncio.sleep(3 * (attempt + 1))
            else:
                # 업로드 파일 정리
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception:
                    pass
                raise

    raise ValueError("Speech emotion analysis failed after 3 attempts")


async def stt_with_emotion(audio_file_path: str) -> dict:
    """음성 파일에서 STT(전사) + 감정 분석을 동시에 수행.

    Returns:
        {
            "transcription": "전사된 텍스트",
            "detected_language": "ja / ko / mixed",
            "emotion_analysis": { ... (analyze_speech_emotion 결과) }
        }
    """
    logger.info(f"[STT+Emotion] Starting combined analysis: {audio_file_path}")

    # Gemini Files API에 음성 파일 업로드
    uploaded_file = await asyncio.to_thread(
        genai.upload_file, audio_file_path
    )

    # 파일 처리 완료 대기
    while uploaded_file.state.name == "PROCESSING":
        await asyncio.sleep(2)
        uploaded_file = await asyncio.to_thread(
            genai.get_file, uploaded_file.name
        )

    if uploaded_file.state.name == "FAILED":
        raise ValueError(f"Audio file processing failed: {uploaded_file.state.name}")

    # STT + 감정 분석 동시 요청
    stt_prompt = """この音声ファイルから以下の2つのタスクを同時に実行してください。

## タスク1: 音声の書き起こし（STT）
音声の内容をそのまま文字に起こしてください。
- 話者が複数いる場合は [カウンセラー] [お客様] のように話者ラベルを付けてください
- 日本語と韓国語が混在する場合はそのまま両方記載してください

## タスク2: 音声感情分析
お客様（患者）の音声特徴を分析してください。

以下のJSON形式で返してください:
{
    "transcription": "書き起こしテキスト全文（話者ラベル付き）",
    "detected_language": "ja（日本語のみ）/ ko（韓国語のみ）/ mixed（混在）",
    "speech_patterns": {
        "hesitation_level": "high / medium / low",
        "confidence_level": "high / medium / low",
        "filler_words": ["えーと", "あの"],
        "filler_count": "概算回数",
        "examples": [
            {"type": "hesitation/confidence", "quote": "発話引用", "context": "文脈"}
        ]
    },
    "intonation": {
        "dominant_pattern": "rising / falling / mixed",
        "question_ratio": "質問調の割合",
        "examples": [
            {"pattern": "rising/falling", "quote": "発話", "meaning": "心理状態"}
        ]
    },
    "speech_speed": {
        "overall": "fast / normal / slow",
        "variation": "significant / moderate / minimal",
        "details": "詳細な観察"
    },
    "silence": {
        "notable_pauses": [
            {"context": "沈黙の文脈", "estimated_duration": "推定秒数", "interpretation": "解釈"}
        ],
        "overall_silence_pattern": "全体的な傾向"
    },
    "voice_cta": {
        "level": "hot / warm / cool",
        "confidence_score": 0.0,
        "reasoning": "判定根拠"
    },
    "overall_emotion": {
        "primary_emotion": "主要な感情",
        "secondary_emotion": "副次的な感情",
        "emotional_shift": "感情変化"
    },
    "summary": "音声分析の総合要約（3〜4文）"
}"""

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        ),
    )

    for attempt in range(3):
        try:
            response = await asyncio.to_thread(
                model.generate_content, [uploaded_file, stt_prompt]
            )
            if response and response.text:
                data = safe_parse_json(response.text)
                if isinstance(data, list):
                    data = data[0] if data else {}

                # emotion_analysis 하위 객체로 정리
                transcription = data.pop("transcription", "")
                detected_language = data.pop("detected_language", "ja")

                result = {
                    "transcription": transcription,
                    "detected_language": detected_language,
                    "emotion_analysis": data,
                }

                logger.info(
                    f"[STT+Emotion] Complete: lang={detected_language}, "
                    f"voice_cta={data.get('voice_cta', {}).get('level', 'N/A')}, "
                    f"transcription_len={len(transcription)}"
                )

                # 업로드 파일 정리
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception:
                    pass

                return result
        except Exception as e:
            logger.warning(f"[STT+Emotion] Attempt {attempt + 1}/3 failed: {str(e)[:150]}")
            if attempt < 2:
                await asyncio.sleep(3 * (attempt + 1))
            else:
                try:
                    await asyncio.to_thread(genai.delete_file, uploaded_file.name)
                except Exception:
                    pass
                raise

    raise ValueError("STT + emotion analysis failed after 3 attempts")
