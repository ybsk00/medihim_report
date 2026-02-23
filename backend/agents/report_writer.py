import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from services.gemini_client import generate_json, safe_parse_json

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """あなたは医療コンサルティングリポートの専門ライターです。
日本語で丁寧かつ温かみのあるリポートを作成してください。

トーン＆マナー:
- 柔らかい提案型の語調: 「〜と理解されました」「〜と見受けられました」「〜をお勧めいたします」
- 温かく安心感のある表現: 「ご安心いただければと存じます」「一緒に最適な方法を見つけてまいりましょう」
- 各項目は2〜4文で十分な説明を含めること（短すぎる記述は避ける）
- セクション間で内容の重複・繰り返しを避ける
- 価格・費用情報: 相談中に具体的な金額が言及された場合のみ、その内容をそのまま記載する。言及がなければ費用セクションを空にする。絶対にAIが費用を推測・創作してはならない。

医療情報の原則:
- カウンセラー/医師が相談で実際に言及した内容のみを記載する
- 相談で言及されていない医療情報は記載しない（信頼低下の原因）
- 医師の発言に反する内容は絶対に記載しない
- RAG資料は内容検証用として参照するが、リポートに直接引用しない
- PubMed論文の詳細引用（citation）は不要

リポート構成（10セクション）:
1. ご相談の要点 — 核心的な悩み・希望・懸念を丁寧に整理（各2〜3文で説明）
2. 現在の状態と原因 — 悩みの原因を丁寧に分析（導入2〜3文 + 原因リスト各2文 + 結論2文）
3. ご提案（Recommended Plan）— 1次推奨 + 必要時併用の構造で提案を丁寧に説明
4. 予想回復スケジュール — タイムライン表 + 補足（各段階を丁寧に説明）
5. 傷跡について — 各項目2〜3文で丁寧に説明
6. 施術前の注意事項 — 各項目2〜3文で丁寧に説明
7. リスクまとめ — 各項目2〜3文で丁寧に説明
8. 予想費用範囲 — 相談中に言及された金額のみ記載（言及なければ空配列）。AIが金額を創作してはならない
9. ご来院予定日 — 相談で言及された日付。なければ「未定」と記載
10. IPPEOからの一言 + 最終整理 — 温かく前向きな行動誘導メッセージ（各3〜4文で丁寧に）"""


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
各項目は2〜4文で十分な説明を含め、温かく丁寧なトーンで記述してください。
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
            "核心的な悩み（2〜3文で丁寧に説明。お客様の状況と背景も含めて温かく記述）",
            "希望する方向性（2〜3文で丁寧に説明。お客様がどのような結果を望んでいるか具体的に）",
            "主要な懸念事項（2〜3文で丁寧に説明。なぜ不安を感じているかの背景も含めて）",
            "改善の可能性の要約（2〜3文で丁寧に説明。前向きで安心感のあるメッセージ）"
        ]
    }},

    "section2_cause_analysis": {{
        "intro": "悩みの原因を要約する導入文（2〜3文。お客様の状態を温かく整理する）",
        "causes": [
            "原因1（2文で丁寧に説明。医学的な背景をわかりやすく）",
            "原因2（2文で丁寧に説明）",
            "原因3（2文で丁寧に説明）"
        ],
        "conclusion": "核心整理（2文で丁寧に。今後の方向性につながる温かいまとめ）"
    }},

    "section3_recommendation": {{
        "primary": {{
            "label": "1次推奨",
            "items": [
                "推奨する施術・アプローチ1（2〜3文で丁寧に説明。なぜこの方法が適しているか根拠も含めて）",
                "推奨2（2〜3文で丁寧に説明）",
                "推奨3（2〜3文で丁寧に説明）"
            ]
        }},
        "secondary": {{
            "label": "必要時併用",
            "items": [
                "追加施術1（2〜3文で丁寧に説明。どのような場合に検討するか）"
            ]
        }},
        "goal": "目標の要約（2〜3文。お客様の理想に寄り添った温かい表現で）"
    }},

    "section4_recovery": {{
        "timeline": [
            {{"period": "1〜3日", "detail": "回復状態の詳しい説明（2〜3文。この時期に注意すべきことも含めて丁寧に）"}},
            {{"period": "7日", "detail": "回復状態の詳しい説明（2〜3文）"}},
            {{"period": "2〜4週", "detail": "回復状態の詳しい説明（2〜3文）"}},
            {{"period": "1〜3ヶ月", "detail": "回復状態の詳しい説明（2〜3文）"}}
        ],
        "note": "スケジュールに関する補足（相談で言及があった場合のみ。なければnull）"
    }},

    "section5_scar_info": {{
        "points": [
            "傷跡に関する情報1（2〜3文で丁寧に説明。安心感のある表現で）",
            "傷跡に関する情報2（2〜3文で丁寧に説明）",
            "傷跡に関する情報3（2〜3文で丁寧に説明）"
        ]
    }},

    "section6_precautions": {{
        "points": [
            "施術前注意事項1（2〜3文で丁寧に説明。なぜ重要かも含めて）",
            "施術前注意事項2（2〜3文で丁寧に説明）",
            "施術前注意事項3（2〜3文で丁寧に説明）"
        ]
    }},

    "section7_risks": {{
        "points": [
            "リスク1（2〜3文で丁寧に説明。対処法や発生頻度も含めて安心感のある表現で）",
            "リスク2（2〜3文で丁寧に説明）",
            "リスク3（2〜3文で丁寧に説明）",
            "リスク4（2〜3文で丁寧に説明）"
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
            "【ハードル低減】この相談の具体的な施術内容に触れながら、大げさなことではないと温かく伝える2〜3文。お客様の悩みに合わせた独自の表現で、安心感を与えてください。",
            "【未来イメージ】お客様が相談で語った具体的な悩み・希望を踏まえて、施術後の日常の一場面を丁寧に描写する2〜3文。相談内容にない場面（旅行等）は使わないこと。",
            "【感情報酬】お客様の具体的な悩みが解消された時の心理的な満足感を2〜3文で丁寧に。相談内容に基づいた固有の表現で温かく。",
            "【安心感】お客様のペースで検討できることを温かく伝える2〜3文。寄り添う姿勢を示してください。",
            "【行動促進】相談内容から読み取れるお客様の意欲度に合わせた、次のステップへの自然で温かい誘導2〜3文。"
        ],
        "final_summary": "最終整理（3〜4文。お客様の目標 + 推奨方向 + スケジュール提案を温かく丁寧に）"
    }}
}}

重要ルール:
- section8_cost_estimate: 相談中にカウンセラーが具体的な金額を言及した場合のみ記載すること。AIが費用を推測・創作することは絶対禁止。言及がなければitemsは空配列[]にすること
- section1〜4は相談で言及された内容のみに基づくこと
- section5（傷跡）・section6（注意事項）・section7（リスク）は、相談で言及がなくても該当施術の一般的な医学情報を記載すること（空にしない）
- PubMed論文の引用（citation）は含めないこと
- 各項目は2〜4文で十分な説明を含めること（短すぎる記述は避ける）
- セクション間の重複・繰り返しを排除すること
- section9_visit_date: 相談で日付が言及されていなければdateは「未定」と記載すること
- pointsの配列に空文字列("")を入れないこと。内容がある項目のみ含めること
- 全10セクション必須
- section10_ippeo_message: 各paragraphは必ずこのお客様の相談内容に固有の表現で作成すること。テンプレート的な汎用文の使い回しは禁止。お客様が相談で述べた具体的な悩み・希望・施術名に言及して、この方だけに向けた温かいメッセージにすること
- 全体を通して、お客様が読んで安心できる温かいトーンを保つこと"""

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
