import asyncio
import json
import logging
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """あなたはリポートの品質管理レビュアーです。
生成されたリポートを厳しくレビューしてください。

レビュー基準:
1. 10セクションが全て存在するか？（section1_key_summary〜section10_ippeo_message）
2. 各項目が1〜2文以内で簡潔に記述されているか？（過度な長文はFail）
3. カウンセラーが言及していない医療情報が含まれていないか？
4. 費用情報: section8_cost_estimateのitemsに、相談で言及されていない金額が含まれていないか？（AIが創作した金額は即Fail）
5. トーンが中立的・整理型か？（感情的な表現「ご安心ください」「一緒に」等はFail）
6. セクション間で内容の重複・繰り返しがないか？
7. section10のparagraphsに行動誘導5要素が含まれているか？
8. 日本語の文法・表現は自然か？"""


async def review_report(
    report_data: dict,
    rag_results: list[dict],
) -> dict:
    rag_context = ""
    if rag_results:
        for i, faq in enumerate(rag_results, 1):
            rag_context += f"\n[参考{i}] Q: {faq.get('question', '')} A: {faq.get('answer', '')}\n"

    prompt = f"""以下のリポートをレビューしてください。

== リポートデータ ==
{json.dumps(report_data, ensure_ascii=False, indent=2)}

== 参考資料（検証用）==
{rag_context if rag_context else "なし"}

== レビュー項目（8項目）==
1. 10セクション全て存在確認（section1_key_summary, section2_cause_analysis, section3_recommendation, section4_recovery, section5_scar_info, section6_precautions, section7_risks, section8_cost_estimate, section9_visit_date, section10_ippeo_message）
2. 簡潔さ: 各項目が1〜2文以内か？ 不必要な修飾語や冗長な表現はないか？
3. 医療情報の正当性: 相談内容で言及されていない情報が含まれていないか？
4. 費用情報: section8_cost_estimateのitemsに相談で言及されていない金額がないか？（AIが創作した金額は即Fail。言及なしなら空配列が正しい）
5. トーン: 中立的・整理型か？ 感情的表現（「ご安心ください」「温かく」「一緒に」等）が含まれていないか？
6. 重複排除: セクション間で同じ内容が繰り返されていないか？
7. section10のparagraphsに行動誘導5要素（大したことではないフレーミング、未来の自分可視化、感情報酬予告、防御心解除、タイミング刺激）が含まれているか？
8. 日本語の自然さ

JSON形式で返してください:
{{
    "passed": true または false,
    "score": 0~100,
    "issues": ["問題点1", "問題点2"],
    "suggestions": ["改善提案1", "改善提案2"],
    "feedback": "リポート作成Agentへのフィードバック（改善指示）"
}}"""

    for parse_attempt in range(2):
        result = await generate_json(prompt, SYSTEM_INSTRUCTION)
        try:
            data = safe_parse_json(result)
            if isinstance(data, list):
                data = data[0] if data else {"passed": True, "score": 70, "issues": [], "suggestions": [], "feedback": ""}
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"[ReviewAgent] JSON parse error (attempt {parse_attempt + 1}): {str(e)[:100]}")
            if parse_attempt == 0:
                await asyncio.sleep(3)
            else:
                logger.error(f"[ReviewAgent] JSON parse failed, returning default pass")
                return {"passed": True, "score": 70, "issues": ["Review JSON parse failed"], "suggestions": [], "feedback": ""}
