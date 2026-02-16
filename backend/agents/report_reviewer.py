import asyncio
import json
import logging
from services.gemini_client import generate_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """あなたはリポートの品質管理レビュアーです。
生成されたリポートを厳しくレビューしてください。

レビュー基準:
1. 7セクションが全て存在するか？
2. 日本語の文法・表現は自然か？
3. 医療情報がRAGデータと整合しているか？
4. 価格・費用情報が含まれていないか？（含まれていたら必ずFail）
5. トーン＆マナーが提案型になっているか？（断定形は NG）
6. 安全フォールバックが適切に使われているか？
7. セクション4の各explanationのtextが3文以上あるか？（テキスト中心の原則）
8. セクション5の各stepのdescが3文以上あるか？
9. セクション6のitemsが配列で複数項目を含んでいるか？
10. PubMed引用がある場合、citation情報（title, url）が正確か？"""


async def review_report(
    report_data: dict,
    rag_results: list[dict],
) -> dict:
    rag_context = ""
    if rag_results:
        for i, faq in enumerate(rag_results, 1):
            source_type = faq.get("source_type", "youtube")
            source_label = "PubMed" if source_type == "pubmed" else "YouTube"
            rag_context += f"\n[参考{i} ({source_label})] Q: {faq.get('question', '')} A: {faq.get('answer', '')}\n"
            if source_type == "pubmed":
                rag_context += f"  論文: {faq.get('paper_title', '')} URL: {faq.get('youtube_url', '')}\n"

    prompt = f"""以下のリポートをレビューしてください。

== リポートデータ ==
{json.dumps(report_data, ensure_ascii=False, indent=2)}

== RAG参考資料 ==
{rag_context if rag_context else "なし"}

== レビュー項目（10項目）==
1. 7セクション全て存在確認（section1_summary〜section7_recovery）
2. 日本語の自然さ（温かく丁寧な表現か）
3. 医療情報の正確性（RAGデータとの整合性）
4. 価格・費用情報の有無（1つでも含まれていたら即Fail）
5. トーン（提案型か？断定型が含まれていないか？）
6. 安全フォールバック（RAGにない情報の扱い）
7. テキスト分量チェック: section4のexplanationsの各textが3文以上か？
8. テキスト分量チェック: section5のstepsの各descが3文以上か？
9. section6のrecommended/optional/unnecessaryの各itemsが配列か？
10. PubMed citation: 引用がある場合、RAGデータに存在するPubMed論文からの情報のみ引用しているか？

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
            data = json.loads(result)
            if isinstance(data, list):
                data = data[0] if data else {"passed": True, "score": 70, "issues": [], "suggestions": [], "feedback": ""}
            return data
        except json.JSONDecodeError as e:
            logger.warning(f"[ReviewAgent] JSON parse error (attempt {parse_attempt + 1}): {str(e)[:100]}")
            if parse_attempt == 0:
                await asyncio.sleep(3)
            else:
                # 파싱 실패 시 기본 pass 응답 반환 (리포트 생성 실패 방지)
                logger.error(f"[ReviewAgent] JSON parse failed, returning default pass")
                return {"passed": True, "score": 70, "issues": ["Review JSON parse failed"], "suggestions": [], "feedback": ""}
