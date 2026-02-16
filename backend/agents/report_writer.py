import json
from services.gemini_client import generate_json

SYSTEM_INSTRUCTION = """あなたは医療コンサルティングリポートの専門ライターです。
日本語で丁寧かつ温かみのあるリポートを作成してください。

トーン＆マナー:
- 柔らかい提案型の語調: 「〜と理解されました」「〜と見受けられました」「〜をお勧めいたします」
- 温かく安心感のある表現: 「ご安心いただければと存じます」「一緒に最適な方法を見つけてまいりましょう」
- 断定形は絶対使用禁止: 「〜です」「〜しなければなりません」は NG
- 日本の消費者が安心できるトーン
- 価格・費用情報は絶対に含めないこと

テキスト中心の原則:
- 各セクションに十分な説明テキストを含める（アイコンや図表よりもテキストで丁寧に説明）
- セクション4の各説明は3〜5文で記述する
- セクション5の各ステップの説明は3〜5文で記述する
- PubMed論文の統計・数値を引用する場合は、必ずcitationフィールドに論文情報を含める
- YouTube/一般的な医療知識に基づくテキストには出典不要

リポート構成（7セクション）:
1. 今回のご相談まとめ — 相談内容4~6文の要約テキスト + 核心的な悩み3つ
2. ご希望の方向性 — 希望事項リスト(詳細説明付き) + 結論 + 解釈
3. 特にお気にされていた点 — 懸念点(各2~3文の説明) + 総合的な解釈
4. 医療的なご説明 — 番号付き医療根拠説明(各3~5文) + PubMed引用(あれば) + 注釈
5. ご提案の方向性 — ステップ形式の提案(各3~5文) + 補足説明
6. 選択肢の整理 — カテゴリ別の複数項目リスト + 総合コメント
7. 回復・スケジュール・総合コメント — 情報テーブル + 締めくくり + やさしいメッセージ"""


