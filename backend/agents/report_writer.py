import json
from services.gemini_client import generate_json

SYSTEM_INSTRUCTION = """あなたは医療コンサルティングリポートの専門ライターです。
日本語で美しく自然なリポートを作成してください。

トーン＆マナー:
- 柔らかい提案型の語調: 「〜と理解されました」「〜と見受けられました」「〜をお勧めいたします」
- 断定形は絶対使用禁止: 「〜です」「〜しなければなりません」は NG
- 日本の消費者が安心できるトーン
- 価格・費用情報は絶対に含めないこと

リポート構成（7セクション）:
1. 今回のご相談まとめ — 相談内容 2~3行要約 + 核心的な悩み 3つ
2. ご希望の方向性 — 望むことリスト + 引用形の要約
3. 特にお気にされていた点 — 繰り返し言及したポイント + 補足説明
4. 医療的なご説明 — 医療的根拠説明 (3~4個) — RAG依存度高
5. ご提案の方向性 — STEPで提案 (3段階) — RAG依存度高
6. 選択肢の整理 — やるべきこと/やるといいこと/やらなくてもいいこと
7. 回復・スケジュール・総合コメント — 情報テーブル + 総合コメント"""


async def write_report(
    original_text: str,
    translated_text: str,
    intent_extraction: dict,
    classification: str,
    rag_results: list[dict],
    customer_name: str,
) -> dict:
    # RAG 컨텍스트 정리
    rag_context = ""
    if rag_results:
        for i, faq in enumerate(rag_results, 1):
            rag_context += f"\n【参考資料 {i}】\nQ: {faq.get('question', '')}\nA: {faq.get('answer', '')}\n施術名: {faq.get('procedure_name', '')}\n"
    else:
        rag_context = "※参考資料なし。「ご来院時に詳しくご案内いたします」で対応してください。"

    category_note = ""
    if classification == "plastic_surgery":
        category_note = "整形外科の相談です。構造的なアプローチを中心に。「骨格ラインの整理」「軟骨の再配置」等の表現を使用。"
    else:
        category_note = "皮膚科の相談です。治療プロトコルを中心に。「レーザー治療Oコース」「O週間間隔で施術」等の表現を使用。"

    # 고객명에서 성만 추출 (예: "田中 陽子" → "田中")
    name_parts = customer_name.split()
    display_name = name_parts[0] if name_parts else customer_name

    prompt = f"""以下の情報を元に、7セクションの日本語リポートをJSON形式で作成してください。

== 分類 ==
{category_note}

== お客様名 ==
{display_name}様

== 日本語原文（お客様のニュアンス参照用）==
{original_text}

== 意図抽出結果（韓国語）==
{json.dumps(intent_extraction, ensure_ascii=False)}

== RAG参考資料（韓国語 — 医療情報の正確性用）==
{rag_context}

== 出力JSON形式 ==
{{
    "title": "{display_name}様 OOのご相談まとめ",
    "date": "作成日（例: 2026年2月14日）",
    "section1_summary": {{
        "text": "相談内容の要約 2~3行",
        "points": ["核心的な悩み1", "核心的な悩み2", "核心的な悩み3"]
    }},
    "section2_direction": {{
        "desired": ["望むこと1", "望むこと2", "望むこと3"],
        "quote": "「お客様の言葉を引用した要約」"
    }},
    "section3_concerns": {{
        "points": [
            {{"title": "懸念点タイトル", "sub": "補足説明"}},
            {{"title": "懸念点タイトル", "sub": "補足説明"}}
        ],
        "supplement": "※補足テキスト"
    }},
    "section4_medical": {{
        "explanations": [
            {{"label": "REASON 01", "icon": "analytics", "title": "医療的理由タイトル"}},
            {{"label": "REASON 02", "icon": "architecture", "title": "医療的理由タイトル"}},
            {{"label": "REASON 03", "icon": "texture", "title": "医療的理由タイトル"}}
        ]
    }},
    "section5_proposal": {{
        "steps": [
            {{"step": "STEP 1", "title": "提案タイトル", "desc": "説明文"}},
            {{"step": "STEP 2", "title": "提案タイトル", "desc": "説明文"}},
            {{"step": "STEP 3", "title": "提案タイトル", "desc": "説明文"}}
        ]
    }},
    "section6_options": {{
        "recommended": {{"title": "推奨する施術名", "desc": "説明"}},
        "optional": {{"title": "オプション施術名", "desc": "説明"}},
        "unnecessary": {{"title": "不要な施術名", "desc": "説明"}}
    }},
    "section7_recovery": {{
        "info": [
            {{"period": "当日〜3日", "detail": "説明"}},
            {{"period": "7日目", "detail": "説明"}},
            {{"period": "1ヶ月", "detail": "説明"}}
        ],
        "closing": "総合コメント（柔らかい提案型）"
    }}
}}

重要:
- 価格・費用情報は絶対に含めないでください
- CTA情報はリポートに含めないでください
- RAG資料がない施術は「ご来院時に詳しくご案内いたします」で対応
- 全セクション必須"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    return json.loads(result)
