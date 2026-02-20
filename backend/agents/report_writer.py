import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """あなたは医療コンサルティングリポートの専門ライターです。
日本語で簡潔かつ中立的なリポートを作成してください。

トーン＆マナー:
- 中立的・整理型の語調を使用する
- 「〜です」「〜と判断されます」「〜が推奨されます」など簡潔な表現
- 感情的・過度に温かい表現は使用しない（「ご安心ください」「一緒に見つけましょう」等はNG）
- 各項目は1〜2文以内で簡潔に記述する
- セクション間で内容の重複・繰り返しを絶対に避ける
- 価格・費用情報: 相談中に具体的な金額が言及された場合のみ、その内容をそのまま記載する。言及がなければ費用セクションを空にする。絶対にAIが費用を推測・創作してはならない。

医療情報の原則:
- カウンセラー/医師が相談で実際に言及した内容のみを記載する
- 相談で言及されていない医療情報は記載しない（信頼低下の原因）
- 医師の発言に反する内容は絶対に記載しない
- RAG資料は内容検証用として参照するが、リポートに直接引用しない
- PubMed論文の詳細引用（citation）は不要

リポート構成（9セクション）:
1. ご相談の要点 — 核心的な悩み・希望・懸念をブレットポイントのみで整理（4項目以内）
2. 現在の状態と原因 — 悩みの原因を簡潔に分析（導入1文 + 原因リスト + 結論1文）
3. ご提案（Recommended Plan）— 1次推奨 + 必要時併用の構造で提案を先に、根拠を後に
4. 予想回復スケジュール — 簡潔なタイムライン表 + 補足（相談で言及された内容のみ）
5. 傷跡について — ブレットポイント（3項目以内）
6. 施術前の注意事項 — ブレットポイント（3項目以内）
7. リスクまとめ — ブレットポイント（4項目以内）
8. 予想費用範囲 — 相談中に言及された金額のみ記載（言及なければ空配列）。AIが金額を創作してはならない
9. ご来院予定日 — 相談で言及された日付。なければ「未定」と記載
10. IPPEOからの一言 + 最終整理 — 行動誘導型CTA（5つの心理要素を含む）"""