async def write_report(
    original_text: str,
    translated_text: str,
    intent_extraction: dict,
    classification: str,
    rag_results: list[dict],
    customer_name: str,
) -> dict:
    # RAG 컨텍스트를 PubMed/YouTube 분리하여 정리
    pubmed_context = ""
    youtube_context = ""
    pubmed_count = 0
    youtube_count = 0

    if rag_results:
        for faq in rag_results:
            source_type = faq.get("source_type", "youtube")
            if source_type == "pubmed":
                pubmed_count += 1
                paper_title = faq.get("paper_title", "")
                pmid = faq.get("pmid", "")
                url = faq.get("youtube_url", "")
                pubmed_context += f"\n【PubMed論文 {pubmed_count}】\n論文タイトル: {paper_title}\nPMID: {pmid}\nURL: {url}\nQ: {faq.get('question', '')}\nA: {faq.get('answer', '')}\n施術名: {faq.get('procedure_name', '')}\n"
            else:
                youtube_count += 1
                youtube_context += f"\n【医療情報 {youtube_count}】\nQ: {faq.get('question', '')}\nA: {faq.get('answer', '')}\n施術名: {faq.get('procedure_name', '')}\n"

    if not pubmed_context and not youtube_context:
        pubmed_context = "※PubMed論文参考資料なし"
        youtube_context = "※YouTube参考資料なし。「ご来院時に詳しくご案内いたします」で対応してください。"

    category_note = ""
    if classification == "plastic_surgery":
        category_note = "整形外科の相談です。構造的なアプローチを中心に記述してください。「骨格ラインの整理」「軟骨の再配置」等の専門的かつ分かりやすい表現を使用。"
    else:
        category_note = "皮膚科の相談です。治療プロトコルを中心に記述してください。「レーザー治療Oコース」「O週間間隔で施術」等の具体的な治療計画表現を使用。"

    # 고객명에서 성만 추출 (예: "田中 陽子" → "田中")
    name_parts = customer_name.split()
    display_name = name_parts[0] if name_parts else customer_name

    prompt = f"""以下の情報を元に、7セクションの日本語リポートをJSON形式で作成してください。
テキスト中心で丁寧に記述してください。各セクションの説明文は十分な長さで、温かみのあるトーンを心がけてください。

== 分類 ==
{category_note}

== お客様名 ==
{display_name}様

== 日本語原文（お客様のニュアンス参照用）==
{original_text}

== 意図抽出結果（韓国語）==
{json.dumps(intent_extraction, ensure_ascii=False)}

== PubMed論文参考資料（統計・数値引用時は必ずcitationを付ける）==
{pubmed_context}

== 医療情報参考資料（出典表記不要）==
{youtube_context}

== 出力JSON形式 ==
{{
    "title": "{display_name}様 OOのご相談まとめ",
    "date": "作成日（例: 2026年2月15日）",
    "section1_summary": {{
        "text": "相談内容の要約（4~6文の丁寧なテキスト。お客様の状況と悩みを温かく整理する。）",
        "points": ["核心的な悩み1", "核心的な悩み2", "核心的な悩み3"]
    }},
    "section2_direction": {{
        "items": [
            {{
                "text": "望むこと1（簡潔な見出し）",
                "detail": "具体的な説明（1~2文。お客様がどのような結果を期待されているか丁寧に記述）"
            }},
            {{
                "text": "望むこと2",
                "detail": "具体的な説明"
            }}
        ],
        "conclusion": "上記の希望を総合した結論（2~3文）",
        "interpretation": "医療的観点からの解釈（2~3文。お客様の希望をどう実現できるか）"
    }},
    "section3_concerns": {{
        "points": [
            {{
                "title": "懸念点タイトル",
                "description": "詳しい説明（2~3文。お客様がなぜこの点を気にされているのか、その背景も含めて丁寧に記述）"
            }}
        ],
        "interpretation": "懸念点に対する総合的な解釈と安心メッセージ（2~3文）"
    }},
    "section4_medical": {{
        "explanations": [
            {{
                "number": 1,
                "title": "医療的説明のタイトル",
                "text": "詳細な医療的説明（3~5文。なぜそのような状態になるのか、医学的な根拠を分かりやすく丁寧に説明する。）",
                "citation": {{
                    "title": "PubMed論文タイトル（PubMed統計/数値を引用した場合のみ。なければcitationフィールド自体を省略）",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/PMID/",
                    "stat": "引用した具体的統計（例: 満足度92.3%）"
                }}
            }},
            {{
                "number": 2,
                "title": "医療的説明のタイトル2",
                "text": "詳細な医療的説明（3~5文）"
            }}
        ],
        "footnote": "※上記は一般的な医療情報であり... 安心していただくための注釈文"
    }},
    "section5_proposal": {{
        "steps": [
            {{
                "step": "STEP 1",
                "title": "提案タイトル",
                "desc": "詳細な提案説明（3~5文。具体的にどのようなアプローチで進めるか丁寧に説明する。）"
            }},
            {{
                "step": "STEP 2",
                "title": "提案タイトル",
                "desc": "詳細な提案説明（3~5文）"
            }},
            {{
                "step": "STEP 3",
                "title": "提案タイトル",
                "desc": "詳細な提案説明（3~5文）"
            }}
        ],
        "context_note": "全体的な提案の補足説明（1~2文。提案全体の意図を温かく伝える）"
    }},
    "section6_options": {{
        "recommended": {{
            "category_label": "おすすめの施術",
            "items": [
                "推奨施術/方法1の名前と簡単な説明",
                "推奨施術/方法2の名前と簡単な説明"
            ]
        }},
        "optional": {{
            "category_label": "ご検討いただける選択肢",
            "items": [
                "オプション施術1の名前と簡単な説明"
            ]
        }},
        "unnecessary": {{
            "category_label": "今回は見送っても良い選択肢",
            "items": [
                "不要な施術1の名前と理由"
            ]
        }},
        "comment": "選択肢全体に対する総合コメント（2~3文。最終的な判断はお客様と医師でとの温かいメッセージ）"
    }},
    "section7_recovery": {{
        "info": [
            {{"period": "当日〜3日", "detail": "回復状態の詳しい説明"}},
            {{"period": "7日目", "detail": "回復状態の詳しい説明"}},
            {{"period": "2〜4週間", "detail": "回復状態の詳しい説明"}},
            {{"period": "1〜3ヶ月", "detail": "回復状態の詳しい説明"}}
        ],
        "closing": "総合的な締めくくりコメント（3~4文。温かく前向きなメッセージ）",
        "gentle_note": "最後の一言（1~2文。「いつでもお気軽にご相談ください」のような温かいメッセージ）"
    }}
}}

重要ルール:
- 価格・費用情報は絶対に含めないでください
- CTA情報はリポートに含めないでください
- RAG資料がない施術は「ご来院時に詳しくご案内いたします」で対応
- 全セクション必須
- PubMed論文の統計/数値を引用する場合のみ citation フィールドを追加（統計がない一般説明にはcitation不要）
- YouTube/一般医療知識に基づく説明にはcitation不要
- section4のtextは必ず3文以上で記述すること
- section5のdescは必ず3文以上で記述すること
- section6の各カテゴリのitemsは配列で、複数項目を含めること"""

    result = await generate_json(prompt, SYSTEM_INSTRUCTION)
    return json.loads(result)
