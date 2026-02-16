import json
from services.gemini_client import generate_json

SYSTEM_INSTRUCTION = """あなたはリポートの品質管理レビュアーです。
生成されたリポートを厳しくレビューしてください。

レビュー基準:
1. 7セクションが全て存在するか？
2. 日本語の文法・表現は自然か？
3. 医療情報がRAGデータと整合しているか？
4. 価格・費用情報が含まれていないか？（含まれていたら必ずFail）
5. トーン＆マナーが提案型になっているか？（断定形は NG）
6. 安全フォールバックが適切に使われているか？"""


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

== RAG参考資料 ==
{rag_context if rag_context else "なし"}

== レビュー項目 ==
1. 7セクション全て存在確認
2. 日本語の自然さ
3. 医療情報の正確性
4. 価格・費用情報の有無 (1つでも含まれていたら即Fail)
5. トーン（提案型か？断定型が含まれていないか？）
6. 安全フォールバック

JSON形式で返してください:
{{
    "passed": true または false,
    "score": 0~100,
    "issues": ["問題点1", "問題点2"],
    "suggestions": ["改善提案1", "改善提案2"],
    "feedback": "リポート作成Agentへのフィードバック（改善指示）"
}}"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    return json.loads(result)