async def write_report(
    original_text: str,
    translated_text: str,
    intent_extraction: dict,
    classification: str,
    rag_results: list[dict],
    customer_name: str,
    admin_direction: str | None = None,
    input_lang: str = "ja",
) -> dict:
    # RAG 컨텍스트를 정리 (내용 검증용)
    rag_context = ""
    if rag_results:
        for i, faq in enumerate(rag_results, 1):
            rag_context += f"\n【参考資料 {i}】\nQ: {faq.get('question', '')}\nA: {faq.get('answer', '')}\n施術名: {faq.get('procedure_name', '')}\n"

    if not rag_context:
        rag_context = "※参考資料なし。相談内容のみに基づいて作成してください。"

    category_note = ""
    if classification == "plastic_surgery":
        category_note = "整形外科の相談です。構造的なアプローチを中心に記述してください。"
    else:
        category_note = "皮膚科の相談です。治療プロトコルを中心に記述してください。"

    # 관리자 재생성 지시 섹션 (있을 때만)
    admin_direction_section = ""
    if admin_direction:
        admin_direction_section = f"""
== 管理者からの修正指示（最優先で反映すること）==
{admin_direction}

上記の管理者指示を最優先で反映してください。
"""

    # 고객명에서 성만 추출 (예: "田中 陽子" → "田中")
    name_parts = customer_name.split()
    display_name = name_parts[0] if name_parts else customer_name

    # 입력 언어에 따라 상담 원문 섹션 구성
    if input_lang == "ko":
        consultation_section = f"""== 韓国語原文（相談内容）==
{original_text}"""
    else:
        consultation_section = f"""== 日本語原文（相談内容）==
{original_text}

== 韓国語翻訳（意味確認用）==
{translated_text}"""

    prompt = f"""以下の情報を元に、10セクションの日本語リポートをJSON形式で作成してください。
各項目は簡潔に1〜2文以内で記述し、セクション間の重複を排除してください。
カウンセラーが相談で実際に言及した内容のみを記載してください。

== 分類 ==
{category_note}

== お客様名 ==
{display_name}様

{consultation_section}

== 意図抽出結果 ==
{json.dumps(intent_extraction, ensure_ascii=False)}

== 参考資料（内容検証用、直接引用しない）==
{rag_context}
{admin_direction_section}
== 出力JSON形式 ==
{{
    "title": "{display_name}様 OOのご相談リポート",
    "date": "作成日：YYYY年M月D日",

    "section1_key_summary": {{
        "points": [
            "核心的な悩み（1文で簡潔に）",
            "希望する方向性（1文で簡潔に）",
            "主要な懸念事項（1文で簡潔に）",
            "改善の可能性の要約（1文で簡潔に）"
        ]
    }},

    "section2_cause_analysis": {{
        "intro": "悩みの原因を要約する1文（例: OOが△△に見える原因は以下の通りです。）",
        "causes": [
            "原因1（簡潔に1文）",
            "原因2（簡潔に1文）",
            "原因3（簡潔に1文）"
        ],
        "conclusion": "核心整理1文（例: 単純なXXではなく、YYがポイントです。）"
    }},

    "section3_recommendation": {{
        "primary": {{
            "label": "1次推奨",
            "items": [
                "推奨する施術・アプローチ1（簡潔に）",
                "推奨2（簡潔に）",
                "推奨3（簡潔に）"
            ]
        }},
        "secondary": {{
            "label": "必要時併用",
            "items": [
                "追加施術1（簡潔に）"
            ]
        }},
        "goal": "目標の要約1文（例: 自然でありながら整った印象を目指します。）"
    }},

    "section4_recovery": {{
        "timeline": [
            {{"period": "1〜3日", "detail": "簡潔な状態説明（1文）"}},
            {{"period": "7日", "detail": "簡潔な状態説明（1文）"}},
            {{"period": "2〜4週", "detail": "簡潔な状態説明（1文）"}},
            {{"period": "1〜3ヶ月", "detail": "簡潔な状態説明（1文）"}}
        ],
        "note": "スケジュールに関する補足（相談で言及があった場合のみ。なければnull）"
    }},

    "section5_scar_info": {{
        "points": [
            "傷跡に関する情報1（1文）",
            "傷跡に関する情報2（1文）",
            "傷跡に関する情報3（1文）"
        ]
    }},

    "section6_precautions": {{
        "points": [
            "施術前注意事項1（1文）",
            "施術前注意事項2（1文）",
            "施術前注意事項3（1文）"
        ]
    }},

    "section7_risks": {{
        "points": [
            "リスク1（簡潔に）",
            "リスク2（簡潔に）",
            "リスク3（簡潔に）",
            "リスク4（簡潔に）"
        ]
    }},

    "section8_cost_estimate": {{
        "items": [
            "相談中に言及された費用情報1（例: 鼻尖形成術 単独: 約OOO〜OOO万ウォン）",
            "相談中に言及された費用情報2（例: 併用時: 追加費用発生）"
        ],
        "includes": "含まれる項目（例: 麻酔/検査費。言及がなければnull）",
        "note": "費用に関する補足（例: 正確なお見積もりは診察後にご案内。言及がなければnull）"
    }},

    "section9_visit_date": {{
        "date": "YYYY.MM.DD（相談で言及された来院予定日。なければ「未定」と記載）",
        "note": "補足説明（なければnull）"
    }},

    "section10_ippeo_message": {{
        "paragraphs": [
            "大したことではないフレーミング（例: 今回の改善は新しい顔を作るのではなく、すでにお持ちの魅力を少し整える過程に近いです。）",
            "未来の自分の可視化（例: 旅行で写真を撮る時、今より少し整った印象で自信を持って笑っている姿を想像してみてください。）",
            "感情報酬の予告（例: 鏡を見るたびに「よかった」と思える変化なら、そのワクワク感は十分に始めてみる価値があります。）",
            "防御心の解除（例: 急いで決める必要はありません。）",
            "さりげないタイミング刺激（例: ただ、すでに心の中で方向が決まっているなら、その変化に少し早く会ってみるのも良いかもしれません。）"
        ],
        "final_summary": "最終整理（2文以内。お客様の目標 + 推奨方向 + スケジュール提案を簡潔に）"
    }}
}}

重要ルール:
- section8_cost_estimate: 相談中にカウンセラーが具体的な金額を言及した場合のみ記載すること。AIが費用を推測・創作することは絶対禁止。言及がなければitemsは空配列[]にすること
- section1〜4は相談で言及された内容のみに基づくこと
- section5（傷跡）・section6（注意事項）・section7（リスク）は、相談で言及がなくても該当施術の一般的な医学情報を記載すること（空にしない）
- PubMed論文の引用（citation）は含めないこと
- 各項目は1〜2文以内で簡潔に
- セクション間の重複・繰り返しを排除すること
- section9_visit_date: 相談で日付が言及されていなければdateは「未定」と記載すること
- pointsの配列に空文字列("")を入れないこと。内容がある項目のみ含めること
- 全10セクション必須"""

    # JSON 파싱 재시도 (최대 2회)
    report = None
    for parse_attempt in range(2):
        result = await generate_json(prompt, SYSTEM_INSTRUCTION)
        try:
            report = safe_parse_json(result)
            if isinstance(report, list):
                report = report[0] if report else {}
            break
        except json.JSONDecodeError as e:
            logger.warning(f"[ReportWriter] JSON parse error (attempt {parse_attempt + 1}): {str(e)[:100]}")
            if parse_attempt == 0:
                await asyncio.sleep(3)
            else:
                raise ValueError(f"Report JSON parse failed after 2 attempts: {str(e)}")

    # 리포트 작성일을 현재 일본 시간(JST) 기준으로 확정
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    report["date"] = f"作成日：{now_jst.year}年{now_jst.month}月{now_jst.day}日"

    return report
